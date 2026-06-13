# LESSON-003 — znaczniki wersji kontraktu żyją w plikach edytowalnych przez agenta

Klasyfikacja: **HOLE_IN_GUARDRAILS** (luka ujawniona, nie wykorzystana)
Data: 2026-06-11 (analiza po rundzie poprawkowej milestone'u 1)

## Incydent

W rundzie poprawkowej agent zadania 7 (path) podniósł `SCENE_VERSION` do 2,
choć należało to do zadania 8. Skutek był łagodny (wszystkie asercje v2
przeszły, zadanie 8 zastało stan spełniony i zakończyło się diff=0), ale
incydent ujawnił asymetrię: skoro agent może wersję PODNIEŚĆ, może ją też
OBNIŻYĆ — a obniżenie wersji wyłącza zaostrzone asercje i pozwala uciec
spod kontraktu (wariant reward-hackingu przez osłabienie sygnału prawdy,
analogiczny do edycji testów).

## Który weryfikator zawiódł i dlaczego

Żaden nie zawiódł aktywnie — ale check_parts i check_scene ufały deklaracji
wersji z pliku, który agent ma prawo edytować. Sygnał prawdy częściowo
zależał od autodeklaracji wykonawcy (złamanie zasady wykonawca ≠ decydent).

## Przeciwdziałanie

1. `scripts/versions_floor.json` (w protected_paths, jak cały scripts/) —
   podłoga wersji per część i dla sceny. check_parts i check_scene egzekwują
   `wersja_w_module >= podłoga` ZANIM zastosują resztę asercji.
2. Podłogę podnosi wyłącznie konfigurator przy bramie milestone'u
   (ratchet: tylko w górę, razem z faktycznym stanem repo).
3. Fixture known-bad: część z wersją poniżej podłogi → FAIL
   (scripts/fixtures/parts_bad_floor/ w test_checkers).
4. Podłoga = faktycznie OSIĄGNIĘTY stan repo (ratchet, tylko w górę),
   zweryfikowany empirycznie, nie z narracji briefu. Stan po milestonie 2
   ("Forma"): terrain/house/pier oraz nowe części (wall, chapel, bridge,
   prop_barrel, prop_crate, bush) = 3; boat/tree/rocks/path = 2;
   water i lighthouse = 1 (nigdy nie miały zadań v2+); scena = 3.
   (Brief M2.5 §A1 mówił „2" dla istniejących części/sceny — to wynikało
   z nieaktualnego obrazu stanu; podłoga niższa niż osiągnięta wersja
   pozwalałaby na regresję v3→v2, więc trzymamy się stanu faktycznego,
   spójnie z §A5 „podłoga jeszcze 3" dla sceny w FAZIE A.)
   scena → 4 dopiero PO finałowym zadaniu M2.5.
