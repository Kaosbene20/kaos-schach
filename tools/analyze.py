#!/usr/bin/env python3
"""Schnelle Schachpartie-Analyse mit Stockfish (WASM via Node) + python-chess.

Nutzung:
  python3 analyze.py --user CHESSCOM_NAME [--games 5] [--depth 16] [--out bericht.md]
  python3 analyze.py --pgn partie.pgn --me NAME [--depth 16]
"""
import argparse, io, json, math, sys, urllib.request
from pathlib import Path
import chess, chess.engine, chess.pgn

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "node_modules/stockfish/bin/stockfish-19-lite-single.js"
UA = "PerfectMe-ChessAnalyzer/1.0"
VALUES = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def fetch_games(user, n):
    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    archives = get(f"https://api.chess.com/pub/player/{user.lower()}/games/archives")["archives"]
    games = []
    for url in reversed(archives):
        for g in reversed(get(url)["games"]):
            if g.get("rules") == "chess" and g.get("pgn"):
                games.append(g["pgn"])
                if len(games) >= n:
                    return games
    return games


def win_pct(score, pov):
    s = score.pov(pov)
    if s.is_mate():
        return 100.0 if s.mate() > 0 else 0.0
    cp = s.score()
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def move_accuracy(drop):
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * drop) - 3.1669))


def phase(board):
    mat = sum(VALUES.get(p.piece_type, 0) for p in board.piece_map().values())
    if mat <= 26:
        return "Endspiel"
    return "Eröffnung" if board.fullmove_number <= 12 else "Mittelspiel"


def classify(drop):
    # Chess.com-Skala: Patzer ab 20, Fehler ab 10, Ungenauigkeit ab 5 Prozentpunkten
    if drop >= 20: return "Patzer"
    if drop >= 10: return "Fehler"
    if drop >= 5: return "Ungenauigkeit"
    return None


def analyse_game(pgn_text, me, engine, depth):
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    h = game.headers
    if me and h.get("White", "").lower() == me.lower():
        color = chess.WHITE
    elif me and h.get("Black", "").lower() == me.lower():
        color = chess.BLACK
    else:
        color = chess.WHITE
    tc = h.get("TimeControl", "")
    base = None
    try:
        base = float(tc.split("+")[0]) if tc and "/" not in tc else None
    except ValueError:
        pass

    board = game.board()
    limit = chess.engine.Limit(depth=depth)
    info = engine.analyse(board, limit)
    moves, node = [], game
    while node.variations:
        nxt = node.variations[0]
        mover = board.turn
        before = win_pct(info["score"], mover)
        best = info.get("pv", [None])[0]
        best_san = board.san(best) if best else "?"
        fen_before = board.fen()
        ph = phase(board)
        san = board.san(nxt.move)
        board.push(nxt.move)
        info = engine.analyse(board, limit)
        after = win_pct(info["score"], mover)
        drop = 0.0 if nxt.move == best else max(0.0, before - after)
        clk = nxt.clock()
        moves.append({
            "ply": board.ply(), "mover": mover, "san": san, "best": best_san,
            "drop": drop, "acc": move_accuracy(drop), "cls": classify(drop),
            "phase": ph, "fen": fen_before, "clock": clk,
            "low_time": bool(base and clk is not None and clk < max(10, 0.1 * base)),
        })
        node = nxt

    mine = [m for m in moves if m["mover"] == color]
    acc = sum(m["acc"] for m in mine) / len(mine) if mine else 0
    opening = h.get("ECOUrl", "").rsplit("/", 1)[-1].replace("-", " ") or h.get("Opening", "?")
    return {
        "white": h.get("White"), "black": h.get("Black"), "result": h.get("Result"),
        "termination": h.get("Termination", ""), "date": h.get("Date", ""),
        "timecontrol": tc, "link": h.get("Link", ""), "opening": opening,
        "color": "Weiß" if color == chess.WHITE else "Schwarz",
        "accuracy": round(acc, 1), "moves": mine, "plies": len(moves),
    }


