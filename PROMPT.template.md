# Zadanie

{{TASK}}

# Kontekst projektu

Projekt: proceduralna wyspa z miasteczkiem nad morzem i latarnią. Trwa MIGRACJA
rdzenia sceny z ręcznych generatorów OBJ na **Blender Python (bpy)**. Architektura
docelowa jest HYBRYDOWA: rdzeń (teren, woda, domy, mur+schody, kapliczka, latarnia)
budują buildery bpy w `parts/<typ>_bpy.py`, a drobiazgi (pomost, łódki, mostek,
krzewy, drzewa, głazy, ścieżka, propsy) pozostają ręcznym OBJ; assembler scala oba
światy w jeden `out/town.obj`. Układ: Y-up w świecie OBJ (poziom morza y=0); w bpy
scena jest Z-up, więc wierzchołek (x,y,z) Y-up mapuje się na (x,-z,y) Blender, co
przy eksporcie (up_axis=Y, forward=-Z) wraca identycznie.

Kontrakt części bpy: sekcja **"Kontrakt bpy"** w `parts/README.md` (PRZECZYTAJ).
W skrócie: `build(seed=0, **params)` — gdy `bpy` jest dostępne, tworzy w bieżącej
scenie nazwane obiekty (grupy) z modyfikatorami i materiałami proceduralnymi i NIC
nie eksportuje (eksport robi `scripts/bpy_build.py`); gdy `bpy` jest niedostępne
(tryb headless), zwraca listę grup stdlib reużywając geometrii ręcznej części
`parts/<typ>.py`. Determinizm bezwzględny: zero losowości, dwa buildy = identyczny
eksport.

**Wzorzec (_ref) = Twoja widoczna specyfikacja.** Dla każdego zadania istnieje
DZIAŁAJĄCY, kompletny wzorzec builder a w `scripts/fixtures/<typ>_bpy_ref.py`
(assembler: `scripts/fixtures/scene_hybrid_ref.py`). Przeczytaj wskazany wzorzec
W CAŁOŚCI przed pisaniem i odtwórz z niego builder w pliku-celu. Wzorce, wszystkie
weryfikatory w `scripts/`, fixtures, `scene.py` oraz ręczne części OBJ `parts/*.py`
są CHRONIONE (sygnał prawdy — pętla ich nie dotyka); są tylko do CZYTANIA.

Blender jest dostępny lokalnie. Weryfikatory bpy uruchamiają Blender wewnętrznie —
możesz wołać `python scripts/<checker>.py`, żeby się sprawdzić.

Definicja "zrobione": PEŁNY łańcuch weryfikatorów kończy się kodem 0 (lista niżej).
Weryfikatory to specyfikacja — przeczytaj asercje dotyczące Twojego zadania przed
pisaniem kodu i traktuj je jako prawdę.

Nie wolno: dodawać zależności spoza stdlib do części (bpy jest dostarczane przez
Blendera w czasie buildu; matplotlib jest zarezerwowany dla narzędzi w `scripts/`);
tworzyć JAKICHKOLWIEK plików poza JEDNYM plikiem-celem wskazanym w sekcji "Zadanie"
(i artefaktami w `out/`) — zero viewerów, skryptów pomocniczych czy "porządków";
dotykać ścieżek chronionych: `scripts/`, `tests/`, `scene.py`, ręcznych
`parts/*.py` (bez sufiksu `_bpy`), `parts/README.md`, `LESSONS/`, `budgets.json`,
plików konfiguracyjnych i dokumentacji repo.

# Zasady pracy (nie zmieniaj ich interpretacji)

1. Wykonaj WYŁĄCZNIE zadanie z sekcji "Zadanie": napisz JEDEN plik-cel wskazany
   w zadaniu, odtwarzając go ze wskazanego wzorca `_ref`. Żadnych refaktorów,
   ulepszeń ani porządków "przy okazji" — wyjdziesz poza limit diffa i cała praca
   zostanie odrzucona.
2. Nie modyfikuj pliku planu zadań ani ścieżek chronionych (w tym wzorców `_ref`,
   weryfikatorów, fixtures, `scene.py`, ręcznych `parts/*.py`) — każda taka zmiana
   jest automatycznie eskalowana do człowieka i unieważnia próbę.
3. Przed zakończeniem uruchom lokalnie weryfikatory i doprowadź je do zieleni:
{{VERIFY_COMMANDS}}
4. NIE wykonuj commitów. Commit robi pętla po niezależnej weryfikacji.
   Twoja praca to zmiany w drzewie roboczym, nic więcej.
5. Jeśli zadanie jest niewykonalne lub niejednoznaczne, nie improwizuj szeroko —
   zrób minimalną, uczciwą wersję albo zakończ bez zmian, wypisując powód
   (trafi do logu pętli).

# Feedback z poprzedniej próby

{{FEEDBACK}}
