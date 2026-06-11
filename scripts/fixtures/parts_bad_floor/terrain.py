# fixture known-bad: wersja PONIŻEJ PODŁOGI (podłoga terrain = 2; LESSON-003)
CONTRACT_VERSION = 1


def build(**params):
    return [{"name": "terrain",
             "vertices": [(-30, 0.5, -30), (30, 0.5, -30), (30, 0.5, 30), (-30, 0.5, 30)],
             "faces": [("grass", (0, 1, 2)), ("grass", (0, 2, 3))],
             "colors": {"grass": (0.35, 0.5, 0.28)}}]
