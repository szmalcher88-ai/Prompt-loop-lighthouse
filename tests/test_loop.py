# -*- coding: utf-8 -*-
"""Testy pętli loop.py — patrz spec: INSTRUKCJE-KOLEJNA-SESJA.md, sekcja 3."""
from conftest import (
    LoopEnv,
    TEMPLATE,
    VERIFY_ALWAYS_RED,
    VERIFY_GREEN,
    VERIFY_NO_BAD,
    VERIFY_NO_BAD_VERBOSE,
)


# ---------------------------------------------------------------------------
# (1) happy path
# ---------------------------------------------------------------------------

def test_happy_path_two_tasks_two_commits(tmp_path):
    env = LoopEnv(tmp_path, ["good:done1.txt", "good:done2.txt"], VERIFY_GREEN)
    rc, out, err = env.run_loop()
    assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"

    plan = env.plan_text()
    assert "- [x] good:done1.txt" in plan
    assert "- [x] good:done2.txt" in plan
    assert "- [ ]" not in plan

    loop_commits = [s for s in env.commit_subjects() if s.startswith("loop:")]
    assert len(loop_commits) == 2
    assert any("good:done1.txt" in s for s in loop_commits)
    assert any("good:done2.txt" in s for s in loop_commits)

    assert (env.repo / "done1.txt").exists()
    assert (env.repo / "done2.txt").exists()
    assert env.status_porcelain() == ""


# ---------------------------------------------------------------------------
# (2) brak postępu -> eskalacja, stash, [!], czyste drzewo, exit 5
# ---------------------------------------------------------------------------

def test_no_progress_escalates_with_stash(tmp_path):
    env = LoopEnv(tmp_path, ["bad"], VERIFY_NO_BAD)
    rc, out, err = env.run_loop()
    assert rc == 5, f"stdout:\n{out}\nstderr:\n{err}"

    # identyczna porażka 2x => dokładnie 2 próby (eskalacja w drugiej)
    assert len(env.prompts()) == 2

    assert "- [!] bad" in env.plan_text()
    assert "loop-eskalacja" in env.stash_list()
    assert not (env.repo / "bad.txt").exists()  # praca odstawiona na stash
    assert env.status_porcelain() == ""

    reports = env.escalation_reports()
    assert [r.name for r in reports] == ["ESKALACJA-001.md"]
    report = reports[0].read_text(encoding="utf-8")
    assert "brak-postepu" in report


# ---------------------------------------------------------------------------
# (3) chroniona ścieżka -> eskalacja w pierwszej próbie
# ---------------------------------------------------------------------------

def test_protected_path_escalates_on_first_attempt(tmp_path):
    env = LoopEnv(
        tmp_path, ["protected"], VERIFY_GREEN,
        config_overrides={"protected_paths": ["tests/"]},
    )
    rc, out, err = env.run_loop()
    assert rc == 5, f"stdout:\n{out}\nstderr:\n{err}"

    assert len(env.prompts()) == 1  # eskalacja od razu, bez retry
    assert "- [!] protected" in env.plan_text()
    assert "loop-eskalacja" in env.stash_list()
    assert not (env.repo / "tests" / "hack.txt").exists()
    assert env.status_porcelain() == ""

    reports = env.escalation_reports()
    assert len(reports) == 1
    assert "chroniona-sciezka" in reports[0].read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (4) scope: diff > max_diff_lines -> eskalacja
# ---------------------------------------------------------------------------

def test_scope_guard_escalates_on_big_diff(tmp_path):
    env = LoopEnv(
        tmp_path, ["big"], VERIFY_GREEN,
        config_overrides={"max_diff_lines": 600},
    )
    rc, out, err = env.run_loop()
    assert rc == 5, f"stdout:\n{out}\nstderr:\n{err}"

    assert len(env.prompts()) == 1
    assert "- [!] big" in env.plan_text()
    assert "loop-eskalacja" in env.stash_list()
    assert env.status_porcelain() == ""

    reports = env.escalation_reports()
    assert len(reports) == 1
    assert "scope" in reports[0].read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (5) preflight odmawia startu (exit 2) — osobny test na każdy przypadek
