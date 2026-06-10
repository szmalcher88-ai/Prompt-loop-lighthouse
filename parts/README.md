# Kontrakt modułu części (`parts/*.py`)

Każdy moduł części eksportuje funkcję:

```python
def build(**params) -> list[dict]
```

Zwraca **listę grup** (część może mieć jedną lub więcej grup `o`). Każda grupa:

```python
{
  "name": str,                      # nazwa grupy `o` (np. "tower", "house")
  "vertices": [(x, y, z), ...],     # float, układ Y-up, jednostki ~metry
  "faces": [(material, (i0, i1, i2, ...)), ...],
                                    # material: str; indeksy 0-based, LOKALNE
                                    # względem "vertices" tej grupy; >=3 indeksy
  "colors": {material: (r, g, b)},  # 0..1; definicje materiałów użytych w faces
}
```

Reguły twarde:
- **Czysty stdlib** — żadnych zależności zewnętrznych w `parts/`.
- **Deterministyczność**: te same `params` → identyczna geometria. Losowość
  wyłącznie przez jawny parametr `seed` (np. `random.Random(seed)`).
- **Zero I/O**: część nie czyta i nie zapisuje plików; zapis OBJ/MTL robi
  wyłącznie assembler (`scene.py`), który scala grupy, przesuwa indeksy
  i nadaje prefiksy nazwom grup (np. `house_1`).
- Wszystkie wartości skończone (bez NaN/inf); budżety wierzchołków/ścianek
  per część w `budgets.json`.

Weryfikacja: `python scripts/check_parts.py` (asercje wspólne + specyficzne
per typ części — przeczytaj przed pisaniem części).

## Wersjonowany kontrakt (zaostrzanie prawdy bez łamania baseline'u)

Każdy moduł części deklaruje stałą modułową `CONTRACT_VERSION = N`
(scene.py analogicznie `SCENE_VERSION = N`). Zaostrzone asercje checkerów
aktywują się wyłącznie dla `CONTRACT_VERSION >= 2` (odpowiednio
`SCENE_VERSION >= 2`). Zadanie "podnieś wersję" = podnieś stałą i spełnij
zaostrzony kontrakt; dzięki temu baseline i wszystkie stany pośrednie planu
pozostają zielone, a prawda twardnieje commit po commicie. Wzorzec
obowiązuje w każdej rundzie rozwoju.

## Wymogi przekrojowe realizmu (obowiązują wszystkie części i scenę)

- **Deterministyczny jitter kolorów per ścianka**: subtelna wariacja barwy
  między ściankami tej samej powierzchni (seed wyprowadzony z parametrów;
  żadnych dwóch identycznych płaszczyzn obok siebie). Realizowane przez
  dodatkowe materiały-odcienie (np. `wall_0`, `wall_1`, `wall_2`).
- **Lekkie nieregularności rozmieszczenia** (poziom sceny): obroty domów
  ±10°, niejednakowe odstępy między instancjami.
- **Zakaz idealnych powtórzeń instancji**: każda instancja części w scenie
  różni się parametrami (wymiary, kolor, seed) od pozostałych.
