import json, math, chess, chess.engine
# side: "b" oder "w" = deine Farbe; moves: SAN; notes: {Halbzug-Index(1-basiert): Kommentar}; plan: Pfeile am Ende
LINES = [
 dict(id="b-haupt", side="b", group="Schwarz · Grundaufbau", title="Gegen 2.Nf3 – Beschleunigter Drache",
  moves="e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6 Nc3 Bg7 Be3 Nf6 Bc4 O-O Bb3 d6 f3 Bd7 Qd2 Rc8",
  notes={2:"Sizilianisch: c5 kämpft um d4, ohne die Mitte sofort zu öffnen.",4:"Erst Springer raus – Figur vor Dame.",8:"…g6: der Läufer kommt nach g7, die lange Diagonale ist dein Motor.",10:"Lg7 zielt durch bis b2 – nach jedem Springerabzug von d4 wird das spürbar.",12:"Sf6 greift e4 an und deckt den König.",14:"Kurze Rochade in Zug 7 – König sicher, Turm kommt ins Spiel.",16:"…d6 öffnet den Läufer c8.",18:"Ld7 bereitet …Tc8 vor.",20:"Tc8: Druck auf der halboffenen c-Linie gegen c3 und den weißen König, falls er lang rochiert."},
  plan=[("c6e5","Se5 → c4 tauscht den starken Lb3 oder die Dame"),("a7a5","…a5–a4 jagt den Lb3"),("g7c3","Lange Diagonale: …Txc3 als Qualitätsopfer")]),
 dict(id="b-ruhig", side="b", group="Schwarz · Grundaufbau", title="Gegen 2.Nc3 / 2.d3 – ruhiger Aufbau",
  moves="e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6 f4 e6 Nf3 Nge7 O-O O-O Be3 Rb8",
  notes={4:"Gleicher Aufbau: Sc6, g6, Lg7, d6.",12:"…e6 + Sge7: so bleibt f5 kontrolliert und der Lg7 frei.",16:"Kurze Rochade in Zug 8.",18:"Tb8: Startschuss für den Damenflügel-Angriff."},
  plan=[("b7b5","…b5–b4 vertreibt den Sc3"),("c5c4","…c4 öffnet Linien gegen den König auf g1"),("g7b2","Lg7 drückt auf b2")]),
 dict(id="b-bc4", side="b", group="Schwarz · Ausnahmen", title="Ausnahme 2.Bc4 – erst …e6, dann …d5",
  moves="e4 c5 Bc4 e6 Nc3 Nc6 Nf3 d5 exd5 exd5 Bb5 Nf6 O-O Be7 d4 O-O",
  notes={4:"…e6 macht den Läufer c4 stumm (f7 ist gedeckt) und bereitet …d5 vor.",8:"…d5 mit Tempo auf den Läufer – nur weil e6 dahinter steht.",10:"Zurückschlagen zuerst! (In deiner Partie kam hier 5…d5?? ohne e6.)",16:"Rochade in Zug 8, alles entwickelt."},
  plan=[]),
 dict(id="b-alapin", side="b", group="Schwarz · Ausnahmen", title="Ausnahme 2.c3 (Alapin) – …Nf6",
  moves="e4 c5 c3 Nf6 e5 Nd5 d4 cxd4 cxd4 d6 Nf3 Nc6",
  notes={4:"…Sf6 greift e4 an, bevor Weiß d4 spielt.",6:"Sd5 steht zentral und kann nicht von einem Bauern vertrieben werden.",10:"…d6 greift die Spitze e5 an.",12:"Danach …g6, …Lg7, …O-O wie gewohnt."},
  plan=[("g7g6","…g6 und Lg7 – zurück im Grundaufbau")]),
 dict(id="b-morra", side="b", group="Schwarz · Ausnahmen", title="Ausnahme Morra 2.d4 cxd4 3.c3 – …Nf6",
  moves="e4 c5 d4 cxd4 c3 Nf6 e5 Nd5 cxd4 d6 Nf3 Nc6",
  notes={6:"Gambit nicht nehmen: …Sf6 führt in die Alapin-Stellung.",8:"Gleiche Idee wie gegen 2.c3.",12:"Entwickeln, dann …g6/…Lg7 oder …e6/…Le7, kurz rochieren."},
  plan=[]),
 dict(id="b-dame", side="b", group="Schwarz · Ausnahmen", title="Ausnahme früher Damenzug – Tempo gewinnen",
  moves="e4 c5 d4 cxd4 Qxd4 Nc6 Qe3 g6 Nc3 Bg7",
  notes={6:"…Sc6 mit Tempo auf die Dame – Figur entwickeln UND angreifen.",8:"Zurück im Grundaufbau. Gegen 2.Dg4: 2…Sf6 3.Dg3 Sxe4 gewinnt einen Bauern; gegen 2.Dh5: 2…Sc6 (nicht 2…Sf6?? Dxc5)."},
  plan=[]),
 dict(id="w-drache", side="w", group="Weiß · Angriff mit langer Rochade", title="Gegen den Drachen – Le3, Dd2, f3, O-O-O",
  moves="e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O Qd2 Nc6 O-O-O Bd7 g4 Rc8 h4",
  notes={11:"Le3: Teil 1 des Musters, deckt d4 und will nach h6.",13:"f3: hält …Sg4 auf und stützt g4.",15:"Dd2: verbindet Le3 und Dame Richtung h6.",17:"Lange Rochade – erst JETZT, weil Schwarz kurz rochiert hat und die Mitte zu ist.",19:"g4: Bauernsturm, der König steht ja auf der anderen Seite.",21:"h4–h5 öffnet die h-Linie gegen den schwarzen König."},
  plan=[("e3h6","Lh6 tauscht den Drachen-Läufer g7"),("h4h5","h5 und hxg6: die h-Linie geht auf"),("c1b1","Kb1: Sicherheit gegen …Txc3")]),
 dict(id="w-pirc", side="w", group="Weiß · Angriff mit langer Rochade", title="Gegen Pirc / Modern – gleiches Muster",
  moves="e4 d6 d4 Nf6 Nc3 g6 Be3 Bg7 Qd2 O-O f3 c6 O-O-O b5 h4",
  notes={7:"Le3 + Dd2: das Muster greift auch hier (gegen Pirc: 1 Sieg, 3 Niederlagen bisher).",11:"f3 sichert e4.",13:"Lange Rochade, Schwarz steht schon kurz.",15:"h4–h5 sofort, Schwarz greift mit …b5 am anderen Flügel an – Tempo zählt."},
  plan=[("e3h6","Lh6 tauscht g7"),("h4h5","h5: Linien öffnen")]),
]
EXC = {"b":[
  ("2.Lc4","…e6 und dann …d5 – der Läufer zielt ins Leere"),
  ("2.c3 oder Morra 2.d4 cxd4 3.c3","…Sf6, nach e5 …Sd5"),
  ("2.Dg4 / 2.Dh5 / 3.Dxd4","Dame mit Tempo angreifen: …Sf6 bzw. …Sc6 – nie …Sf6 gegen Dh5"),
  ("Weiß rochiert lang und stürmt","nicht passiv werden: …Tc8, …Se5–c4, …a5/…b5 – wer schneller ist, gewinnt"),
 ], "w":[
  ("Gegner hat nicht kurz rochiert","keine lange Rochade – erst entwickeln, König kurz in Sicherheit"),
  ("Mitte geht auf (…d5 oder …e5 mit Bauerntausch)","kurz rochieren: offene Linien in der Mitte treffen den König auf c1"),
  ("Schwarz ist am Damenflügel schneller (…b5–b4, offene c-Linie)","Kb1 und Verteidiger (Sc3, Ld3) vor dem eigenen Angriff"),
  ("Gegner spielt 1…e5 / 1…d5","Muster passt nicht, normale Entwicklung (Italienisch)"),
 ]}
E = chess.engine.SimpleEngine.popen_uci(["node", "node_modules/stockfish/bin/stockfish-19-lite-single.js"])
def wcp(b):
    s = E.analyse(b, chess.engine.Limit(depth=16))["score"].white()
    return s.score(mate_score=10000)
out = []
for L in LINES:
    b = chess.Board(); plies = [{"fen": b.fen()}]
    for k, san in enumerate(L["moves"].split(), 1):
        legal = [m.uci() for m in b.legal_moves]
        mv = b.parse_san(san); s = b.san(mv); b.push(mv)
        plies.append({"san": s, "uci": mv.uci(), "fen": b.fen(), "legal": legal, "note": L["notes"].get(k, "")})
    for u, _ in L["plan"]:
        assert chess.Board(b.fen()).piece_at(chess.parse_square(u[:2])) is not None, (L["id"], u)
    cp = wcp(b)
    out.append({k: L[k] for k in ("id", "side", "group", "title")} | {"plies": plies, "plan": [{"uci": u, "text": t} for u, t in L["plan"]], "cp": cp})
    print(L["id"], len(plies) - 1, cp)
E.quit()
json.dump({"lines": out, "exc": EXC}, open("rep/rep.json", "w"), ensure_ascii=False)
