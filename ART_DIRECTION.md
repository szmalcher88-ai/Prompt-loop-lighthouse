# ART_DIRECTION — gwiazda polarna projektu

Referencja: `art/reference/village_lighthouse.png` (wioska rybacka z latarnią
na skalistej wyspie). Data przyjęcia: 2026-06-11.

**Decyzja architekta (2026-06-11):** wracamy do układu WYSPY. Referencja
unieważnia wcześniejszy „pas wybrzeża" z rundy poprawkowej milestone'u 1.

**Status referencji:** gwiazda polarna, NIE definicja „zrobione". Żadnych
porównań pikselowych z obrazem — nigdy. Obraz steruje wymaganiami przez
ludzką dekompozycję na własności (niżej); część własności staje się
asercjami checkerów, reszta kryteriami bramy (człowiek ogląda PNG).

## Sylwetka

- Latarnia (biało-czerwona) dominuje nad całością, stoi na najwyższym
  plateau wyspy.
- Zabudowa schodzi TARASAMI po skale ku wodzie (>= 3 poziomy tarasowe).
- Osobna turnia z kapliczką, rozłączna z głównym masywem zabudowy,
  połączona mostkiem linowym z poziomem wioski.
- Pierścień skał w wodzie wokół wyspy.
- Zatoczka z plażą od strony POŁUDNIOWEJ (-Z; front kamery "bay"
  w scripts/render_test.py).

## Elementy obowiązkowe (M2 — geometria)

- Mur oporowy na krawędziach tarasów + kamienne schody między poziomami.
- >= 9 budynków mieszkalnych w >= 3 archetypach o istotnie różnej geometrii:
  mur pruski (timber: belki na elewacji), kamienna chata (stone: pełny cokół,
  1 kondygnacja), dwukondygnacyjny z poddaszem (two_story: 2 poziomy okien).
  Zabudowa ciasna: każdy dom ma sąsiada w promieniu <= 12 m.
- Kapliczka na turni; mostek linowy (liny ze zwisem + deski).
- Pomosty przy brzegu (>= 2 segmenty) z rekwizytami: >= 4 beczki,
  >= 3 skrzynie na pomostach lub nabrzeżu.
- Zatoczka z plażą i łódką wiosłową NA PIASKU (nie w wodzie).
- Zieleń: >= 8 krzewów między zabudową (+ istniejące sosny).
- Głazy w wodzie wokół wyspy (>= 8 poza obrysem lądu).

## Paleta (zapisana teraz, realizacja w M3 — tekstury)

- Ciepły kamień: piaskowo-szary.
- Drewno: brąz wyblakły.
- Dachy: łupkowo-ceglaste.
- Latarnia: biel + czerwień.
- Woda: ciemny granat. Zieleń: stonowana.

## Poza zakresem projektu (domena renderera/symulacji, nie modelu)

Fale i piana, postacie, ptaki, efekty atmosferyczne, głębia ostrości.

## Harmonogram zakresów

- M2 „Forma": wyłącznie geometria (ten dokument = wymagania + asercje v3).
- M3: tekstury/materiały wg palety.
- M4: prawdziwy renderer (Blender headless) + LLM-judge przy bramie.
- loop.py: zamrożony bezterminowo.
