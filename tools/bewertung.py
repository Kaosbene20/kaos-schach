"""Zugbewertung nach der Chess.com-Skala (verlorene Gewinnchance in Prozentpunkten).

Quelle der Grenzen: Chess.com Hilfe "How are moves classified" (Expected Points):
Bester 0 · Exzellent bis 2 · Gut bis 5 · Ungenauigkeit bis 10 · Fehler bis 20 · Patzer ab 20.
Zusätzlich: Erzwungen (einziger legaler Zug), Matt verpasst, Chance verpasst (Fehler des Gegners nicht bestraft).
Brillant: bester oder fast bester Zug (< 2 Punkte), der eine Figur (mind. Leichtfigur) opfert, ohne schon klar zu gewinnen.
Toll: der einzige gute Zug – der zweitbeste Zug wäre mindestens 10 Punkte schlechter (Wert "gap" aus great_engine.py).
Partie-Elo: Schätzung aus dem durchschnittlichen Bauernverlust pro Zug (ACPL), unabhängig vom Rating.
"""
import math
import chess

GRENZEN = [(2, "excellent"), (5, "good"), (10, "inaccuracy"), (20, "mistake")]
FEHLER = ("mistake", "blunder", "missed_mate", "miss")
DEUTSCH = {"blunder": "Patzer", "mistake": "Fehler", "inaccuracy": "Ungenauigkeit"}


def stufe(drop):
    """Stufe nur aus dem Verlust (ohne Sonderfälle)."""
    for grenze, name in GRENZEN:
        if drop < grenze:
            return name
    return "blunder"


def stufe_deutsch(drop):
    """Für die Engine-Auswertung je Partie: Patzer / Fehler / Ungenauigkeit / None."""
    return DEUTSCH.get(stufe(drop))


WERT = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def ist_opfer(fen, uci):
    """True, wenn der gezogene Stein (mind. 3 Punkte) danach netto mind. 2 Punkte einbüßen kann."""
    b = chess.Board(fen)
    mv = chess.Move.from_uci(uci)
    stein = b.piece_at(mv.from_square)
    if stein is None or WERT[stein.piece_type] < 3:
        return False
    geschlagen = b.piece_at(mv.to_square)
    gewinn = WERT[geschlagen.piece_type] if geschlagen else 0
    ich = b.turn
    b.push(mv)
    if b.is_checkmate():
        return False
    ziel = mv.to_square
    gedeckt = bool(b.attackers(ich, ziel))
    angreifer = [WERT[b.piece_at(a).piece_type] for a in b.attackers(not ich, ziel)
                 if not (b.piece_at(a).piece_type == chess.KING and gedeckt)]
    if not angreifer:
        return False
    verlust = WERT[stein.piece_type] - (min(angreifer) if gedeckt else 0)
    return verlust - gewinn >= 2


def zug_cp(p, weiss_zieht_danach=None):
    """Bewertung in Centipawns (Weiß-Sicht), auf ±1000 begrenzt; Matt zählt als ±1000."""
    if p.get("mate") is not None:
        if p["mate"] == 0:
            return None
        return 1000 if p["mate"] > 0 else -1000
    if p.get("cp") is None:
        return None
    return max(-1000, min(1000, p["cp"]))


def partie_elo(plies):
    """Geschätzte Spielstärke beider Seiten in dieser Partie aus dem ACPL: Elo ≈ 3100 · e^(−0,01 · ACPL).
    None, wenn eine Seite weniger als 8 Züge gemacht hat."""
    verlust = {"w": [], "b": []}
    for i in range(1, len(plies)):
        seite = "w" if i % 2 == 1 else "b"
        a = zug_cp(plies[i - 1])
        b = 1000 if seite == "w" else -1000
        if plies[i].get("mate") != 0:
            b = zug_cp(plies[i])
        if a is None or b is None:
            continue
        verlust[seite].append(min(1000, max(0, (a - b) if seite == "w" else (b - a))))
    out = {}
    for s, v in verlust.items():
        if len(v) < 8:
            out[s] = None
            continue
        acpl = sum(v) / len(v)
        out[s] = {"elo": int(round(max(100, min(3000, 3100 * math.exp(-0.01 * acpl))), -1)), "acpl": round(acpl)}
    return out


def klassifiziere(plies):
    """Setzt cls für jeden Halbzug einer Viewer-Partie neu (plies[0] = Startstellung)."""
    for i in range(1, len(plies)):
        p, prev = plies[i], plies[i - 1]
        weiss = i % 2 == 1
        sign = 1 if weiss else -1
        drop = p.get("drop") or 0.0
        if chess.Board(prev["fen"]).legal_moves.count() == 1:
            p["cls"] = "forced"
            continue
        if p.get("mate") == 0:  # Matt gesetzt: immer bester Zug
            p["cls"] = "best"
            continue
        vorher = prev["w"] if weiss else 100 - prev["w"]
        nachher = p["w"] if weiss else 100 - p["w"]
        bester = bool(p.get("best_uci")) and p.get("uci") == p["best_uci"]
        if (bester or drop < 2) and vorher <= 90 and nachher >= 50 and ist_opfer(prev["fen"], p["uci"]):
            p["cls"] = "brilliant"
            continue
        if bester:
            vorvor = plies[i - 1].get("uci") if i >= 2 else None
            rueck = vorvor is not None and vorvor[2:4] == p["uci"][2:4] and chess.Board(plies[i - 2]["fen"]).piece_at(chess.parse_square(vorvor[2:4])) is not None
            p["cls"] = "great" if (p.get("gap") or 0) >= 10 and vorher <= 90 and nachher >= 25 and not rueck else "best"
            continue
        hatte_matt = prev.get("mate") is not None and prev["mate"] * sign > 0
        haelt_matt = (p.get("mate") is not None and p["mate"] * sign > 0) or p.get("mate") == 0
        if hatte_matt and not haelt_matt:
            p["cls"] = "missed_mate"
            continue
        gegner_fehler = i >= 2 and (plies[i - 1].get("drop") or 0) >= 10
        if gegner_fehler and vorher >= 60 and drop >= 10:
            p["cls"] = "miss"
            continue
        p["cls"] = stufe(drop)
    return plies
