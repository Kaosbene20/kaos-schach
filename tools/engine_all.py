#!/usr/bin/env python3
"""Engine-Analyse aller Partien mit Cache (eine JSON-Datei pro Partie).
Nutzung: python3 engine_all.py games.json NAME WORKER_INDEX WORKER_COUNT"""
import json, sys
from pathlib import Path
import chess.engine
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # analyse_game, ENGINE

games_file, me, idx, cnt = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
cache = Path("cache"); cache.mkdir(exist_ok=True)
games = [g for g in json.load(open(games_file)) if g.get("rules") == "chess" and g.get("pgn")]
engine = chess.engine.SimpleEngine.popen_uci(["node", str(analyze.ENGINE)])
try:
    for i, g in enumerate(games):
        if i % cnt != idx:
            continue
        out = cache / (g["url"].rstrip("/").rsplit("/", 1)[-1] + ".json")
        if out.exists():
            continue
        r = analyze.analyse_game(g["pgn"], me, engine, 16)
        for m in r["moves"]:
            m["mover"] = bool(m["mover"])
        r["url"] = g["url"]
        out.write_text(json.dumps(r))
        print(f"[{idx}] {i+1}/{len(games)} {g['url']} acc={r['accuracy']}", flush=True)
finally:
    engine.quit()
