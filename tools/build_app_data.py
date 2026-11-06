#!/usr/bin/env python3
"""Baut die Daten der Seite "Kaos Schach" (Partien, Training, Trophäen).
Nutzung: python3 build_app_data.py NAME   (liest games.json, data.json, vcache/, pcache/; schreibt app/data/)"""
import collections, datetime, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bewertung import klassifiziere, partie_elo, FEHLER

NAME = sys.argv[1]
ME = NAME.lower()
D = json.load(open("data.json"))
A = D["achievements"]
EX = D.get("beispiele", {})

# (Schlüssel in A, Name, Beschreibung, Stufen B/S/G/L, geheim)
DEFS = {
    "Mattkunst": [
        ("Schachmatt gesetzt", "Mattsetzer", "Partien, die du mit Matt beendet hast", (5, 25, 100, 250), False),
        ("Damenmatt", "Königin des Bretts", "Matt mit der Dame", (3, 15, 50, 150), False),
        ("Turmmatt", "Turmbau", "Matt mit dem Turm", (1, 10, 30, 100), False),
        ("Treppenmatt", "Treppenhaus", "Zwei Schwerfiguren treiben den König an den Rand", (1, 5, 15, 40), False),
        ("Grundreihenmatt", "Hintertür", "Matt auf der Grundreihe des Gegners", (1, 5, 15, 40), False),
        ("Läufermatt", "Diagonal-Diplomat", "Matt mit dem Läufer", (1, 5, 15, 30), False),
        ("Springermatt", "Um die Ecke", "Matt mit dem Springer", (1, 5, 15, 30), False),
        ("Bauernmatt", "Kleiner Mann, große Wirkung", "Matt mit einem Bauern", (1, 3, 10, 25), False),
        ("Miniatur-Matt (≤ 20 Züge)", "Miniatur", "Matt in höchstens 20 Zügen", (1, 5, 15, 40), False),
        ("Schäfermatt", "Schäfer", "Damenmatt auf f7/f2 in den ersten 10 Zügen", (1, 3, 5, 10), False),
        ("Ersticktes Matt", "Erstickt", "Springermatt, der König steht zwischen eigenen Figuren", (1, 3, 5, 10), True),
        ("Doppelschach-Matt", "Zwei auf einen Streich", "Matt durch Doppelschach", (1, 3, 5, 10), True),
        ("Umwandlungs-Matt", "Krönung", "Matt mit dem Umwandlungszug", (1, 2, 3, 5), True),
        ("Rochade-Matt", "Burgtor zu", "Matt durch Rochade", (1, 2, 3, 5), True),
        ("En-passant-Matt", "Im Vorbeigehen", "Matt durch en passant", (1, 2, 3, 5), True),
    ],
    "Taktik & Material": [
        ("Materialgewinn-Zug (≥ 3 Punkte netto)", "Sammler", "Züge, die nach der Antwort mindestens 3 Punkte netto bringen", (10, 50, 150, 500), False),
        ("Dame netto gewonnen", "Damenraub", "Die gegnerische Dame ohne gleichwertige Gegenleistung gewonnen", (3, 10, 30, 100), False),
        ("Dame geschlagen", "Damenjäger", "Gegnerische Dame geschlagen (auch im Tausch)", (10, 50, 150, 400), False),
        ("Dame mit Bauer/Leichtfigur geschlagen", "David gegen Goliath", "Dame mit Bauer, Springer oder Läufer geschlagen", (3, 15, 40, 100), False),
        ("Springergabel", "Gabelstapler", "Springer greift zwei von König, Dame, Turm an", (3, 10, 30, 100), False),
        ("Königliche Gabel (König + Dame)", "Familienessen", "Springergabel auf König und Dame", (1, 5, 15, 40), False),
        ("Doppelschach", "Doppelt hält besser", "Zwei Figuren geben gleichzeitig Schach", (1, 5, 15, 40), False),
    ],
    "Stil & Spezialzüge": [
        ("Lange Rochade", "Lange Burg", "O-O-O gespielt", (5, 20, 60, 150), False),
        ("Kurze Rochade", "Kurze Burg", "O-O gespielt", (10, 40, 100, 250), False),
        ("Umwandlung", "Beförderung", "Einen Bauern umgewandelt", (3, 10, 30, 100), False),
        ("En passant", "Im Vorübergehen", "En passant geschlagen", (1, 5, 15, 40), False),
        ("Unterverwandlung", "Bescheidenheit", "In Springer, Läufer oder Turm umgewandelt", (1, 3, 5, 10), True),
    ],
    "Meilensteine": [
        ("Partien gespielt", "Am Brett", "Gespielte Partien", (50, 200, 500, 1500), False),
        ("Siege", "Sieger", "Gewonnene Partien", (25, 100, 250, 750), False),
        ("Sieg trotz ≥ 5 Punkten Rückstand", "Nie aufgeben", "Gewonnen, obwohl du 5+ Punkte Material hinten lagst", (1, 5, 15, 40), False),
        ("Giant Killer (+100 Elo besiegt)", "Giant Killer", "Gegner mit 100+ Elo mehr besiegt", (3, 10, 30, 100), False),
        ("Giant Killer XL (+200 Elo besiegt)", "Giant Killer XL", "Gegner mit 200+ Elo mehr besiegt", (1, 5, 15, 40), False),
        ("Sieg auf Zeit", "Uhrmacher", "Gegner hat die Zeit überschritten", (5, 20, 60, 150), False),
        ("Gegner gibt auf", "Weiße Fahne", "Gegner hat aufgegeben", (5, 20, 60, 150), False),
    ],
    "Engine-Abzeichen": [
        ("Partie ohne Patzer", "Saubere Weste", "Ganze Partie ohne Patzer laut Stockfish", (3, 10, 30, 100), False),
        ("Eiskalt (≥ 90 % Genauigkeit)", "Eiskalt", "Partie mit mindestens 90 % Genauigkeit", (1, 5, 15, 40), False),
    ],
}
TIERS = ["Bronze", "Silber", "Gold", "Legende"]
TIER_XP = [10, 25, 50, 100]
LEVELS = [(0, "♙", "Bauer"), (150, "♘", "Springer"), (350, "♗", "Läufer"), (700, "♖", "Turm"), (1200, "♕", "Dame"), (2000, "♔", "König")]



