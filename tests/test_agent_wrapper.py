# -*- coding: utf-8 -*-
"""Regresja ZADANIA A (ROZBIEZNOSCI 2): odczyt wyjscia agenta nie wywraca sie
na znakach spoza cp1250 (bajt 0x88) i wymusza UTF-8 w procesie agenta.

Defekt (Windows): _real_run czytal wyjscie agenta domyslnym cp1250 -> bajt 0x88
(niezdefiniowany w cp1250) wywracal odczyt, a rc=0 mimo to prowadzil do
task_done. Tu symulujemy warunek defektu (srodowisko BEZ PYTHONUTF8) i zadamy,
by fix mimo to: (a) wymusil utf-8 w procesie agenta, (b) przeczytal wyjscie
z bajtem 0x88 + polskimi znakami bez wyjatku i bez utraty tresci, (c) zachowal rc.
"""
import importlib.util
import sys
from pathlib import Path

_WRAP = Path(__file__).resolve().parents[1] / "scripts" / "agent_wrapper.py"
_spec = importlib.util.spec_from_file_location("agent_wrapper", _WRAP)
agent_wrapper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_wrapper)


def test_agent_output_non_cp1250_does_not_break_read(tmp_path, monkeypatch):
    # warunek defektu: launch BEZ wymuszonego utf-8 (jak typowy bieg na Windows)
    monkeypatch.delenv("PYTHONUTF8", raising=False)
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)

    child = tmp_path / "emit.py"
    child.write_text(
        "import sys\n"
        "print('ENC=' + (sys.stdout.encoding or '').lower())\n"
        "sys.stdout.flush()\n"
        # surowe bajty: 0x88 (niedekodowalny w cp1250) + utf-8 'a' (ac4 85) i 'l' (c5 82)
        "sys.stdout.buffer.write(b'POLISH \\x88 \\xc4\\x85\\xc5\\x82 END\\n')\n"
        "sys.stdout.buffer.flush()\n",
        encoding="utf-8",
    )

    rc, out = agent_wrapper._real_run([sys.executable, str(child)], "")

    assert rc == 0, out                                   # rc zachowany
    # fix wymusza utf-8 w procesie agenta mimo braku w srodowisku:
    assert "enc=utf-8" in out.lower(), "proces agenta bez wymuszonego utf-8: " + out
    # odczyt 0x88 + polskich znakow nie wywrocil sie i nie uciol tresci:
    assert "POLISH" in out and "END" in out, "odczyt wywrocil sie/uciol: " + repr(out)
