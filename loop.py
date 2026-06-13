#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loop.py — generyczny szkielet pętli promptującej agenta kodującego.

Filozofia (inwarianty):
  * Agent PROPONUJE zmiany. Pętla WERYFIKUJE i COMMITUJE. Agent nigdy nie
    rozstrzyga sam, czy jego praca jest dobra (wykonawca != decydent).
  * Każda iteracja = świeży agent, czysty kontekst. Stan żyje w plikach
    (PLAN.md) i w gicie, nie w oknie kontekstowym agenta.
  * Pętla jest dokładnie tak dobra, jak jej verify_commands (sygnał prawdy).
    Pętla bez weryfikatorów ODMAWIA startu.
  * Baseline musi być zielony przed startem — inaczej pętla nie odróżnia
    własnych szkód od zastanych.
  * PLAN.md należy do pętli; agent, który go dotyka, jest eskalowany.

stdlib-only, Python >= 3.9. Cross-platform (na Windows zalecany Git Bash/WSL).

Użycie:
  python loop.py --config loop.config.json            # normalny bieg
  python loop.py --config loop.config.json --dry-run  # preflight + podgląd promptu, bez agenta
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {
    "repo_dir": ".",
    "plan_file": "PLAN.md",
    "prompt_template": "PROMPT.template.md",
    "state_dir": ".loop",                  # logi + eskalacje; MUSI być w .gitignore
    "agent_command": ["claude", "-p"],     # prompt idzie na stdin; albo użyj {prompt_file}
    "verify_commands": [],                 # listy argv (przenośne) lub stringi (shell)
    "max_iterations": 20,                  # łączny budżet prób (wszystkie zadania)
    "max_retries_per_task": 3,
    "max_wall_seconds": 4 * 3600,
    "agent_timeout_seconds": 1800,
    "verify_timeout_seconds": 900,
    "max_diff_lines": 600,                 # guard na scope creep (dodane+usunięte)
    "protected_paths": [],                 # prefiksy ścieżek; zmiana => eskalacja (np. "tests/")
    "feedback_tail_chars": 4000,           # ile ogona outputu weryfikatora wraca do agenta
    "on_escalation": "stop",               # "stop" | "skip" (skip = idź do następnego zadania)
}

TASK_OPEN = re.compile(r"^- \[ \] (.+?)\s*$")