def tier_of(n, t):
    return sum(1 for x in t if n >= x)


def category(time_class, time_control, opp):
    if opp.lower().startswith("coach-"):
        return "Bots / Coach"
    if time_class == "bullet":
        return "1 Min"
    if time_class == "blitz":
        return "3–5 Min"
    if time_class == "rapid":
        return "10 Min" if str(time_control).startswith("600") else "30+ Min"
    return "Daily"


GRUPPEN_ENDE = ("Defense", "Opening", "Game", "Gambit", "Attack", "System")


def gruppe(name):
    """Grobe Eröffnungsgruppe, z. B. alle Varianten von "Sicilian Defense"."""
    words = name.split()
    for i, w in enumerate(words):
        if w in GRUPPEN_ENDE:
            return " ".join(words[:i + 1])
    return " ".join(words[:2]) if words else "Unbekannt"


def leistung(gs):
    """Leistungs-Elo: Ø Gegner-Elo + 400 × (Siege − Niederlagen) / Partien (ohne Coach-Partien)."""
    gs = [g for g in gs if g["cat"] != "Bots / Coach"]
    if not gs:
        return None
    opp = sum((g["black"] if g["color"] == "w" else g["white"])["rating"] for g in gs) / len(gs)
    w = sum(g["outcome"] == "W" for g in gs); l = sum(g["outcome"] == "L" for g in gs)
    return round(opp + 400 * (w - l) / len(gs))


# ---- Partien ----
games = []
for f in glob.glob("vcache/*.json"):
    g = json.load(open(f))
    if len(g["plies"]) <= 2:
        continue
    white_me = g["white"]["name"].lower() == ME
    me, op = (g["white"], g["black"]) if white_me else (g["black"], g["white"])
    g["color"] = "w" if white_me else "b"
    g["outcome"] = "W" if me["result"] == "win" else ("L" if op["result"] == "win" else "D")
    g["cat"] = category(g["time_class"], g["time_control"], op["name"])
    g["family"] = " ".join(g["opening"].split()[:3]) if g["opening"] else "Unbekannt"
    g["group"] = gruppe(g["opening"]) if g["opening"] else "Unbekannt"
    klassifiziere(g["plies"])
    codes = {g["white"]["result"], g["black"]["result"]} - {"win"}
    g["ende"] = next(iter(codes)) if len(codes) == 1 else "unbekannt"
    g["elo"] = partie_elo(g["plies"])
    games.append(g)
games.sort(key=lambda g: -(g.get("end") or 0))
known = {g["id"] for g in games}
fehler = {}
for g in games:
    for i, pl in enumerate(g["plies"][1:], 1):
        if (i % 2 == 1) == (g["color"] == "w") and pl["cls"] in FEHLER:
            fehler[f'{g["id"]}-{i}'] = pl["cls"]

# ---- Training ----
puzzles = []
for f in glob.glob("pcache/*.json"):
    p = json.load(open(f))
    if p["game"] not in known or p["id"] not in fehler:
        continue
    p["played"]["cls"] = fehler[p["id"]]
    gm = next(x for x in games if x["id"] == p["game"])
    ply = gm["plies"][p["ply"]]
    played = next((m for m in p["moves"] if m["uci"] == p["played"]["uci"]), None)
    # Matt-Stellung: gelöst, wenn ein Zug ein erzwungenes Matt behält; sonst innerhalb 5 Punkten vom besten Zug
    has_mate = any((m.get("m") or 0) > 0 for m in p["moves"])
    if played and has_mate and (played.get("m") or 0) > 0:
        continue  # gespielter Zug hielt das Matt: keine eindeutige Aufgabe
    if played and not has_mate and p["moves"][0]["w"] - played["w"] < 5:
        continue
    p["best16"] = {"uci": ply.get("best_uci"), "san": ply.get("best")}
    p["mode"] = "mate" if has_mate else "win"
    p["cat"], p["end"] = gm["cat"], gm.get("end")
    puzzles.append(p)
