#!/usr/bin/env python3
"""Bewertet in jeder eigenen Fehlerstellung ALLE legalen Züge (für das interaktive Training).
Nutzung: python3 puzzle_engine.py NAME WORKER_INDEX WORKER_COUNT [tiefe]  (liest vcache/, schreibt pcache/)"""
import glob, json, math, sys
from pathlib import Path
import chess, chess.engine
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bewertung import klassifiziere, FEHLER

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "node_modules/stockfish/bin/stockfish-19-lite-single.js"
ME, idx, cnt = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3])
DEPTH = int(sys.argv[4]) if len(sys.argv) > 4 else 14
out_dir = Path("pcache"); out_dir.mkdir(exist_ok=True)


def win(score, pov):
    s = score.pov(pov)
    if s.is_mate():
        return 100.0 if s.mate() > 0 else 0.0
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * s.score())) - 1)


jobs = []
for f in sorted(glob.glob("vcache/*.json")):
    g = json.load(open(f))
    klassifiziere(g["plies"])
    mc = chess.WHITE if g["white"]["name"].lower() == ME else chess.BLACK
    for i, p in enumerate(g["plies"][1:], 1):
        mover = chess.WHITE if i % 2 == 1 else chess.BLACK
        if mover == mc and p["cls"] in FEHLER:
            jobs.append((g, i))

engine = chess.engine.SimpleEngine.popen_uci(["node", str(ENGINE)])
try:
    for k, (g, i) in enumerate(jobs):
        if k % cnt != idx:
            continue
        pid = f'{g["id"]}-{i}'
        out = out_dir / f"{pid}.json"
        if out.exists():
            continue
        board = chess.Board(g["plies"][i - 1]["fen"])
        mover = board.turn
        legal = list(board.legal_moves)
        infos = engine.analyse(board, chess.engine.Limit(depth=DEPTH), multipv=len(legal))
        moves = []
        for inf in infos:
            mv = inf["pv"][0]
            sc = inf["score"].pov(mover)
            moves.append({"uci": mv.uci(), "san": board.san(mv), "w": round(win(inf["score"], mover), 1),
                          "m": sc.mate() if sc.is_mate() else None})
        moves.sort(key=lambda m: -m["w"])
        played = g["plies"][i]
        out.write_text(json.dumps({
            "id": pid, "game": g["id"], "ply": i, "fen": board.fen(), "side": "w" if mover else "b",
            "played": {"uci": played["uci"], "san": played["san"], "cls": played["cls"]},
            "before": round(g["plies"][i - 1]["w"] if mover else 100 - g["plies"][i - 1]["w"], 1),
            "moves": moves,
        }, separators=(",", ":")))
        print(f"[{idx}] {k+1}/{len(jobs)} {pid} {len(legal)} Züge", flush=True)
finally:
    engine.quit()