# ---------------------------------------------------------------------------

def _assert_preflight_refused(env, needle):
    rc, out, err = env.run_loop()
    assert rc == 2, f"stdout:\n{out}\nstderr:\n{err}"
    assert "PREFLIGHT NIEZALICZONY" in err
    assert needle in err
    # preflight nie odpalił agenta
    assert env.prompts() == []


def test_preflight_refuses_red_baseline(tmp_path):
    env = LoopEnv(tmp_path, ["good:x.txt"], VERIFY_ALWAYS_RED)
    _assert_preflight_refused(env, "Baseline jest CZERWONY")


def test_preflight_refuses_dirty_tree(tmp_path):
    env = LoopEnv(tmp_path, ["good:x.txt"], VERIFY_GREEN)
    (env.repo / "niezacommitowany.txt").write_text("brud\n", encoding="utf-8")
    _assert_preflight_refused(env, "nie jest czyste")


def test_preflight_refuses_empty_verify_commands(tmp_path):
    env = LoopEnv(tmp_path, ["good:x.txt"], [])
    _assert_preflight_refused(env, "verify_commands")


def test_preflight_refuses_unfilled_template(tmp_path):
    env = LoopEnv(
        tmp_path, ["good:x.txt"], VERIFY_GREEN,
        template=TEMPLATE + "\n<!-- WYPEŁNIJ: kontekst projektu -->\n",
    )
    _assert_preflight_refused(env, "niewype")


def test_preflight_refuses_state_dir_outside_gitignore(tmp_path):
    env = LoopEnv(tmp_path, ["good:x.txt"], VERIFY_GREEN,
                  gitignore="inny-katalog/\n")
    _assert_preflight_refused(env, ".gitignore")


# ---------------------------------------------------------------------------
# (6) tryb {prompt_file} równoważny stdin
# ---------------------------------------------------------------------------

def test_prompt_file_mode_equivalent_to_stdin(tmp_path):
    env_stdin = LoopEnv(tmp_path / "a", ["good:done.txt"], VERIFY_GREEN,
                        prompt_mode="stdin")
    env_file = LoopEnv(tmp_path / "b", ["good:done.txt"], VERIFY_GREEN,
                       prompt_mode="file")

    for env in (env_stdin, env_file):
        rc, out, err = env.run_loop()
        assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"
        assert "- [x] good:done.txt" in env.plan_text()
        assert (env.repo / "done.txt").exists()
        assert env.status_porcelain() == ""

    # ten sam prompt dotarł do agenta oboma kanałami
    assert env_stdin.prompts() == env_file.prompts()
    assert len(env_stdin.prompts()) == 1


# ---------------------------------------------------------------------------
# (7) on_escalation=skip: po eskalacji pętla idzie do następnego zadania
# ---------------------------------------------------------------------------

def test_on_escalation_skip_continues_to_next_task(tmp_path):
    env = LoopEnv(
        tmp_path, ["bad", "good:done.txt"], VERIFY_NO_BAD,
        config_overrides={"on_escalation": "skip"},
    )
    rc, out, err = env.run_loop()
    assert rc == 0, f"stdout:\n{out}\nstderr:\n{err}"

    plan = env.plan_text()
    assert "- [!] bad" in plan
    assert "- [x] good:done.txt" in plan

    assert "loop-eskalacja" in env.stash_list()
    assert (env.repo / "done.txt").exists()
    assert not (env.repo / "bad.txt").exists()
    assert env.status_porcelain() == ""

    loop_commits = [s for s in env.commit_subjects() if s.startswith("loop:")]
    assert any("good:done.txt" in s for s in loop_commits)


# ---------------------------------------------------------------------------
# (a) wyczerpane-proby: inna porazka w kazdej probie -> eskalacja po limicie
# ---------------------------------------------------------------------------

