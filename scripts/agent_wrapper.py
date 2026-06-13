#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper agenta: przeżywa limity sesji Claude CLI bez ręcznego wznawiania.

Uruchamia prawdziwą komendę agenta (argv po nazwie skryptu), przekazując jej
prompt ze stdin. Jeśli w outputcie wykryje sygnaturę limitu sesji
("session limit" / "resets HH:MMam/pm"), NIE zwraca porażki — czeka do czasu
resetu (z rozsądnym capem) i ponawia z tym samym promptem. Każdy inny błąd
przechodzi bez zmian (pętla obsłuży go jak dotąd).

To warstwa PROJEKTOWA (nie loop.py): obie eskalacje M2 wynikały z limitu
sesji, nie z merytoryki — pętla widziała je poprawnie jako porażki, wrapper
oszczędza tylko ręcznych wznowień.

Użycie (w loop.config.json jako agent_command, prompt na stdin):
  python scripts/agent_wrapper.py claude -p --permission-mode acceptEdits ...

Logika wydzielona do funkcji (now_fn / sleep_fn / run_fn wstrzykiwane w testach).
"""

import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

LIMIT_PAT = re.compile(r"session limit|usage limit|rate limit", re.IGNORECASE)
RESET_PAT = re.compile(r"resets?\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)?", re.IGNORECASE)

DEFAULT_MAX_WAIT_SECONDS = 6 * 3600     # cap pojedynczego oczekiwania
DEFAULT_MAX_LIMIT_RETRIES = 4           # ile razy łącznie czekać na reset
WAKE_BUFFER_SECONDS = 45                # margines po deklarowanym resecie


def detect_limit(text: str) -> bool:
    return bool(LIMIT_PAT.search(text or ""))


def parse_reset_delay(text: str, now: datetime):
    """Sekundy do deklarowanego resetu (z RESET_PAT) lub None, gdy nie da się
    sparsować. Czas 12h (am/pm) liczony do najbliższego przyszłego wystąpienia."""
    m = RESET_PAT.search(text or "")
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    ampm = (m.group(3) or "").lower()
    if not (0 <= minute < 60):
        return None
    if ampm:
        if not (1 <= hour <= 12):
            return None
        hour = hour % 12 + (12 if ampm == "pm" else 0)
    elif not (0 <= hour < 24):
        return None
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds() + WAKE_BUFFER_SECONDS


def run_with_retry(cmd, prompt, *, run_fn, now_fn, sleep_fn,
                   max_wait_seconds=DEFAULT_MAX_WAIT_SECONDS,
                   max_limit_retries=DEFAULT_MAX_LIMIT_RETRIES, log=None):
    """Uruchom cmd (lista argv) z promptem na stdin. Zwraca (rc, output).

    run_fn(cmd, prompt) -> (rc, output); now_fn() -> datetime; sleep_fn(sec).
    Limit sesji => czekaj do resetu i ponów; inny wynik => zwróć bez zmian.
    Limit, którego resetu nie da się sparsować lub jest dalej niż cap, NIE jest
    maskowany — zwracany jako porażka (pętla eskaluje, dowód zostaje)."""
    log = log or (lambda m: print(m, file=sys.stderr, flush=True))
    for attempt in range(max_limit_retries + 1):
        rc, out = run_fn(cmd, prompt)
        if rc == 0 or not detect_limit(out):
            return rc, out
        if attempt == max_limit_retries:
            log("[agent_wrapper] limit sesji nadal aktywny po %d oczekiwaniach "
                "— przepuszczam jako porażkę." % max_limit_retries)
            return rc, out
        delay = parse_reset_delay(out, now_fn())
        if delay is None:
            log("[agent_wrapper] limit sesji, ale nie sparsowałem czasu resetu "
                "— przepuszczam jako porażkę.")
            return rc, out
        if delay <= 0 or delay > max_wait_seconds:
            log("[agent_wrapper] limit sesji, reset za %.0f s (poza capem %d s) "
                "— przepuszczam jako porażkę." % (delay, max_wait_seconds))
            return rc, out
        wake = now_fn() + timedelta(seconds=delay)
        log("[agent_wrapper] limit sesji — czekam do %s (~%.0f min), potem ponawiam."
            % (wake.strftime("%H:%M"), delay / 60))
        sleep_fn(delay)
    return rc, out


_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_\-./:=]+$")


def _shell_join(cmd):
    """Złóż argv z powrotem w string dla shell=True, cytując tokeny ze znakami
    specjalnymi (np. 'Bash(python:*)'). Powód: na Windows `claude` to npm-owy
    shim .cmd — subprocess bez shella go nie rozwiąże, więc inner komendę
    odpalamy przez shell tak samo, jak robiła to dotąd pętla."""
    out = []
    for tok in cmd:
        out.append(tok if _SAFE_TOKEN.match(tok) else '"%s"' % tok.replace('"', r'\"'))
    return " ".join(out)


def _real_run(cmd, prompt):
    p = subprocess.run(_shell_join(cmd), input=prompt, capture_output=True,
                       text=True, shell=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main(argv):
    cmd = argv[1:]
    if not cmd:
        print("agent_wrapper: brak komendy agenta w argumentach", file=sys.stderr)
        return 2
    prompt = sys.stdin.read()
    rc, out = run_with_retry(cmd, prompt, run_fn=_real_run,
                             now_fn=datetime.now, sleep_fn=time.sleep)
    sys.stdout.write(out)
    sys.stdout.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
