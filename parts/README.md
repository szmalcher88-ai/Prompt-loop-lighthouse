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