def test_exhausted_retries_escalates(tmp_path):
    env = LoopEnv(
        tmp_path, ["bad-vary"], VERIFY_NO_BAD_VERBOSE,
        config_overrides={"max_retries_per_task": 3},
    )
    rc, out, err = env.run_loop()
    assert rc == 5, f"stdout:\n{out}\nstderr:\n{err}"

    # kazda proba miala INNA sygnature, wiec zadnego "brak-postepu" --
    # agent dostal pelne max_retries_per_task prob
    assert len(env.prompts()) == 3

    assert "- [!] bad-vary" in env.plan_text()
    assert "loop-eskalacja" in env.stash_list()
    assert not (env.repo / "bad.txt").exists()
    assert env.status_porcelain() == ""

    reports = env.escalation_reports()
    assert [r.name for r in reports] == ["ESKALACJA-001.md"]
    assert "wyczerpane-proby" in reports[0].read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (b) max_iterations: budzet mniejszy niz potrzeba zadan -> exit 3 + event
# ---------------------------------------------------------------------------

def test_max_iterations_budget_exhausted(tmp_path):
    import json
    env = LoopEnv(
        tmp_path, ["good:done1.txt", "good:done2.txt"], VERIFY_GREEN,
        config_overrides={"max_iterations": 1},
    )
    rc, out, err = env.run_loop()
    assert rc == 3, f"stdout:\n{out}\nstderr:\n{err}"

    # pierwsze zadanie zdazylo przejsc, drugie zostalo otwarte
    plan = env.plan_text()
    assert "- [x] good:done1.txt" in plan
    assert "- [ ] good:done2.txt" in plan

    log_lines = (env.repo / ".loop" / "loop_log.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    events = [json.loads(l) for l in log_lines]
    exhausted = [e for e in events if e["event"] == "budget_exhausted"]
    assert len(exhausted) == 1
    assert exhausted[0]["kind"] == "iterations"


# ---------------------------------------------------------------------------
# (c) raport eskalacji zawiera referencje stash i numer proby
# ---------------------------------------------------------------------------

def test_escalation_report_contains_stash_ref_and_attempt(tmp_path):
    env = LoopEnv(tmp_path, ["bad"], VERIFY_NO_BAD)
    rc, out, err = env.run_loop()
    assert rc == 5, f"stdout:\n{out}\nstderr:\n{err}"

    report = env.escalation_reports()[0].read_text(encoding="utf-8")
    assert "stash@{0}" in report          # referencja stash z praca agenta
    assert "**Proba nr:** 2" in report.replace("ó", "o")  # eskalacja w 2. probie
    # referencja z raportu istnieje naprawde
    assert "stash@{0}" in env.stash_list() or env.stash_list().startswith("stash@{0}")


# ---------------------------------------------------------------------------
# (d) numer raportu eskalacji przezywa restart procesu (regresja: licznik
#     w pamieci zerowal sie i nadpisywal ESKALACJA-001.md, niszczac dowody)
# ---------------------------------------------------------------------------

def test_escalation_numbering_survives_loop_restart(tmp_path):
    # dwa zadania; kazdy bieg eskaluje pierwsze otwarte i zatrzymuje sie
    # (on_escalation=stop). Drugi bieg to nowy proces -> licznik w pamieci
    # ruszylby od zera i nadpisal 001; numer z liczby plikow w state_dir nie.
    env = LoopEnv(tmp_path, ["bad", "bad"], VERIFY_NO_BAD)

    rc1, out1, err1 = env.run_loop()
    assert rc1 == 5, f"bieg 1 stdout:\n{out1}\nstderr:\n{err1}"
    assert [r.name for r in env.escalation_reports()] == ["ESKALACJA-001.md"]

    # bieg 2: swiezy proces, drzewo czyste (praca biegu 1 na stashu),
    # baseline zielony; pierwsze otwarte zadanie to drugie "bad"
    rc2, out2, err2 = env.run_loop()
    assert rc2 == 5, f"bieg 2 stdout:\n{out2}\nstderr:\n{err2}"

    names = [r.name for r in env.escalation_reports()]
    assert names == ["ESKALACJA-001.md", "ESKALACJA-002.md"], names
    # raport 001 nie zostal nadpisany przez bieg 2 (numer w tytule zgodny)
    assert "# Eskalacja 001" in env.escalation_reports()[0].read_text(encoding="utf-8")
    assert "# Eskalacja 002" in env.escalation_reports()[1].read_text(encoding="utf-8")
