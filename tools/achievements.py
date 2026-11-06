#!/usr/bin/env python3
"""Achievements, Kategorien-Statistik und Eröffnungsbilanz aus Chess.com-Partien.
Nutzung: python3 achievements.py games.json NAME [cache_dir] > data.json"""
import io, json, sys, collections
from pathlib import Path
import chess, chess.pgn
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bewertung import stufe_deutsch

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
games_file, ME = sys.argv[1], sys.argv[2].lower()
CACHE = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("cache")


def balance(b, color):
    s = 0
    for p in b.piece_map().values():
        s += VAL[p.piece_type] * (1 if p.color == color else -1)
    return s


def category(g, opp):
    if opp.lower().startswith("coach-"):
        return "Bots / Coach"
    tc, cls = g.get("time_control", ""), g.get("time_class")
    if cls == "bullet":
        return "1 Min (Bullet)"
    if cls == "blitz":
        return "3–5 Min (Blitz)"
    if cls == "rapid":
        return "10 Min (Rapid)" if tc.startswith("600") else "30+ Min (Rapid lang)"
    return "Daily"


def mate_type(b, mover, last_move, was_castle, was_ep):
    """b = Matt-Stellung, mover = mattsetzende Farbe."""
    k = b.king(not mover)
    checkers = list(b.checkers())
    kf, kr = chess.square_file(k), chess.square_rank(k)
    types = []
    if len(checkers) >= 2:
        types.append("Doppelschach-Matt")
    pc = b.piece_at(checkers[0]).piece_type if checkers else None
    neigh = [s for s in chess.SquareSet(chess.BB_KING_ATTACKS[k])]
    if pc == chess.KNIGHT and all(b.piece_at(s) and b.piece_at(s).color != mover for s in neigh):
        types.append("Ersticktes Matt")
    heavy = [s for s in b.pieces(chess.ROOK, mover) | b.pieces(chess.QUEEN, mover)]
    on_edge_rank = kr in (0, 7)
    on_edge_file = kf in (0, 7)
    ladder = False
    for c in checkers:
        if b.piece_at(c).piece_type not in (chess.ROOK, chess.QUEEN):
            continue
        if on_edge_rank and chess.square_rank(c) == kr:
            adj = 1 if kr == 0 else 6
            ladder |= any(chess.square_rank(h) == adj for h in heavy if h != c)
        if on_edge_file and chess.square_file(c) == kf:
            adj = 1 if kf == 0 else 6
            ladder |= any(chess.square_file(h) == adj for h in heavy if h != c)
    if ladder:
        types.append("Treppenmatt")
    back = 7 if mover == chess.WHITE else 0
    if not ladder and kr == back and any(
            b.piece_at(c).piece_type in (chess.ROOK, chess.QUEEN) and chess.square_rank(c) == back for c in checkers):
        types.append("Grundreihenmatt")
    if last_move.promotion:
        types.append("Umwandlungs-Matt")
    if was_castle:
        types.append("Rochade-Matt")
    if was_ep:
        types.append("En-passant-Matt")
    names = {chess.QUEEN: "Damenmatt", chess.ROOK: "Turmmatt", chess.BISHOP: "Läufermatt",
             chess.KNIGHT: "Springermatt", chess.PAWN: "Bauernmatt", chess.KING: "Königsmatt"}
    if pc:
        types.append(names[pc])
    return types


