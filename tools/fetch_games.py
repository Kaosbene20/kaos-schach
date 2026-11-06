#!/usr/bin/env python3
"""Lädt alle Chess.com-Partien eines Spielers nach games.json. Nutzung: python3 fetch_games.py NAME"""
import json, sys, urllib.request

UA = {"User-Agent": "PerfectMe-ChessAnalyzer/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


name = sys.argv[1].lower()
games = []
for a in get(f"https://api.chess.com/pub/player/{name}/games/archives")["archives"]:
    games += get(a)["games"]
json.dump(games, open("games.json", "w"))
print(f"{len(games)} Partien gespeichert")
