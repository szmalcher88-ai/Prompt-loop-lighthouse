# Zadanie

{{TASK}}

# Kontekst projektu

Projekt: proceduralny generator modelu 3D latarni morskiej w czystym Pythonie
(stdlib-only, Python >= 3.9). Cała logika modelu mieszka w JEDNYM pliku
`lighthouse.py` w korzeniu repo; uruchomiony przez `python lighthouse.py`
zapisuje model Wavefront OBJ (i ewentualnie MTL) do katalogu `out/`
(twórz go, jest w .gitignore). Układ współrzędnych: Y-up, jednostki ~metry,
oś wieży w (x=0, z=0). Części modelu jako nazwane grupy `o` w OBJ.

Definicja "zrobione": `python scripts/check_lighthouse.py` kończy się kodem 0.
Ten skrypt to sygnał prawdy — przeczytaj go w całości przed pisaniem kodu
i traktuj jego asercje jako specyfikację. Możesz uruchamiać `python ...`
(generator i weryfikator) lokalnie, by się sprawdzić.

Nie wolno: dodawać zależności spoza stdlib; tworzyć innych plików niż
`lighthouse.py` i artefakty w `out/`; dotykać `scripts/`, `tests/`, `loop.py`,
plików konfiguracyjnych i dokumentacji repo.

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
