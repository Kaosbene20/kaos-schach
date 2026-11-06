#!/usr/bin/env python3
"""Setzt die Seite zusammen: app/app_template.html + Figuren -> app/index.html"""
t = open("app/app_template.html").read()
s = open("app/pieces_sprite.svg").read()
open("app/index.html", "w").write(t.replace("<!--PIECES-->", s, 1))
print("app/index.html", len(t) + len(s), "Bytes")