# ----------------------------------------------------------------------------
# infrastruktura
# ----------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonlLog:
    """Crash-proof log: każdy event natychmiast na dysk (write+flush+fsync)."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(path, "a", encoding="utf-8")

    def event(self, event_kind: str, **data) -> None:
        # nazwa parametru celowo nie "kind" — eventy przekazują kind=... w data
        rec = {"ts": now_iso(), "event": event_kind, **data}
        self._f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._f.flush()
        os.fsync(self._f.fileno())


def run_cmd(cmd, cwd, timeout=None, stdin_text=None):
    """Uruchom komendę. cmd: lista argv (bez shella) lub string (shell).
    Zwraca (returncode, stdout+stderr)."""
    shell = isinstance(cmd, str)
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd), shell=shell, input=stdin_text,
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        out = e.stdout if isinstance(e.stdout, str) else ""
        return 124, (out or "") + "\n[TIMEOUT po %ss]" % timeout
    except FileNotFoundError as e:
        return 127, f"[NIE ZNALEZIONO KOMENDY] {e}"


def git(args, cwd, timeout=120):
    return run_cmd(["git"] + args, cwd, timeout=timeout)


def git_is_clean(cwd) -> bool:
    rc, out = git(["status", "--porcelain"], cwd)
    return rc == 0 and out.strip() == ""


def git_stage_and_summarize(cwd):
    """git add -A, potem podsumowanie zmian: (lista plików, suma linii +/-)."""
    git(["add", "-A"], cwd)
    _, numstat = git(["diff", "--cached", "--numstat"], cwd)
    files, lines = [], 0
    for line in numstat.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added, deleted, path = parts
            lines += (int(added) if added.isdigit() else 0)
            lines += (int(deleted) if deleted.isdigit() else 0)
            files.append(path)
    return files, lines


# ----------------------------------------------------------------------------
# plan zadań (własność pętli, nie agenta)
# ----------------------------------------------------------------------------

def next_open_task(plan_path: Path):
    for line in plan_path.read_text(encoding="utf-8").splitlines():
        m = TASK_OPEN.match(line)
        if m:
            return m.group(1)
    return None


def mark_task(plan_path: Path, task: str, mark: str) -> None:
    """mark: 'x' = zrobione, '!' = eskalowane."""
    text = plan_path.read_text(encoding="utf-8")
    old, new = f"- [ ] {task}", f"- [{mark}] {task}"
    if old not in text:
        raise RuntimeError(f"Zadanie zniknęło z planu (ktoś go dotknął?): {task!r}")
    plan_path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ----------------------------------------------------------------------------
# prompt i agent
# ----------------------------------------------------------------------------

def build_prompt(template_path: Path, task: str, verify_commands, feedback: str) -> str:
    tpl = template_path.read_text(encoding="utf-8")
    verify_str = "\n".join(
        f"  - {c if isinstance(c, str) else ' '.join(c)}" for c in verify_commands
    )
    return (
        tpl.replace("{{TASK}}", task)
           .replace("{{VERIFY_COMMANDS}}", verify_str)
           .replace("{{FEEDBACK}}", feedback or "(pierwsza próba — brak)")
    )


def run_agent(cfg, prompt: str, cwd, log: JsonlLog):
    """Świeży agent na iterację. Prompt przez {prompt_file} albo stdin.
    Plik promptu lądy POZA repo (temp), żeby nie zaśmiecać drzewa gita."""
    cmd = cfg["agent_command"]
    uses_file = any(isinstance(c, str) and "{prompt_file}" in c for c in cmd) \
        if isinstance(cmd, list) else "{prompt_file}" in cmd
    if uses_file:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(prompt)
            pfile = tf.name
        try:
            if isinstance(cmd, list):
                cmd = [c.replace("{prompt_file}", pfile) for c in cmd]
            else:
                cmd = cmd.replace("{prompt_file}", pfile)
            return run_cmd(cmd, cwd, timeout=cfg["agent_timeout_seconds"])
        finally:
            try:
                os.unlink(pfile)
            except OSError:
                pass
    return run_cmd(cmd, cwd, timeout=cfg["agent_timeout_seconds"], stdin_text=prompt)


# ----------------------------------------------------------------------------
# weryfikacja (sygnał prawdy) i sygnatury porażek
# ----------------------------------------------------------------------------

def verify(cfg, cwd):
    """Zwraca listę porażek (pusta = zielono). Stop na pierwszej porażce."""
    for cmd in cfg["verify_commands"]:
        rc, out = run_cmd(cmd, cwd, timeout=cfg["verify_timeout_seconds"])
        if rc != 0:
            return [{
                "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
                "rc": rc,
                "tail": out[-cfg["feedback_tail_chars"]:],
            }]
    return []


def failure_signature(fails) -> str:
    """Heurystyka 'brak postępu': hash (komenda, kod, ogon outputu bez cyfr).
    Cyfry maskowane, bo czasy/liczniki zmieniają się między biegami."""
    h = hashlib.sha256()
    for f in fails:
        h.update(str(f["cmd"]).encode())
        h.update(str(f["rc"]).encode())
        h.update(re.sub(r"\d+", "#", f["tail"][-600:]).encode())
    return h.hexdigest()[:16]


def render_feedback(fails, attempt: int) -> str:
    parts = [
        f"Próba {attempt} NIE przeszła niezależnej weryfikacji. "
        f"Napraw wyłącznie poniższe problemy — nie ruszaj niczego innego."
    ]
    for f in fails:
        parts.append(
            f"### Komenda: `{f['cmd']}` (kod wyjścia {f['rc']})\n"
            f"```\n{f['tail']}\n```"
        )
    return "\n\n".join(parts)


# ----------------------------------------------------------------------------
# eskalacja
# ----------------------------------------------------------------------------

def escalate(cfg, cwd, state_dir: Path, log: JsonlLog, task: str, reason: str,
             detail: str, attempt: int) -> Path:
    """Odstaw pracę agenta na stash (nic nie ginie), oznacz zadanie [!],
    zapisz raport dla człowieka."""
    # Numer raportu wyprowadzony z liczby istniejących plików ESKALACJA-*.md
    # w state_dir, nie z licznika w pamięci procesu: licznik zerował się przy
    # restarcie pętli i nadpisywał ESKALACJA-001.md, niszcząc dowody (ROZBIEZNOSCI.md).
    seq = len(list(state_dir.glob("ESKALACJA-*.md"))) + 1
    stash_ref = None
    if not git_is_clean(cwd):
        git(["stash", "push", "-u", "-m", f"loop-eskalacja: {task[:60]}"], cwd)
        _, top = git(["stash", "list", "-1"], cwd)
        stash_ref = top.strip() or None

    plan_path = Path(cwd) / cfg["plan_file"]
    mark_task(plan_path, task, "!")
    git(["add", cfg["plan_file"]], cwd)
    git(["commit", "-m", f"loop: eskalacja — {task[:60]}"], cwd)

    report = state_dir / f"ESKALACJA-{seq:03d}.md"
    report.write_text(
        f"# Eskalacja {seq:03d}\n\n"
        f"- **Czas:** {now_iso()}\n"
        f"- **Zadanie:** {task}\n"
        f"- **Powód:** {reason}\n"
        f"- **Próba nr:** {attempt}\n"
        f"- **Stash z pracą agenta:** {stash_ref or '(brak zmian do odstawienia)'}\n\n"
        f"## Szczegóły\n\n{detail}\n\n"
        f"## Co dalej (człowiek)\n\n"
        f"1. Obejrzyj pracę agenta: `git stash show -p \"{stash_ref or 'stash@{0}'}\"`\n"
        f"2. Zdecyduj: przywrócić i dokończyć ręcznie (`git stash pop`), "
        f"czy odrzucić (`git stash drop`).\n"
        f"3. Popraw zadanie w {cfg['plan_file']} (doprecyzuj / podziel) "
        f"i zmień `[!]` z powrotem na `[ ]`, jeśli pętla ma spróbować ponownie.\n",
        encoding="utf-8",
    )
    log.event("escalation", task=task, reason=reason, attempt=attempt,
              stash=stash_ref, report=str(report))
    print(f"  !! ESKALACJA ({reason}) -> {report}")
    return report


# ----------------------------------------------------------------------------
# preflight
# ----------------------------------------------------------------------------

def preflight(cfg, cwd: Path, state_dir: Path, log: JsonlLog) -> None:
    def die(msg):
        print(f"PREFLIGHT NIEZALICZONY: {msg}", file=sys.stderr)
        log.event("preflight_failed", reason=msg)
        sys.exit(2)

    rc, _ = git(["rev-parse", "--is-inside-work-tree"], cwd)
    if rc != 0:
        die(f"{cwd} nie jest repozytorium git — pętla nie ma pamięci ani odwrotu.")

    if not cfg["verify_commands"]:
        die("verify_commands jest puste. Pętla bez sygnału prawdy to nie pętla, "
            "to bezobsługowe generowanie zmian. Skonfiguruj weryfikatory.")

    plan = cwd / cfg["plan_file"]
    if not plan.exists():
        die(f"Brak pliku planu: {plan}")

    tpl = cwd / cfg["prompt_template"]
    if not tpl.exists():
        die(f"Brak szablonu promptu: {tpl}")
    tpl_text = tpl.read_text(encoding="utf-8")
    for ph in ("{{TASK}}", "{{FEEDBACK}}"):
        if ph not in tpl_text:
            die(f"Szablon promptu nie zawiera placeholdera {ph}.")
    if "WYPEŁNIJ" in tpl_text:
        die("Szablon promptu zawiera niewypełnione sekcje (znacznik 'WYPEŁNIJ'). "
            "Uzupełnij kontekst projektu przed startem.")

    rc, _ = git(["check-ignore", "-q", str(state_dir)], cwd)
    if rc != 0:
        die(f"Katalog stanu pętli ({cfg['state_dir']}) nie jest w .gitignore. "
            f"Dodaj go, inaczej logi pętli zabrudzą drzewo i scope guard.")

    if not git_is_clean(cwd):
        die("Drzewo robocze nie jest czyste. Pętla wymaga czystego startu, "
            "żeby każdy diff był jednoznacznie pracą agenta.")

    print("Preflight: baseline — uruchamiam weryfikatory na nietkniętym repo...")
    fails = verify(cfg, cwd)
    if fails:
        die("Baseline jest CZERWONY (weryfikator pada na nietkniętym repo): "
            f"`{fails[0]['cmd']}` rc={fails[0]['rc']}. Pętla nie odróżni "
            "własnych szkód od zastanych. Najpierw doprowadź repo do zieleni.\n"
            f"Ogon outputu:\n{fails[0]['tail'][-1500:]}")
    if not git_is_clean(cwd):
        die("Weryfikatory zabrudziły drzewo (artefakty buildu/cache nie są "
            "w .gitignore). Dodaj je do .gitignore — inaczej trafią do commitów pętli.")
    print("Preflight: OK (repo czyste, baseline zielony, plan i szablon obecne).")
    log.event("preflight_ok")


# ----------------------------------------------------------------------------
# główna pętla
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Pętla promptująca agenta kodującego.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="preflight + podgląd promptu pierwszego zadania, bez agenta")
    args = ap.parse_args()

    cfg = dict(DEFAULTS)
    cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    cwd = Path(cfg["repo_dir"]).resolve()
    state_dir = (cwd / cfg["state_dir"]).resolve()
    state_dir.mkdir(parents=True, exist_ok=True)
    log = JsonlLog(state_dir / "loop_log.jsonl")
    log.event("loop_start", config={k: v for k, v in cfg.items()}, dry_run=args.dry_run)

    # PLAN.md należy do pętli — zawsze chroniony przed agentem.
    protected = list(cfg["protected_paths"]) + [cfg["plan_file"]]

    preflight(cfg, cwd, state_dir, log)

    plan_path = cwd / cfg["plan_file"]
    tpl_path = cwd / cfg["prompt_template"]

    if args.dry_run:
        task = next_open_task(plan_path)
        if task is None:
            print("Dry-run: plan nie zawiera otwartych zadań.")
        else:
            print(f"Dry-run: następne zadanie -> {task}\n")
            print("--- PROMPT, który dostałby agent: ---------------------------")
            print(build_prompt(tpl_path, task, cfg["verify_commands"], ""))
            print("-------------------------------------------------------------")
        return 0

    t0 = time.monotonic()
    iterations = 0

    while True:
        if iterations >= cfg["max_iterations"]:
            print("Budżet iteracji wyczerpany — stop.")
            log.event("budget_exhausted", kind="iterations")
            return 3
        if time.monotonic() - t0 > cfg["max_wall_seconds"]:
            print("Budżet czasu wyczerpany — stop.")
            log.event("budget_exhausted", kind="wall_clock")
            return 3

        task = next_open_task(plan_path)
        if task is None:
            print("Plan ukończony — wszystkie zadania zamknięte.")
            log.event("plan_complete")
            return 0

        print(f"\n=== Zadanie: {task}")
        feedback = ""
        seen_sigs = set()
        escalated = False

        for attempt in range(1, cfg["max_retries_per_task"] + 1):
            iterations += 1
            if iterations > cfg["max_iterations"]:
                break
            print(f"  -> próba {attempt}/{cfg['max_retries_per_task']} "
                  f"(iteracja {iterations}/{cfg['max_iterations']})")
            log.event("attempt_start", task=task, attempt=attempt, iteration=iterations)

            prompt = build_prompt(tpl_path, task, cfg["verify_commands"], feedback)
            rc, agent_out = run_agent(cfg, prompt, cwd, log)
            log.event("agent_done", task=task, attempt=attempt, rc=rc,
                      output_tail=agent_out[-1000:])

            files, lines = git_stage_and_summarize(cwd)

            # guard: chronione ścieżki (w tym sam plan)
            touched_protected = [
                f for f in files
                if any(f == p or f.startswith(p.rstrip("/") + "/") or f.startswith(p)
                       for p in protected)
            ]
            if touched_protected:
                escalate(cfg, cwd, state_dir, log, task, "chroniona-sciezka",
                         "Agent zmienił ścieżki wymagające ludzkiej recenzji "
                         f"(guard anty-reward-hacking): {touched_protected}",
                         attempt)
                escalated = True
                break

            # guard: scope creep
            if lines > cfg["max_diff_lines"]:
                escalate(cfg, cwd, state_dir, log, task, "scope",
                         f"Diff ma {lines} linii (limit {cfg['max_diff_lines']}). "
                         f"Zmienione pliki: {files}", attempt)
                escalated = True
                break

            if rc != 0 and not files:
                # agent padł i nic nie zmienił — potraktuj jak porażkę z feedbackiem
                fails = [{"cmd": "agent", "rc": rc,
                          "tail": agent_out[-cfg["feedback_tail_chars"]:]}]
            else:
                fails = verify(cfg, cwd)

            if not fails:
                mark_task(plan_path, task, "x")
                git(["add", "-A"], cwd)
                rc_c, out_c = git(
                    ["commit", "-m", f"loop: {task[:72]}\n\nproba: {attempt}"], cwd)
                if rc_c != 0:
                    print(f"  !! commit nie powiódł się: {out_c.strip()[:300]}")
                    log.event("commit_failed", task=task, detail=out_c[-500:])
                    return 4
                print(f"  OK zielono -> commit ({lines} linii, {len(files)} plików)")
                log.event("task_done", task=task, attempt=attempt,
                          files=files, diff_lines=lines)
                break

            sig = failure_signature(fails)
            log.event("verify_failed", task=task, attempt=attempt, signature=sig,
                      cmd=fails[0]["cmd"], rc=fails[0]["rc"])
            print(f"  XX czerwono: `{fails[0]['cmd']}` rc={fails[0]['rc']} (sig {sig})")

            if sig in seen_sigs:
                escalate(cfg, cwd, state_dir, log, task, "brak-postepu",
                         "Identyczna sygnatura porażki w kolejnych próbach — "
                         "agent kręci się w miejscu.\n\n" + render_feedback(fails, attempt),
                         attempt)
                escalated = True
                break
            seen_sigs.add(sig)
            feedback = render_feedback(fails, attempt)
        else:
            # wyczerpane próby (pętla for nie przerwana breakiem)
            escalate(cfg, cwd, state_dir, log, task, "wyczerpane-proby",
                     f"Zadanie nie zzieleniało w {cfg['max_retries_per_task']} próbach.\n\n"
                     + (feedback or "(brak feedbacku)"), cfg["max_retries_per_task"])
            escalated = True

        if escalated and cfg["on_escalation"] == "stop":
            print("Polityka on_escalation=stop — pętla zatrzymana, czeka na człowieka.")
            log.event("loop_stop", reason="escalation")
            return 5
        # on_escalation == "skip": zadanie oznaczone [!], idziemy dalej


if __name__ == "__main__":
    sys.exit(main())