def main():
    raw = [g for g in json.load(open(games_file)) if g.get("rules") == "chess" and g.get("pgn")]
    raw.sort(key=lambda g: g.get("end_time", 0))
    A = collections.Counter()
    EX = collections.defaultdict(list)

    def hit(key, gid, ply):
        A[key] += 1
        if len(EX[key]) < 60:
            EX[key].append([gid, ply])
    best = {}
    cats = collections.defaultdict(lambda: collections.Counter())
    openings = collections.defaultdict(lambda: collections.Counter())
    castle = collections.defaultdict(lambda: collections.Counter())
    sicilian = []
    streak = best_streak = 0
    ratings = {}
    week = collections.Counter()
    import datetime
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    week_start = datetime.datetime.combine(monday, datetime.time()).timestamp()
    results_seq = []
    for g in raw:
        game = chess.pgn.read_game(io.StringIO(g["pgn"]))
        gid = g["url"].rstrip("/").rsplit("/", 1)[-1]
        w, bl = g["white"], g["black"]
        color = chess.WHITE if w["username"].lower() == ME else chess.BLACK
        mine, opp = (w, bl) if color == chess.WHITE else (bl, w)
        moves = list(game.mainline_moves())
        if len(moves) < 2:
            continue
        res = mine["result"]
        outcome = "W" if res == "win" else ("L" if opp["result"] == "win" else "D")
        cat = category(g, opp["username"])
        if not opp["username"].lower().startswith("coach-"):
            tcls = g.get("time_class")
            ratings.setdefault(tcls, {"aktuell": 0, "peak": 0})
            ratings[tcls]["aktuell"] = mine["rating"]
            ratings[tcls]["peak"] = max(ratings[tcls]["peak"], mine["rating"])
        if g.get("end_time", 0) >= week_start:
            week[cat] += 1
        c = cats[cat]
        c["Partien"] += 1
        c[outcome] += 1
        results_seq.append(outcome)
        if outcome == "W":
            streak += 1
            best_streak = max(best_streak, streak)
        elif outcome == "L":
            streak = 0

        eco = game.headers.get("ECOUrl", "").rsplit("/", 1)[-1].replace("-", " ")
        fam = " ".join(eco.split()[:3]) if eco else "Unbekannt"
        side = "Weiß" if color == chess.WHITE else "Schwarz"
        openings[(fam, side)]["Partien"] += 1
        openings[(fam, side)][outcome] += 1

        b = game.board()
        my_castle = "keine"
        min_bal = 0
        bal_hist = [0]
        sic = False
        for i, mv in enumerate(moves):
            mover = b.turn
            is_me = mover == color
            was_castle = b.is_castling(mv)
            was_ep = b.is_en_passant(mv)
            cap = b.piece_at(mv.to_square) if b.is_capture(mv) and not was_ep else None
            piece = b.piece_at(mv.from_square)
            gives_check = b.gives_check(mv)
            b.push(mv)
            bal_hist.append(balance(b, color))
            if i == 1 and moves[0] == chess.Move.from_uci("e2e4") and mv == chess.Move.from_uci("c7c5"):
                sic = True
            if is_me:
                if was_castle:
                    my_castle = "lang (O-O-O)" if chess.square_file(mv.to_square) == 2 else "kurz (O-O)"
                    hit("Lange Rochade" if my_castle.startswith("lang") else "Kurze Rochade", gid, i + 1)
                if was_ep:
                    hit("En passant", gid, i + 1)
                if mv.promotion:
                    hit("Umwandlung", gid, i + 1)
                    if mv.promotion != chess.QUEEN:
                        hit("Unterverwandlung", gid, i + 1)
                if gives_check and len(b.checkers()) >= 2:
                    hit("Doppelschach", gid, i + 1)
                if cap and cap.piece_type == chess.QUEEN:
                    hit("Dame geschlagen", gid, i + 1)
                    if piece.piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP):
                        hit("Dame mit Bauer/Leichtfigur geschlagen", gid, i + 1)
                if piece.piece_type == chess.KNIGHT:
                    targets = [b.piece_at(s) for s in b.attacks(mv.to_square)]
                    big = [t for t in targets if t and t.color != color and t.piece_type in (chess.KING, chess.QUEEN, chess.ROOK)]
                    if len(big) >= 2:
                        hit("Springergabel", gid, i + 1)
                        kinds = {t.piece_type for t in big}
                        if chess.KING in kinds and chess.QUEEN in kinds:
                            hit("Königliche Gabel (König + Dame)", gid, i + 1)
                if b.is_checkmate():
                    hit("Schachmatt gesetzt", gid, i + 1)
                    for t in mate_type(b, color, mv, was_castle, was_ep):
                        hit(t, gid, i + 1)
                    full = b.fullmove_number if color == chess.WHITE else b.fullmove_number - 1
                    if full <= 20:
                        hit("Miniatur-Matt (≤ 20 Züge)", gid, i + 1)
                    if full <= 10 and piece.piece_type == chess.QUEEN and chess.square_name(mv.to_square) in ("f7", "f2"):
                        hit("Schäfermatt", gid, i + 1)
                    best["Schnellstes Matt (Zug)"] = min(best.get("Schnellstes Matt (Zug)", 999), full)
            else:
                if b.is_checkmate():
                    hit("Selbst mattgesetzt worden", gid, i + 1)
            if len(bal_hist) >= 3:
                min_bal = min(min_bal, max(bal_hist[-2], bal_hist[-1]))
        # Materialgewinn: eigener Zug, Bilanz nach gegnerischer Antwort >= +3 gegenüber vor dem Zug
        start = 0 if color == chess.WHITE else 1
        for j in range(start, len(bal_hist) - 2, 2):
            ref = max(bal_hist[j], bal_hist[j - 1]) if j >= 1 else bal_hist[j]
            gain = bal_hist[j + 2] - ref
            if gain >= 3:
                hit("Materialgewinn-Zug (≥ 3 Punkte netto)", gid, j + 1)
            if gain >= 8:
                hit("Dame netto gewonnen", gid, j + 1)
            best["Größter Materialgewinn (Punkte)"] = max(best.get("Größter Materialgewinn (Punkte)", 0), gain)
        castle[my_castle]["Partien"] += 1
        castle[my_castle][outcome] += 1
        if outcome == "W":
            if min_bal <= -5:
                hit("Sieg trotz ≥ 5 Punkten Rückstand", gid, len(moves))
            diff = opp["rating"] - mine["rating"]
            if diff >= 100:
                hit("Giant Killer (+100 Elo besiegt)", gid, len(moves))
            if diff >= 200:
                hit("Giant Killer XL (+200 Elo besiegt)", gid, len(moves))
            if opp["result"] == "timeout":
                hit("Sieg auf Zeit", gid, len(moves))
            if opp["result"] == "resigned":
                hit("Gegner gibt auf", gid, len(moves))
            best["Stärkster besiegter Gegner (Elo)"] = max(best.get("Stärkster besiegter Gegner (Elo)", 0), opp["rating"])
            best["Kürzester Sieg (Züge)"] = min(best.get("Kürzester Sieg (Züge)", 999), (len(moves) + 1) // 2)
        A["Partien gespielt"] += 1
        A["Siege"] += outcome == "W"
        best["Längste Partie (Züge)"] = max(best.get("Längste Partie (Züge)", 0), (len(moves) + 1) // 2)
        if sic:
            sicilian.append({
                "url": g["url"], "farbe": side, "ergebnis": outcome, "rochade": my_castle,
                "eroeffnung": eco, "zuege": " ".join(chess.Board().variation_san(moves[:10]).split()),
                "kategorie": cat,
            })
    best["Längste Siegesserie"] = best_streak

    # Engine-Cache je Kategorie
    eng = collections.defaultdict(lambda: {"acc": [], "patzer": 0, "fehler": 0, "phase": collections.Counter(), "zeitnot": 0, "n": 0})
    url2cat = {}
    for g in raw:
        opp = g["black"] if g["white"]["username"].lower() == ME else g["white"]
        url2cat[g["url"]] = category(g, opp["username"])
    for f in CACHE.glob("*.json"):
        r = json.loads(f.read_text())
        if not r["moves"]:
            continue
        for m in r["moves"]:
            m["cls"] = stufe_deutsch(m["drop"])
        e = eng[url2cat.get(r["url"], "?")]
        e["n"] += 1
        e["acc"].append(r["accuracy"])
        for m in r["moves"]:
            if m["cls"] == "Patzer":
                e["patzer"] += 1
            if m["cls"] == "Fehler":
                e["fehler"] += 1
            if m["cls"] in ("Patzer", "Fehler"):
                e["phase"][m["phase"]] += 1
                e["zeitnot"] += bool(m["low_time"])
        pat = sum(1 for m in r["moves"] if m["cls"] == "Patzer")
        egid = r["url"].rstrip("/").rsplit("/", 1)[-1]
        if pat == 0:
            hit("Partie ohne Patzer", egid, 0)
        if r["accuracy"] >= 90:
            hit("Eiskalt (≥ 90 % Genauigkeit)", egid, 0)
        best["Beste Genauigkeit (%)"] = max(best.get("Beste Genauigkeit (%)", 0), r["accuracy"])

    out = {
        "achievements": dict(A), "beispiele": dict(EX), "rekorde": best,
        "kategorien": {k: {**dict(v), **({
            "engine_partien": eng[k]["n"],
            "genauigkeit": round(sum(eng[k]["acc"]) / len(eng[k]["acc"]), 1) if eng[k]["acc"] else None,
            "patzer_pro_partie": round(eng[k]["patzer"] / eng[k]["n"], 2) if eng[k]["n"] else None,
            "fehler_pro_partie": round(eng[k]["fehler"] / eng[k]["n"], 2) if eng[k]["n"] else None,
            "fehlerphase": dict(eng[k]["phase"]),
            "zeitnot_anteil": round(eng[k]["zeitnot"] / max(1, eng[k]["patzer"] + eng[k]["fehler"]), 2),
        })} for k, v in cats.items()},
        "eroeffnungen": [{"name": k[0], "farbe": k[1], **dict(v)} for k, v in sorted(openings.items(), key=lambda x: -x[1]["Partien"])],
        "rochade": {k: dict(v) for k, v in castle.items()},
        "sizilianisch": sicilian,
        "verlauf": "".join(results_seq),
        "ratings": ratings,
        "diese_woche": dict(week),
        "stand": datetime.date.today().isoformat(),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


main()
