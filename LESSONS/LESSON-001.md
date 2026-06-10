# LESSON-001 — pętla zaakceptowała viewer HTML bez pokrycia weryfikatorem

Klasyfikacja: **MISS_BY_VERIFIER**
Data: 2026-06-10 (bieg równoległego eksperymentu)

## Incydent

W biegu równoległego eksperymentu agent pętli wytworzył, obok zadanego artefaktu,
viewer HTML do podglądu modelu. Pętla zweryfikowała i scommitowała tę pracę jako
zieloną, mimo że nikt (ani człowiek, ani maszyna) nie sprawdził, czy viewer
w ogóle działa. Artefakt wszedł do historii repo jako „zweryfikowany",
choć sygnał prawdy w ogóle go nie dotykał.

## Który weryfikator zawiódł i dlaczego

Żaden — i to jest sednem incydentu. `verify_commands` pokrywały wyłącznie
geometrię OBJ (check_lighthouse). Viewer HTML leżał poza dziedziną wszystkich
weryfikatorów, więc pętla nie miała jak go odrzucić: dla sygnału prawdy był
niewidzialny. Pętla działała poprawnie wobec swojej definicji prawdy;
zawiodła definicja prawdy (za wąska wobec tego, co agent może wytworzyć).

## Przeciwdziałanie

1. **Render-test** (`scripts/render_test.py`): podgląd dla człowieka dają
   deterministyczne rendery PNG generowane i sprawdzane w łańcuchu verify —
   nie artefakty ad hoc.
2. **Zakaz artefaktów bez pokrycia**: szablon promptu zakazuje agentowi
   tworzenia jakichkolwiek plików poza jawnie dozwolonymi ścieżkami;
   viewer HTML wejdzie dopiero w milestonie z infrastrukturą zdolną go
   zweryfikować (decyzja: Playwright albo rezygnacja).
3. Reguła ogólna do stosowania przy każdym przyszłym planie: **każdy artefakt
   wymieniony w zadaniu musi mieć wskazaną sekcję weryfikatora, która go
   pokrywa**; artefakt bez weryfikatora nie wchodzi do planu.