def report(results, me):
    L = [f"# Schach-Analyse{' – ' + me if me else ''}", ""]
    errs = [m for r in results for m in r["moves"] if m["cls"]]
    if not results:
        return "Keine Partien gefunden."
    avg = sum(r["accuracy"] for r in results) / len(results)
    count = {c: sum(1 for m in errs if m["cls"] == c) for c in ("Patzer", "Fehler", "Ungenauigkeit")}
    by_phase = {}
    for m in errs:
        if m["cls"] in ("Patzer", "Fehler"):
            by_phase[m["phase"]] = by_phase.get(m["phase"], 0) + 1
    low = sum(1 for m in errs if m["cls"] in ("Patzer", "Fehler") and m["low_time"])
    big = count["Patzer"] + count["Fehler"]

    L += ["## Überblick",
          f"- Partien: {len(results)} · Ø Genauigkeit (ca.): {avg:.1f} %",
          f"- Patzer: {count['Patzer']} · Fehler: {count['Fehler']} · Ungenauigkeiten: {count['Ungenauigkeit']}",
          f"- Patzer/Fehler pro Partie: {big / len(results):.1f}"]
    if by_phase:
        L.append("- Schwere Fehler nach Phase: " + ", ".join(f"{k} {v}" for k, v in sorted(by_phase.items(), key=lambda x: -x[1])))
    if big:
        L.append(f"- Davon in Zeitnot: {low} von {big}")
    L.append("")

    L.append("## Top-3-Lernpunkte")
    tips = []
    if by_phase:
        worst = max(by_phase, key=by_phase.get)
        tips.append({
            "Eröffnung": "Die meisten schweren Fehler passieren in der Eröffnung: Prinzipien (Zentrum, Entwicklung, Rochade) und 1 feste Eröffnung pro Farbe festigen.",
            "Mittelspiel": "Die meisten schweren Fehler passieren im Mittelspiel: vor jedem Zug Schach/Schlagen/Drohungen (CCT) für beide Seiten prüfen, mehr Taktik-Puzzles.",
            "Endspiel": "Die meisten schweren Fehler passieren im Endspiel: Grundendspiele (Bauernendspiel, Opposition, Turm-Endspiel) üben.",
        }[worst])
    if big and low / big >= 0.4:
        tips.append("Viele schwere Fehler fallen in Zeitnot: langsamere Bedenkzeit spielen (Rapid 10–15 Min.) und Zeit früher einteilen.")
    if count["Patzer"] / len(results) >= 1:
        tips.append("Im Schnitt mindestens 1 Patzer pro Partie: vor dem Zug kurz Blunder-Check ('Was greift mein Gegner nach diesem Zug an?').")
    if avg >= 85 and big / len(results) < 1:
        tips.append("Solide Genauigkeit: nächster Hebel sind Pläne im Mittelspiel und Endspieltechnik.")
    tips.append("Die kritischen Stellungen unten im Analysebrett nachspielen und die bessere Idee selbst finden, bevor du die Lösung ansiehst.")
    for t in tips[:3]:
        L.append(f"- {t}")
    L.append("")

    L.append("## Partien")
    for i, r in enumerate(results, 1):
        L.append(f"### {i}. {r['white']} – {r['black']} ({r['result']})")
        meta = [f"Du: {r['color']}", r['timecontrol'], r['date'] if "?" not in r['date'] else "",
                f"Eröffnung: {r['opening']}" if r['opening'] not in ("", "?") else ""]
        L.append("- " + " · ".join(x for x in meta if x))
        L.append(f"- Genauigkeit (ca.): {r['accuracy']} %" + (f" · {r['termination']}" if r['termination'] else ""))
        if r["link"]:
            L.append(f"- Partie: {r['link']}")
        crit = sorted([m for m in r["moves"] if m["cls"] in ("Patzer", "Fehler")], key=lambda m: -m["drop"])[:3]
        for m in crit:
            num = (m["ply"] + 1) // 2
            dots = "." if m["mover"] == chess.WHITE else "..."
            zeit = " (Zeitnot)" if m["low_time"] else ""
            L.append(f"  - **{m['cls']}** {num}{dots}{m['san']} → besser **{m['best']}** "
                     f"(−{m['drop']:.0f} % Gewinnchance, {m['phase']}){zeit}")
            L.append(f"    FEN zum Üben: `{m['fen']}`")
        if not crit:
            L.append("  - Keine schweren Fehler.")
        L.append("")
    L.append("_Genauigkeit nach Lichess-Formel (Gewinnchance), Werte können von Chess.com abweichen._")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user")
    ap.add_argument("--pgn")
    ap.add_argument("--me")
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--depth", type=int, default=16)
    ap.add_argument("--out", default="schach-analyse.md")
    a = ap.parse_args()
    me = a.me or a.user
    if a.user:
        pgns = fetch_games(a.user, a.games)
    elif a.pgn:
        text = Path(a.pgn).read_text()
        pgns, buf = [], io.StringIO(text)
        while (g := chess.pgn.read_game(buf)) is not None:
            pgns.append(str(g))
    else:
        sys.exit("--user oder --pgn angeben")
    engine = chess.engine.SimpleEngine.popen_uci(["node", str(ENGINE)])
    try:
        results = [analyse_game(p, me, engine, a.depth) for p in pgns]
    finally:
        engine.quit()
    md = report(results, me)
    Path(a.out).write_text(md)
    print(md)


if __name__ == "__main__":
    main()
