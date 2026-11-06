#!/usr/bin/env python3
"""Ergänzt in vcache/ für jeden Bestzug den Abstand zum zweitbesten Zug ("gap", Prozentpunkte aus Sicht des Ziehenden).
Grundlage für "Toll" (einziger guter Zug). Nutzung: python3 great_engine.py WORKER_INDEX WORKER_COUNT [tiefe]"""
import glob, json, math, sys
from pathlib import Path
import chess, chess.engine

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "node_modules/stockfish/bin/stockfish-19-lite-single.js"
idx, cnt = int(sys.argv[1]), int(sys.argv[2])
DEPTH = int(sys.argv[3]) if len(sys.argv) > 3 else 14


def win(score, pov):
    s = score.pov(pov)
    if s.is_mate():
        return 100.0 if s.mate() > 0 else 0.0
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * s.score())) - 1)


engine = chess.engine.SimpleEngine.popen_uci(["node", str(ENGINE)])
try:
    for k, f in enumerate(sorted(glob.glob("vcache/*.json"))):
        if k % cnt != idx:
            continue
        g = json.load(open(f))
        changed = False
        for i, p in enumerate(g["plies"][1:], 1):
            if "gap" in p or not p.get("best_uci") or p.get("uci") != p["best_uci"]:
                continue
            b = chess.Board(g["plies"][i - 1]["fen"])
            if b.legal_moves.count() < 2:
                continue
            infos = engine.analyse(b, chess.engine.Limit(depth=DEPTH), multipv=2)
            ws = [win(x["score"], b.turn) for x in infos]
            top = infos[0]["pv"][0].uci() == p["uci"]
            p["gap"] = round(ws[0] - ws[1], 1) if top and len(ws) > 1 else 0.0
            changed = True
        if changed:
            Path(f).write_text(json.dumps(g, separators=(",", ":")))
        print(f"[{idx}] {f}", flush=True)
finally:
    engine.quit()
