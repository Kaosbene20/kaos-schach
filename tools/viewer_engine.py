#!/usr/bin/env python3
"""Bewertet jeden Halbzug (beide Seiten) für den Partie-Viewer, mit Cache.
Nutzung: python3 viewer_engine.py games.json NAME WORKER_INDEX WORKER_COUNT [tiefe]"""
import io, json, math, sys
from pathlib import Path
import chess, chess.engine, chess.pgn
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bewertung import klassifiziere

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "node_modules/stockfish/bin/stockfish-19-lite-single.js"
games_file, ME, idx, cnt = sys.argv[1], sys.argv[2].lower(), int(sys.argv[3]), int(sys.argv[4])
DEPTH = int(sys.argv[5]) if len(sys.argv) > 5 else 16
cache = Path("vcache"); cache.mkdir(exist_ok=True)


def white_win(score):
    s = score.white()
    if s.is_mate():
        return 100.0 if s.mate() > 0 else 0.0, None, s.mate()
    cp = s.score()
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1), cp, None


def classify(drop, played_best, mate_missed):
    if played_best:
        return "best"
    if mate_missed:
        return "missed_mate"
    if drop >= 30: return "blunder"
    if drop >= 20: return "mistake"
    if drop >= 10: return "inaccuracy"
    if drop >= 5: return "good"
    return "excellent"


games = [g for g in json.load(open(games_file)) if g.get("rules") == "chess" and g.get("pgn")]
engine = chess.engine.SimpleEngine.popen_uci(["node", str(ENGINE)])
limit = chess.engine.Limit(depth=DEPTH)
try:
    for i, g in enumerate(games):
        if i % cnt != idx:
            continue
        gid = g["url"].rstrip("/").rsplit("/", 1)[-1]
        out = cache / f"{gid}.json"
        if out.exists():
            continue
        game = chess.pgn.read_game(io.StringIO(g["pgn"]))
        board = game.board()
        info = engine.analyse(board, limit)
        w0, cp0, m0 = white_win(info["score"])
        plies = [{"fen": board.fen(), "w": round(w0, 1), "cp": cp0, "mate": m0}]
        node = game
        while node.variations:
            nxt = node.variations[0]
            mover = board.turn
            best = info.get("pv", [None])[0]
            before_w = plies[-1]["w"]
            before_mate = plies[-1]["mate"]
            best_san = board.san(best) if best else None
            san = board.san(nxt.move)
            board.push(nxt.move)
            info = engine.analyse(board, limit) if not board.is_game_over() else None
            if info:
                w, cp, m = white_win(info["score"])
            else:
                w = 100.0 if board.is_checkmate() and mover == chess.WHITE else (0.0 if board.is_checkmate() else 50.0)
                cp, m = None, (0 if board.is_checkmate() else None)
            sign = 1 if mover == chess.WHITE else -1
            mover_before = before_w if mover == chess.WHITE else 100 - before_w
            mover_after = w if mover == chess.WHITE else 100 - w
            drop = max(0.0, mover_before - mover_after)
            had_mate = before_mate is not None and before_mate * sign > 0
            still_mate = (m is not None and m * sign > 0) or board.is_checkmate()
            played_best = best is not None and nxt.move == best
            plies.append({
                "san": san, "uci": nxt.move.uci(), "fen": board.fen(), "w": round(w, 1), "cp": cp, "mate": m,
                "best": best_san, "best_uci": best.uci() if best else None,
                "cls": classify(drop, played_best, had_mate and not still_mate),
                "drop": round(0.0 if played_best else drop, 1), "clock": nxt.clock(),
            })
            node = nxt
        w_, b_ = g["white"], g["black"]
        out.write_text(json.dumps({
            "id": gid, "url": g["url"], "end": g.get("end_time"), "time_class": g.get("time_class"),
            "time_control": g.get("time_control"),
            "white": {"name": w_["username"], "rating": w_["rating"], "result": w_["result"]},
            "black": {"name": b_["username"], "rating": b_["rating"], "result": b_["result"]},
            "opening": game.headers.get("ECOUrl", "").rsplit("/", 1)[-1].replace("-", " "),
            "plies": klassifiziere(plies),
        }, separators=(",", ":")))
        print(f"[{idx}] {i+1}/{len(games)} {gid}", flush=True)
finally:
    engine.quit()
