# Kaos Schach

Eigene Schach-Analyse für Chess.com-Spieler **2Kaos0**: Partie-Viewer mit Zugbewertung nach Chess.com-Skala (Brillant bis Patzer), Partie-Elo, Material, Filter, interaktives Training aus eigenen Fehlern und Trophäen.

- Seite: https://kaosbene20.github.io/kaos-schach/
- Kennzahlen als JSON (z. B. für Home Assistant): `data/summary.json`

## Daten neu bauen
Voraussetzung: Python 3 mit `python-chess`, Node mit npm-Paket `stockfish` (Stockfish 19 lite, WASM).

```bash
python3 tools/fetch_games.py 2Kaos0                       # Partien laden -> games.json
python3 tools/engine_all.py games.json 2Kaos0 0 1         # Engine-Auswertung je Partie -> cache/
python3 tools/viewer_engine.py games.json 2Kaos0 0 1      # Bewertung jedes Halbzugs -> vcache/
python3 tools/great_engine.py 0 1                         # zweitbester Zug (für "Toll")
python3 tools/puzzle_engine.py 2Kaos0 0 1 10              # alle Züge in Fehlerstellungen -> pcache/
python3 tools/achievements.py games.json 2Kaos0 > data.json
python3 tools/build_app_data.py 2Kaos0                    # -> app/data/*.json
python3 tools/make_page.py                                # -> app/index.html
```

Bewertungsgrenzen nach [Chess.com Hilfe](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-move). Figuren: Cburnett (CC BY-SA 3.0).
