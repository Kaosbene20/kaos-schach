#!/usr/bin/env python3
"""Setzt die Seite zusammen: app/app_template.html + Figuren + Repertoire-Bereich (rep/rep_template.html, rep/rep.json) -> app/index.html"""
import re

t = open("app/app_template.html").read()
s = open("app/pieces_sprite.svg").read()
r = open("rep/rep_template.html").read()
data = open("rep/rep.json").read()

# --- CSS des Repertoires auf den Bereich #v-repertoire begrenzen ---
css = r[r.index("<style>") + 7:r.index("</style>")]
SKIP = (":root", "*", "body", "button, select", ":focus-visible", ".mono")


def scope(block):
    out, i = [], 0
    while i < len(block):
        j = block.find("{", i)
        if j < 0:
            break
        sel = block[i:j].strip()
        if sel.startswith("@media"):
            depth, k = 1, j + 1
            while depth:
                depth += {"{": 1, "}": -1}.get(block[k], 0); k += 1
            inner = block[j + 1:k - 1]
            if "prefers-color-scheme" not in sel:
                out.append(sel + " {" + scope(inner) + "}")
            i = k
            continue
        k = block.index("}", j)
        body = block[j + 1:k]
        if sel not in SKIP and not sel.startswith(":root"):
            out.append(", ".join("#v-repertoire " + x.strip() for x in sel.split(",")) + " {" + body + "}")
        i = k + 1
    return "\n".join(out)


rcss = ("#v-repertoire { --plan:var(--c-great); --ok:var(--c-best); --bad:var(--c-blunder); --warn:var(--c-inaccuracy) }\n"
        "#v-repertoire .rwrap { display:grid; gap:18px }\n#v-repertoire ol.steps .why { border:0; padding:0 }\n" + scope(css).replace("#v-repertoire .wrap", "#v-repertoire .rwrap"))

# --- Markup: nur der Inhalt, IDs mit Präfix rp- ---
html = r[r.index('<div class="wrap">'):r.index("<script>")].strip()
html = html.replace('<div class="wrap">', '<div class="rwrap">', 1)
html = re.sub(r'\b(id|for|aria-labelledby)="([^"]+)"', lambda m: f'{m.group(1)}="rp-{m.group(2)}"', html)
html = html.replace("<h1>", '<h2 class="rh1">').replace("</h1>", "</h2>")
rcss += "\n#v-repertoire header .rh1 { font-family:var(--display); font-weight:800; font-size:clamp(1.2rem, 2.6vw, 1.7rem); margin:0; letter-spacing:-.01em; text-wrap:balance }"

# --- Skript: eigener Bereich, Hash r-<linie>, Pfeiltasten nur wenn sichtbar ---
js = r[r.index("<script>") + 8:r.index("</script>")]
rep = [
    ('const $ = id => document.getElementById(id);', 'const $ = id => document.getElementById("rp-" + id);\n  const visible = () => !document.getElementById("v-repertoire").hidden;'),
    ('try { history.replaceState(null, "", "#" + S.line.id); } catch (_) {}', 'if (visible()) try { history.replaceState(null, "", "#r-" + S.line.id); } catch (_) {}'),
    ('document.addEventListener("keydown", e => { if (S.mode === "play") return;', 'document.addEventListener("keydown", e => { if (S.mode === "play" || !visible()) return;'),
    ('const h = (location.hash || "").slice(1);', 'const h = (location.hash || "").replace(/^#r-/, "");'),
    ('const DATA = /*DATA*/null;', 'const DATA = ' + data + ';'),
]
for a, b in rep:
    assert js.count(a) == 1, a
    js = js.replace(a, b)

# --- in die App einsetzen ---
ins = [
    ('</style>', rcss + "\n</style>"),
    ('    <a href="#trophaeen" data-v="trophaeen">Trophäen</a>', '    <a href="#trophaeen" data-v="trophaeen">Trophäen</a>\n    <a href="#repertoire" data-v="repertoire">Repertoire</a>'),
    ('<!-- PARTIEN -->', '<!-- REPERTOIRE -->\n  <section class="view" id="v-repertoire" aria-label="Repertoire" hidden>\n' + html + '\n  </section>\n\n  <!-- PARTIEN -->'),
    ('["partien","training","trophaeen"].forEach(x =>', '["partien","training","trophaeen","repertoire"].forEach(x =>'),
    ('if (v === "trophaeen") { renderTrophies(); setHash("trophaeen"); }', 'if (v === "trophaeen") { renderTrophies(); setHash("trophaeen"); }\n    if (v === "repertoire") window.__repOpen && window.__repOpen();'),
    ('if (h === "training" || h === "trophaeen" || h === "partien") { go(h); return; }', 'if (h === "training" || h === "trophaeen" || h === "partien" || h === "repertoire") { go(h); return; }\n    if (/^r-/.test(h)) { go("repertoire"); window.__repSelect && window.__repSelect(h.slice(2)); return; }'),
    ('</script>', '</script>\n<script>' + js.replace('openLine(DATA.lines.some(l => l.id === h) ? h : DATA.lines[0].id);',
        'openLine(DATA.lines.some(l => l.id === h) ? h : DATA.lines[0].id);\n  window.__repOpen = () => { try { history.replaceState(null, "", "#r-" + S.line.id); } catch (_) {} };\n  window.__repSelect = id => { if (DATA.lines.some(l => l.id === id) && S.line.id !== id) openLine(id); };') + '</script>'),
]
for a, b in ins:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
assert 'window.__repOpen = ' in t
t = t.replace("<!--PIECES-->", s, 1)
open("app/index.html", "w").write(t)
open("rep/index.html", "w").write(r.replace("<!--PIECES-->", s).replace("/*DATA*/null", data))
print("app/index.html", len(t), "Bytes")
