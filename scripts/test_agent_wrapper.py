#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test agent_wrappera (standalone, jak test_checkers): czas/sleep/runner
mockowane — zero realnego sleepa, zero sieci.

Sprawdza dwa scenariusze z briefu M2.5 A2:
  * output z limitem sesji -> wrapper czeka (sleep wywołany) i ponawia,
    a po resecie zwraca sukces;
  * output z błędem merytorycznym -> przechodzi jako porażka, bez czekania.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_wrapper as aw  # noqa: E402

failures = []


def check(name, cond, detail=""):
    if cond:
        print("  PASS  " + name)
    else:
        failures.append("%s %s" % (name, detail))
        print("  FAIL  " + name + " " + detail)


NOW = datetime(2026, 6, 11, 19, 0, 0)   # 19:00 lokalnie


def main():
    print("agent_wrapper:")

    # (1) limit sesji -> czeka do resetu i ponawia; druga próba sukces
    slept = []
    seq = [
        (1, "You've hit your session limit · resets 8:20pm (Europe/Warsaw)"),
        (0, "ok, zrobione"),
    ]
    calls = {"n": 0}

    def run_fn(cmd, prompt):
        i = calls["n"]
        calls["n"] += 1
        return seq[i]

    rc, out = aw.run_with_retry(
        ["claude", "-p"], "PROMPT",
        run_fn=run_fn, now_fn=lambda: NOW, sleep_fn=slept.append, log=lambda m: None)
    check("limit -> ponowienie kończy się sukcesem", rc == 0 and "zrobione" in out,
          "(rc=%r)" % rc)
    check("limit -> wrapper faktycznie czekał (sleep wywołany)", len(slept) == 1,
          "(slept=%r)" % slept)
    # 19:00 -> 20:20 to 80 min + bufor 45 s
    check("limit -> czas oczekiwania ~ do 20:20", slept and 4800 < slept[0] < 4900,
          "(delay=%r)" % (slept[0] if slept else None))
    check("limit -> dokładnie 2 wywołania agenta", calls["n"] == 2,
          "(n=%r)" % calls["n"])

    # (2) błąd merytoryczny -> przechodzi jako porażka, bez czekania
    slept2 = []
    calls2 = {"n": 0}

    def run_fn_err(cmd, prompt):
        calls2["n"] += 1
        return (1, "Traceback: AssertionError w check_scene")

    rc2, out2 = aw.run_with_retry(
        ["claude", "-p"], "PROMPT",
        run_fn=run_fn_err, now_fn=lambda: NOW, sleep_fn=slept2.append, log=lambda m: None)
    check("błąd merytoryczny -> porażka przepuszczona", rc2 == 1, "(rc=%r)" % rc2)
    check("błąd merytoryczny -> bez czekania", slept2 == [], "(slept=%r)" % slept2)
    check("błąd merytoryczny -> jedno wywołanie agenta", calls2["n"] == 1,
          "(n=%r)" % calls2["n"])

    # (3) sukces od razu -> bez czekania, bez ponawiania
    rc3, out3 = aw.run_with_retry(
        ["claude", "-p"], "P",
        run_fn=lambda c, p: (0, "od razu ok"), now_fn=lambda: NOW,
        sleep_fn=lambda s: failures.append("nie powinno spać"), log=lambda m: None)
    check("sukces od razu -> rc 0 bez snu", rc3 == 0)

    # (4) limit bez sparsowalnego czasu -> nie maskuj, przepuść porażkę
    rc4, out4 = aw.run_with_retry(
        ["claude", "-p"], "P",
        run_fn=lambda c, p: (1, "session limit reached, try later"),
        now_fn=lambda: NOW, sleep_fn=lambda s: failures.append("nie powinno spać"),
        log=lambda m: None)
    check("limit bez czasu resetu -> porażka, bez snu", rc4 == 1)

    if failures:
        print("FAIL — test_agent_wrapper (%d problemów):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("OK: agent_wrapper czeka na reset limitu i przepuszcza błędy merytoryczne.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
