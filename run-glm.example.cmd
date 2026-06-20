@echo off
REM ============================================================
REM  Szablon launchera GLM-5.2 dla auto-loopa.
REM  Skopiuj jako run-glm.cmd (gitignored) i wklej swoj klucz:
REM      copy run-glm.example.cmd run-glm.cmd
REM  Klucz API bierzesz z konsoli https://z.ai (Coding Plan / API key).
REM  Uzycie:  run-glm.cmd            -> bieg petli na GLM-5.2
REM           run-glm.cmd --dry-run  -> preflight + podglad promptu
REM ============================================================
cd /d "%~dp0"
set "ZAI_API_KEY=WKLEJ_TUTAJ_SWOJ_KLUCZ_Z_AI"
python loop.py --config loop.config.json --model glm %*