puzzles.sort(key=lambda p: (-(p["end"] or 0), p["ply"]))

# ---- Trophäen ----
cards, quests, xp, unlocked, total = [], [], 0, 0, 0
for fam, items in DEFS.items():
    for key, name, desc, t, secret in items:
        n = A.get(key, 0)
        k = tier_of(n, t)
        total += 1
        unlocked += k > 0
        xp += sum(TIER_XP[:k])
        nxt = t[k] if k < 4 else None
        hidden = secret and n == 0
        cards.append({"fam": fam, "key": key, "name": name, "desc": desc, "n": n, "k": k, "nxt": nxt,
                      "tiers": list(t), "secret": hidden, "ex": [] if hidden else EX.get(key, [])})
        if nxt and not hidden:
            quests.append({"name": name, "n": n, "nxt": nxt, "tier": TIERS[k], "p": n / nxt})
quests.sort(key=lambda q: -q["p"])
level = [l for l in LEVELS if xp >= l[0]][-1]
li = LEVELS.index(level)
nl = LEVELS[li + 1] if li + 1 < len(LEVELS) else None

K = D["kategorien"]
rapid = K.get("10 Min (Rapid)", {})
week_rapid = D["diese_woche"].get("10 Min (Rapid)", 0)
plan = [
    {"tag": "Wochenziel", "name": "5 Rapid-Partien (10 Min) diese Woche", "n": week_rapid, "nxt": 5},
    {"tag": "Neues Terrain", "name": "Erste 3-Minuten-Partie spielen", "n": K.get("3–5 Min (Blitz)", {}).get("Partien", 0), "nxt": 1},
    {"tag": "Rating", "name": "Rapid-Rating 600 erreichen", "n": D["ratings"].get("rapid", {}).get("aktuell", 0), "nxt": 600},
]
cat_rows = []
for src_name, label in [("1 Min (Bullet)", "1 Min"), ("3–5 Min (Blitz)", "3–5 Min"), ("10 Min (Rapid)", "10 Min"),
                        ("30+ Min (Rapid lang)", "30+ Min"), ("Bots / Coach", "Bots / Coach")]:
    v = K.get(src_name, {})
    ph = v.get("fehlerphase") or {}
    cat_rows.append({"cat": label, "n": v.get("Partien", 0), "W": v.get("W", 0), "D": v.get("D", 0), "L": v.get("L", 0),
                     "acc": v.get("genauigkeit"), "ppg": v.get("patzer_pro_partie"),
                     "phase": max(ph, key=ph.get) if ph else None,
                     "zeitnot": v.get("zeitnot_anteil") if v.get("engine_partien") else None,
                     "perf": leistung([g for g in games if g["cat"] == label])})

stand = datetime.date.today().strftime("%d.%m.%Y")
app = {
    "name": NAME, "stand": stand,
    "level": {"nr": li + 1, "piece": level[1], "title": level[2], "xp": xp, "from": level[0],
              "next": nl[0] if nl else None, "next_title": nl[2] if nl else None},
    "unlocked": unlocked, "total": total, "ratings": D["ratings"],
    "plan": plan, "ppg_rapid": rapid.get("patzer_pro_partie"), "quests": quests[:6],
    "cards": cards, "records": {k: v for k, v in D["rekorde"].items() if v not in (999, 0, None)},
    "cats": cat_rows, "openings": D["eroeffnungen"], "rochade": D["rochade"],
}
os.makedirs("app/data", exist_ok=True)
json.dump(app, open("app/data/app.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"games": games}, open("app/data/games.json", "w"), separators=(",", ":"))
json.dump({"puzzles": puzzles}, open("app/data/puzzles.json", "w"), separators=(",", ":"))
# vollständiger Cache aller bewerteten Stellungen (auch aussortierte), damit nichts neu gerechnet wird
json.dump({os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob("pcache/*.json")},
          open("app/data/puzzle_cache.json", "w"), separators=(",", ":"))
summary = {"name": NAME, "stand": stand, "level": li + 1, "level_titel": level[2], "xp": xp,
           "achievements": unlocked, "achievements_gesamt": total,
           "rapid": D["ratings"].get("rapid", {}).get("aktuell"), "bullet": D["ratings"].get("bullet", {}).get("aktuell"),
           "partien": A.get("Partien gespielt", 0), "siege": A.get("Siege", 0),
           "rapid_genauigkeit": rapid.get("genauigkeit"), "rapid_patzer_pro_partie": rapid.get("patzer_pro_partie"),
           "uebungsstellungen": len(puzzles)}
json.dump(summary, open("app/data/summary.json", "w"), ensure_ascii=False, indent=1)
print(f"{len(games)} Partien, {len(puzzles)} Übungsstellungen, Level {li + 1} {level[2]}, {unlocked}/{total}, {xp} XP")
for f in ("app.json", "games.json", "puzzles.json"):
    print(f, os.path.getsize("app/data/" + f) // 1024, "KB")
