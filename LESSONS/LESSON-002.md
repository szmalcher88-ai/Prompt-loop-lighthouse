# LESSON-002 — feedback bramy milestone'u 1: trzy przegapienia weryfikatorów

Klasyfikacja: punkty 1-3 **MISS_BY_VERIFIER**, punkt 4 poza zasięgiem weryfikatorów
Data: 2026-06-10 (brama milestone'u 1)

## Incydent

Brama odesłała scenę z czterema uwagami:
1. pomost wizualnie nie istnieje (brunatny punkt w wodzie),
2. miasteczko czyta się jako wysepka, nie pas wybrzeża,
3. kadr luźny — scena zajmuje ułamek obrazu,
4. ogólnie mało realistyczny wygląd, brak detali.

## Który weryfikator zawiódł i dlaczego

Punkty 1-3 były MIERZALNE, a niemierzone:
- check_parts żądał od pomostu tylko „pale poniżej, deski powyżej" — bez
  minimalnej długości i bez detali; 2-metrowy pomost spełniał kontrakt;
- check_parts/check_scene nie wymagały, by teren sięgał krawędzi sceny —
  wyspa o zasięgu 40x40 m otoczona wodą spełniała wszystkie asercje;
- render_test sprawdzał tylko „obraz niepusty (>0.5%)" — kadr wypełniony
  w 3% był zielony.

Punkt 4 („realistyczniej") nie jest asercją — to poziom jakości doświadczenia.
Pozostaje przy bramie (człowiek ogląda PNG); do pętli wchodzi wyłącznie po
przełożeniu na policzalne cechy geometryczne w treściach zadań.

## Przeciwdziałanie

1. Zaostrzone asercje: pomost (długość/klepki/balustrada/polery), teren
   (zasięg do krawędzi, łukowa linia brzegowa, plaża, klif), wypełnienie
   kadru 25-65% w panoramie render-testu.
2. **Wersjonowany kontrakt** (uogólnienie warunkowego baseline'u): zaostrzenia
   aktywują się od `CONTRACT_VERSION >= 2` (części) / `SCENE_VERSION >= 2`
   (scena), więc baseline i stany pośrednie pozostają zielone, a prawda
   twardnieje commit po commicie.
3. Każde zaostrzenie dostaje fixture known-good i known-bad w test_checkers —
   zaostrzenie bez fixture'a to deklaracja, nie prawda.
4. Zadania częściowe obejmują też integrację w scene.py (część + jej miejsce
   w scenie w jednym commicie), by asercje sceny miały zielone stany pośrednie.
