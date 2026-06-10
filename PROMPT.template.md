# Zadanie

{{TASK}}

# Kontekst projektu

Projekt: proceduralne miasteczko nad morzem z latarnią — scena 3D w formacie
Wavefront OBJ/MTL, generowana czystym Pythonem (stdlib-only, Python >= 3.9).
Architektura: moduły części w `parts/` (kontrakt: `parts/README.md` —
PRZECZYTAJ; build(**params) -> lista grup, deterministycznie, zero I/O)
+ assembler `scene.py` w korzeniu, który scala części i zapisuje
`out/town.obj` + `out/town.mtl` (katalog `out/` jest w .gitignore).
Istnieje też `lighthouse.py` (generator latarni, zapisuje out/lighthouse.obj).
Układ współrzędnych: Y-up, jednostki ~metry, poziom morza y=0.

Definicja "zrobione": PEŁNY łańcuch weryfikatorów kończy się kodem 0
(lista w sekcji zasad poniżej). Weryfikatory w `scripts/` to sygnał prawdy —
przeczytaj asercje dotyczące Twojego zadania przed pisaniem kodu i traktuj
je jako specyfikację. Możesz uruchamiać `python ...` lokalnie, by się sprawdzić.

Nie wolno: dodawać zależności spoza stdlib (matplotlib jest zarezerwowany
dla narzędzi weryfikacji w scripts/, NIE dla części); tworzyć JAKICHKOLWIEK
plików poza `parts/*.py`, `scene.py`, `lighthouse.py` i artefaktami w `out/`
— w szczególności zero viewerów HTML i innych artefaktów bez pokrycia
weryfikatorem; dotykać `scripts/`, `tests/`, `loop.py`, `parts/README.md`,
`LESSONS/`, `budgets.json`, plików konfiguracyjnych i dokumentacji repo.

# Zasady pracy (nie zmieniaj ich interpretacji)

1. Wykonaj WYŁĄCZNIE zadanie z sekcji "Zadanie". Żadnych refaktorów,
   ulepszeń ani porządków "przy okazji" — wyjdziesz poza limit diffa
   i cała praca zostanie odrzucona.
2. Nie modyfikuj pliku planu zadań ani ścieżek chronionych — każda taka
   zmiana jest automatycznie eskalowana do człowieka.
3. Przed zakończeniem uruchom lokalnie weryfikatory i doprowadź je do zieleni:
{{VERIFY_COMMANDS}}
4. NIE wykonuj commitów. Commit robi pętla po niezależnej weryfikacji.
   Twoja praca to zmiany w drzewie roboczym, nic więcej.
5. Jeśli zadanie jest niewykonalne lub niejednoznaczne, nie improwizuj
   szeroko — zrób minimalną, uczciwą wersję albo zakończ bez zmian,
   wypisując powód (trafi do logu pętli).

# Feedback z poprzedniej próby

{{FEEDBACK}}
