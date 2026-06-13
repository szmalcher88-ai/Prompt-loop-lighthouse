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
