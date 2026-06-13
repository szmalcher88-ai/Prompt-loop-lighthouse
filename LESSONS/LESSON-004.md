# LESSON-004 — luka relacji przestrzennych: checkery mierzą pozycję, nie styk

Klasyfikacja: **MISS_BY_VERIFIER** (mierzalne, a niemierzone)
Data: 2026-06-13 (brama milestone'u 2.5, rendery Blendera)

## Incydent

Rendery bramy M2.5 ujawniły trzy defekty o WSPÓLNYM korzeniu:
1. schody (mur/stopnie) nachodzą na bryłę domu,
2. łódka tonie w wodzie zamiast spoczywać na tafli (regres z M1 — łódka
   znów zanurzona),
3. drewniane schody do kapliczki urywają się w trawie, nie dochodząc do progu.

## Który weryfikator zawiódł i dlaczego

Żaden — i to jest korzeń: checkery sprawdzały ISTNIENIE i POZYCJĘ części
(grupa istnieje, centroid w zakresie, posadowiona na terenie, AABB domów
rozłączne) ale NIE ich STYK z innymi częściami. Kolizje liczyliśmy wyłącznie
DOM-DOM, nie DOM-infrastruktura. „Przyleganie" końca ścieżki/schodów do tego,
co łączą, nie było w ogóle pojęciem w sygnale prawdy. Dopóki elementy nie
musiały się stykać, luka była niewidoczna; gdy zaczęły (schody między
poziomami, łódka na wodzie, mostek do turni) — ujawniła się jako trzy
niezależne objawy jednej dziury.

## Przeciwdziałanie

Nowa KLASA asercji: **relacje przestrzenne między częściami** (check_scene,
od SCENE_VERSION >= 5), oparta na liczbowych helperach AABB (scripts/geom.py):
1. (a) schody/mur NIE przenikają AABB budynków (wariant kolizji
   dom-infrastruktura) i STYKAJĄ się z dwoma poziomami, które łączą
   (min/max-Y ≈ wysokości łączonych poziomów w tolerancji);
2. (b) łódka pływająca: dno ≈ y=0, burty nad taflą, nie zatopiona głębiej
   niż próg; łódka plażowa: spoczywa na piasku;
3. (c) ścieżka/mostek do kapliczki: oba końce stykają się (jeden z poziomem
   wioski, drugi z progiem kapliczki/gruntem turni) — koniec NIE urywa się
   w powietrzu/trawie.

Reguła ogólna: gdy część MA się stykać z inną, styk jest osobną, liczbową
asercją (próg tolerancji + uzasadnienie w komentarzu) z fixture'em known-bad,
nie domniemaniem z pozycji. Materiały (M3) świadomie PO tej rundzie:
tekstura na błędnej formie utrwala błąd i wymusza ponowne mapowanie UV.
