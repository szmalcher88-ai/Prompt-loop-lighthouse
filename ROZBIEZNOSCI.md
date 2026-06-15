# Rozbieżności: spec (INSTRUKCJE-KOLEJNA-SESJA.md §3) vs zachowanie loop.py

**Brak rozbieżności.**

Podczas pisania suite'u (tests/test_loop.py, 11 testów) faktyczne zachowanie
`loop.py` we wszystkich sprawdzanych punktach zgadzało się z opisem w sekcji 3
specyfikacji:

- happy path: commit `loop: <zadanie>` per zadanie, `[x]` w planie, exit 0;
- identyczna sygnatura porażki przy drugiej próbie → eskalacja „brak-postepu",
  exit 5, praca na stashu (`loop-eskalacja`), `[!]` w planie, czyste drzewo,
  raport `.loop/ESKALACJA-001.md`;
- guardy chronionej ścieżki i `max_diff_lines` działają na zastanym diffie,
  PRZED weryfikacją — eskalacja w pierwszej próbie, bez retry;
- preflight odmawia startu (exit 2) dla: czerwonego baseline'u, brudnego
  drzewa, pustych `verify_commands`, znacznika `WYPEŁNIJ` w szablonie,
  `state_dir` poza `.gitignore`;
- tryby podawania promptu (stdin i `{prompt_file}`) dają identyczny prompt
  i identyczny rezultat;
- `on_escalation: skip` oznacza zadanie `[!]` i kontynuuje od następnego.

Żaden test nie wymagał oznaczenia `xfail` ani zmiany `loop.py`.

---

## Rozbieżność 1 (M2.5): numeracja raportów eskalacji nie przeżywała restartu

**Defekt.** Numer raportu eskalacji pochodził z licznika `esc_counter`
trzymanego w pamięci procesu pętli (inicjowany `= 0` przy każdym `run()`).
Po zatrzymaniu pętli (`on_escalation: stop`) i ponownym uruchomieniu — co
w praktyce zdarza się przy każdej eskalacji wymagającej interwencji człowieka —
licznik startował od zera, więc kolejna eskalacja zapisywała znów
`ESKALACJA-001.md`, **nadpisując** raport z poprzedniego biegu.

**Obserwacja.** Ujawnione w milestonie 2: dwie eskalacje w osobnych biegach
(`terrain v3`, potem `scene v3`) wyprodukowały tylko jeden plik
`ESKALACJA-001.md` — raport pierwszej eskalacji przepadł.

**Klasa.** Utrata materiału dowodowego (raport eskalacji to jedyny trwały
ślad ścieżki porażki; jego nadpisanie kasuje dowód, na którym opiera się
diagnoza i decyzja człowieka).

**Decyzja człowieka (brief M2.5 §A1): naprawić** (nie `xfail`). Autoryzowane,
wąskie odmrożenie `loop.py`. Poprawka: numer raportu liczony z liczby
istniejących plików `ESKALACJA-*.md` w `state_dir` (`+1`), nie z licznika
w pamięci. Format raportu bez zmian. Licznik `esc_counter` usunięty
(parametr + inicjalizacja + 5 inkrementacji w call-sites).

**Test regresyjny.** `tests/test_loop.py::test_escalation_numbering_survives_loop_restart`:
dwa biegi pętli w jednym tmp-repo, każdy z wymuszoną eskalacją → istnieją
`ESKALACJA-001.md` ORAZ `ESKALACJA-002.md` (nie jeden nadpisany). Suite po
fiksie: 15 testów zielonych (14 dotychczasowych + 1 nowy; brief zakładał 16
istniejących i 17 łącznie — faktyczny stan repo to 14, stąd 15).

Po tym fiksie `loop.py` z powrotem traktujemy jako zamrożony.

---

## Rozbieżność 2 (przed migracją drobiazgów): cichy błąd dekodowania wyjścia agenta (cp1250) mógł maskować wynik

**Defekt.** Odczyt stdout/stderr agenta był dekodowany domyślnym kodowaniem
konsoli (na Windows cp1250). Wyjście agenta ze znakiem spoza cp1250 — np. bajt
`0x88`, niezdefiniowany w cp1250 — wywracało odczyt (`UnicodeDecodeError:
'charmap'`) w warstwie czytającej wyjście, a `rc=0` mimo to prowadził do
`task_done`. Źródło: `scripts/agent_wrapper.py._real_run` czytał wyjście agenta
przez `subprocess.run(..., text=True)` bez jawnego kodowania, a `main()`
wypisywał je na cp1250-owy stdout (drugi hazard, przy zapisie).

**Obserwacja.** Bieg 13 czerwca: trzy zadania pokazały `UnicodeDecodeError:
'charmap'`/cp1250 w `output_tail` przy `rc=0`. Tym razem skończyło się dobrze,
bo weryfikatory i tak przeszły — ale to cicha krucha granica.

**Klasa.** Cichy błąd dekodowania może maskować wynik agenta: gdyby wyjątek
kiedyś przesłonił realny błąd agenta, pętla zobaczyłaby `rc=0` i scommitowała
na wątpliwym fundamencie. Klasa pokrewna do utraty materiału dowodowego
(Rozbieżność 1), ale tu zagrożony jest sam sygnał „czy agent się udał".

**Decyzja człowieka (brief przed migracją drobiazgów): naprawić** (nie obejść).
Źródło dekodowania leży w warstwie PROJEKTOWEJ (`agent_wrapper.py`), więc
naprawa **bez odmrażania `loop.py`** — węższa ścieżka, zgodnie z decyzją.
Poprawka: `_real_run` wymusza `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`
w środowisku procesu agenta (jego python nie generuje już błędów cp1250) ORAZ
czyta wyjście z `encoding="utf-8", errors="replace"` (niedekodowalny bajt staje
się znakiem zastępczym, nie wyjątkiem); `main()` reconfiguruje stdout/stderr na
`utf-8`/`replace` (zapis wyjścia agenta nie wywraca się przy `write`).

**Residual (świadomie nieodmrażany).** `loop.py.run_cmd` nadal czyta wyjście
wrappera przez `text=True` — ten sam latentny hazard. W logu NIE wystrzelił
(pętla nie padła, `rc=0` znaczył, że odczyt loop.py się powiódł), a po fiksie
wrapper emituje czyste utf-8 i bieg i tak jest uruchamiany z `PYTHONUTF8=1`.
Kanoniczny `loop.py` (snapshot w skillu) ma już `encoding="utf-8",
errors="replace"` w `run_cmd` — gdyby kiedyś trzeba domknąć i ten warstwę,
robi się to wąskim odmrożeniem jako sync z kanoniczną wersją.

**Test regresyjny.** `tests/test_agent_wrapper.py::test_agent_output_non_cp1250_does_not_break_read`:
`monkeypatch` usuwa `PYTHONUTF8`/`PYTHONIOENCODING` ze środowiska (symuluje
warunek defektu — launch bez utf-8); agent emituje bajt `0x88` + polskie znaki
utf-8 → `_real_run` (a) wymusza utf-8 w procesie agenta (`ENC=utf-8`),
(b) czyta wyjście bez wyjątku i bez utraty treści (`POLISH`/`END` obecne),
(c) zachowuje `rc=0`. Suite po fiksie: 16 testów (15 + 1 nowy). `loop.py`
nietknięty — pozostaje zamrożony.
