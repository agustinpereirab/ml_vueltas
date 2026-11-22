"""Arma el informe final en PDF: figuras desde los resultados, HTML y PDF A4.

    py informe/armar_informe.py

1. Lee los resultados ya generados (`modelo/resultados/*.json`) y dibuja las figuras en SVG
   (`informe/fuente/svg/`). No recalcula nada: cada número sale de esos archivos.
2. Pega las figuras dentro de `informe/fuente/informe.html` (marcadores <!--SVG:nombre-->).
3. Imprime el PDF con Chromium (Playwright) en `informe/informe.pdf` y se detiene si pasa de
   6 páginas, el máximo de la consigna.

No necesita la tabla de datos. Además de requirements.txt, necesita Playwright con Chromium
(`pip install playwright` y `playwright install chromium`).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RESULTADOS = RAIZ / "modelo" / "resultados"
FUENTE = Path(__file__).resolve().parent / "fuente"
SVG = FUENTE / "svg"
SALIDA_HTML = FUENTE / "_armado.html"
SALIDA_PDF = Path(__file__).resolve().parent / "informe.pdf"
MAX_PAGINAS = 6

# Tokens (los mismos que el CSS del informe)
TINTA, TINTA2, TINTA3 = "#17202b", "#4a5562", "#6b7682"
LINEA, GRILLA = "#cfd5dc", "#e8ebef"
ACENTO = "#1d5b8f"      # el dato protagonista: el modelo, los grupos de H2, lo que se discute
GRIS = "#8f99a4"        # la referencia: el azar, los otros grupos
FONDO = "#ffffff"
SANS = "'Source Sans 3', 'Segoe UI', sans-serif"


def leer(nombre: str) -> dict:
    return json.loads((RESULTADOS / nombre).read_text(encoding="utf-8"))


def num(x: float, dec: int = 1) -> str:
    """Formato del informe: coma decimal, punto de miles."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(x: float, dec: int = 1) -> str:
    return num(100 * x, dec) + "%"


def texto(x, y, t, tam=10, peso=400, color=TINTA2, ancla="start", extra=""):
    t = t.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{tam}" '
            f'font-weight="{peso}" fill="{color}" text-anchor="{ancla}" '
            f'style="font-variant-numeric: tabular-nums" {extra}>{t}</text>')


def barra_h(x0, x1, yc, alto, color, extra=""):
    """Barra horizontal con el extremo de datos redondeado (4 px) y la base recta."""
    r = min(4, abs(x1 - x0) / 2)
    y0, y1 = yc - alto / 2, yc + alto / 2
    if x1 >= x0:
        d = (f"M{x0:.1f},{y0:.1f} H{x1 - r:.1f} Q{x1:.1f},{y0:.1f} {x1:.1f},{y0 + r:.1f} "
             f"V{y1 - r:.1f} Q{x1:.1f},{y1:.1f} {x1 - r:.1f},{y1:.1f} H{x0:.1f} Z")
    else:
        d = (f"M{x0:.1f},{y0:.1f} H{x1 + r:.1f} Q{x1:.1f},{y0:.1f} {x1:.1f},{y0 + r:.1f} "
             f"V{y1 - r:.1f} Q{x1:.1f},{y1:.1f} {x1 + r:.1f},{y1:.1f} H{x0:.1f} Z")
    return f'<path d="{d}" fill="{color}" {extra}/>'


def barra_v(xc, y0, y1, ancho, color, extra=""):
    """Columna que crece desde la base y0 hacia arriba hasta y1, con tapa redondeada."""
    r = min(4, abs(y0 - y1) / 2)
    x0, x1 = xc - ancho / 2, xc + ancho / 2
    d = (f"M{x0:.1f},{y0:.1f} V{y1 + r:.1f} Q{x0:.1f},{y1:.1f} {x0 + r:.1f},{y1:.1f} "
         f"H{x1 - r:.1f} Q{x1:.1f},{y1:.1f} {x1:.1f},{y1 + r:.1f} V{y0:.1f} Z")
    return f'<path d="{d}" fill="{color}" {extra}/>'


def svg(ancho, alto, cuerpo, titulo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
            f'width="{ancho}" height="{alto}" role="img" aria-label="{titulo}">'
            f'<title>{titulo}</title>{cuerpo}</svg>')


# ---------------------------------------------------------------- Figura 1: curva de captura
def figura_captura() -> str:
    p = leer("prueba.json")
    curva = [(0.0, 0.0)] + [(c["frac"], c["captura"]) for c in p["campania"]["curva"]]
    W, H = 330, 236
    L, R, T, B = 34, 12, 26, 34
    pw, ph = W - L - R, H - T - B
    X = lambda f: L + f * pw
    Y = lambda c: T + (1 - c) * ph
    o = []
    for v in (0, .2, .4, .6, .8, 1):
        o.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRILLA}" stroke-width="1"/>')
        o.append(texto(L - 6, Y(v) + 3.5, f"{int(v * 100)}%", 9, color=TINTA3, ancla="end"))
        o.append(texto(X(v), H - B + 14, f"{int(v * 100)}%", 9, color=TINTA3, ancla="middle"))
    o.append(texto(L - 30, 12, "Parte de las vueltas que entra en la lista", 9.5, 600, TINTA2))
    o.append(texto(L + pw / 2, H - 4, "Clientes seleccionados, de mayor a menor probabilidad", 9.5, 400, TINTA2, "middle"))
    # lo que agrega el modelo sobre el azar: lavado al 10 %
    poli = " ".join(f"{X(f):.1f},{Y(c):.1f}" for f, c in curva) + " " + \
           " ".join(f"{X(f):.1f},{Y(f):.1f}" for f, _ in reversed(curva))
    o.append(f'<polygon points="{poli}" fill="{ACENTO}" fill-opacity=".10"/>')
    o.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="{GRIS}" stroke-width="1.6" stroke-dasharray="5 4"/>')
    o.append(f'<polyline points="{" ".join(f"{X(f):.1f},{Y(c):.1f}" for f, c in curva)}" fill="none" '
             f'stroke="{ACENTO}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    c20 = p["campania"]["por_probabilidad"]
    cap20 = c20["captura"]
    # 20 %: modelo y azar. El rótulo va arriba a la izquierda, donde no hay curva, con una guía.
    o.append(f'<line x1="{X(.2):.1f}" x2="{X(.2):.1f}" y1="{Y(cap20):.1f}" y2="{Y(.2):.1f}" stroke="{TINTA3}" stroke-width="1"/>')
    o.append(f'<line x1="{X(.2):.1f}" x2="{X(.2):.1f}" y1="{Y(cap20) - 6:.1f}" y2="{Y(.6):.1f}" stroke="{TINTA3}" stroke-width="1"/>')
    o.append(f'<circle cx="{X(.2):.1f}" cy="{Y(.2):.1f}" r="3.6" fill="{GRIS}" stroke="{FONDO}" stroke-width="2"/>')
    o.append(f'<circle cx="{X(.2):.1f}" cy="{Y(cap20):.1f}" r="4.4" fill="{ACENTO}" stroke="{FONDO}" stroke-width="2"/>')
    o.append(texto(X(0) + 6, Y(.86), "Al seleccionar el 20% de mayor probabilidad", 9, 400, TINTA2))
    o.append(texto(X(0) + 6, Y(.86) + 15, f"{pct(cap20)} de las vueltas", 12, 700, TINTA))
    captura_regla = p["evaluacion"]["regla_acompaniante"]["captura_20"]
    o.append(texto(X(0) + 6, Y(.86) + 28,
                   f"Regla del acompañante: {pct(captura_regla)}", 9, 400, TINTA2))
    o.append(texto(X(.2) + 7, Y(.2) + 11, "al azar: 20%", 9, 400, TINTA3))
    # leyenda abajo a la derecha, bajo la diagonal
    lx, ly = X(.58), Y(.13)
    o.append(f'<line x1="{lx}" x2="{lx + 18}" y1="{ly}" y2="{ly}" stroke="{ACENTO}" stroke-width="2"/>')
    o.append(texto(lx + 24, ly + 3.5, "Modelo principal", 9.5, 400, TINTA2))
    o.append(f'<line x1="{lx}" x2="{lx + 18}" y1="{ly + 15}" y2="{ly + 15}" stroke="{GRIS}" stroke-width="1.6" stroke-dasharray="5 4"/>')
    o.append(texto(lx + 24, ly + 18.5, "Selección al azar", 9.5, 400, TINTA2))
    return svg(W, H, "".join(o), "Curva de captura del modelo principal en la prueba")


# ---------------------------------------------------------------- Figura 2: aporte por grupo
GRUPOS = [  # (clave en el JSON, rótulo, es de H2)
    ("H2 · compañía previa", "Compañía previa", True),
    ("Datos de contacto (día 0)", "Contacto del registro inicial", False),
    ("Viaje", "Viaje", False),
    ("H2 · vendedor", "Vendedor", True),
    ("Montos", "Montos", False),
    ("Producto", "Producto", False),
    ("H2 · destino", "Destino", True),
]


def figura_grupos() -> str:
    d = leer("interpretacion_validacion.json")["bootstrap"]["diferencias"]
    W, H = 330, 236
    L, R, T, B = 118, 34, 26, 50
    pw, ph = W - L - R, H - T - B
    lo, hi = -0.01, 0.08
    X = lambda v: L + (v - lo) / (hi - lo) * pw
    fila = ph / len(GRUPOS)
    o = []
    for v in (0, .02, .04, .06, .08):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{T + ph}" '
                 f'stroke="{TINTA3 if v == 0 else GRILLA}" stroke-width="1"/>')
        o.append(texto(X(v), T + ph + 13, num(v, 2), 9, color=TINTA3, ancla="middle"))
    o.append(texto(8, 12, "PR-AUC que pierde el modelo sin cada grupo", 9.5, 600, TINTA2))
    for i, (clave, rotulo, h2) in enumerate(GRUPOS):
        iv = d[f"completo - sin · {clave}"]["pr_auc"]
        yc = T + fila * (i + .5)
        o.append(texto(L - 8, yc + 3.5, rotulo, 9.5, 600 if h2 else 400, TINTA if h2 else TINTA2, "end"))
        o.append(barra_h(X(0), X(iv["punto"]), yc, 12, ACENTO if h2 else GRIS))
        o.append(f'<line x1="{X(iv["desde"]):.1f}" x2="{X(iv["hasta"]):.1f}" y1="{yc:.1f}" y2="{yc:.1f}" stroke="{TINTA}" stroke-width="1.2"/>')
        for e in (iv["desde"], iv["hasta"]):
            o.append(f'<line x1="{X(e):.1f}" x2="{X(e):.1f}" y1="{yc - 3:.1f}" y2="{yc + 3:.1f}" stroke="{TINTA}" stroke-width="1.2"/>')
        o.append(texto(X(max(iv["hasta"], 0)) + 5, yc + 3.5, num(iv["punto"], 3), 9, 600 if h2 else 400, TINTA2))
    ly = H - 12
    o.append(f'<rect x="{L - 100}" y="{ly - 8}" width="10" height="10" rx="2" fill="{ACENTO}"/>')
    o.append(texto(L - 86, ly + 1, "grupo de la hipótesis 2", 9, 400, TINTA2))
    o.append(f'<rect x="{L + 30}" y="{ly - 8}" width="10" height="10" rx="2" fill="{GRIS}"/>')
    o.append(texto(L + 44, ly + 1, "otro grupo · línea: intervalo del 95%", 9, 400, TINTA2))
    return svg(W, H, "".join(o), "PR-AUC que pierde la logística sin cada grupo de variables, en validación")


# ---------------------------------------------------------------- Cada variable sola
GRUPOS_H2 = ("H2 · compañía previa", "H2 · vendedor", "H2 · destino")


def figura_variables(n=10) -> str:
    d = leer("variables_solas.json")["variables"]
    modelo = next(f for f in d if f["grupo"] == "modelo")
    filas = [f for f in d if f["grupo"] != "modelo"][:n]
    W, H = 330, 236
    L, R, T, B = 150, 30, 26, 44
    pw, ph = W - L - R, H - T - B
    lo, hi = 0.5, 0.67
    X = lambda v: L + (v - lo) / (hi - lo) * pw
    fila = ph / len(filas)
    o = [texto(8, 12, "ROC-AUC de cada variable sola (validación)", 9.5, 600, TINTA2)]
    for v in (0.5, 0.55, 0.6, 0.65):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{T + ph}" stroke="{TINTA3 if v == 0.5 else GRILLA}" stroke-width="1"/>')
        o.append(texto(X(v), T + ph + 13, num(v, 2), 9, color=TINTA3, ancla="middle"))
    for i, f in enumerate(filas):
        yc = T + fila * (i + .5)
        h2 = f["grupo"] in GRUPOS_H2
        nombre = f["nombre"].replace(" cargado el día 0", " en registro inicial")
        o.append(texto(L - 8, yc + 3.5, nombre, 9, 600 if h2 else 400, TINTA if h2 else TINTA2, "end"))
        o.append(barra_h(X(0.5), X(f["roc_auc"]["punto"]), yc, 9, ACENTO if h2 else GRIS))
        o.append(texto(X(f["roc_auc"]["punto"]) + 4, yc + 3.2, num(f["roc_auc"]["punto"], 3), 8.5, 400, TINTA2))
    xm = X(modelo["roc_auc"]["punto"])
    o.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{T - 4}" y2="{T + ph}" stroke="{TINTA}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    o.append(texto(xm - 4, H - 6, f"las 29 juntas: {num(modelo['roc_auc']['punto'], 3)}", 9, 700, TINTA, "end"))
    return svg(W, H, "".join(o), "ROC-AUC en validación de cada variable por separado, contra el modelo completo")


# ---------------------------------------------------------------- Calibración por decil, prueba
def figura_calibracion() -> str:
    p = leer("prueba.json")
    W, H = 330, 236
    L, R, T, B = 40, 14, 26, 36
    pw, ph = W - L - R, H - T - B
    maximo = 0.6
    X = lambda v: L + v / maximo * pw
    Y = lambda v: T + (1 - v / maximo) * ph
    o = [texto(8, 12, "Vuelven, por decil de probabilidad (prueba)", 9.5, 600, TINTA2)]
    for v in (0, .1, .2, .3, .4, .5, .6):
        o.append(f'<line x1="{L}" x2="{L + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRILLA}" stroke-width="1"/>')
        o.append(texto(L - 6, Y(v) + 3.5, f"{int(v * 100)}%", 9, color=TINTA3, ancla="end"))
        o.append(texto(X(v), T + ph + 13, f"{int(v * 100)}%", 9, color=TINTA3, ancla="middle"))
    o.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(maximo)}" y2="{Y(maximo)}" stroke="{TINTA3}" stroke-width="1.2" stroke-dasharray="4 4"/>')
    o.append(texto(X(.49), Y(.53), "predicho = observado", 8.5, 400, TINTA3, "end"))
    for clave, color, rot in (("principal_sin_recalibrar", GRIS, "sin recalibrar"), ("principal", ACENTO, "recalibrada con 2024")):
        pts = [(x["p_media"], x["observada"]) for x in p["deciles"][clave]]
        o.append(f'<polyline points="{" ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts)}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for a, b in pts:
            o.append(f'<circle cx="{X(a):.1f}" cy="{Y(b):.1f}" r="3.6" fill="{color}" stroke="{FONDO}" stroke-width="1.6"/>')
    ly = T + 12
    for i, (color, rot) in enumerate(((ACENTO, "recalibrada con 2024"), (GRIS, "sin recalibrar"))):
        o.append(f'<line x1="{L + 8}" x2="{L + 24}" y1="{ly + i * 14}" y2="{ly + i * 14}" stroke="{color}" stroke-width="2"/>')
        o.append(texto(L + 30, ly + i * 14 + 3.5, rot, 9, 400, TINTA2))
    o.append(texto(L + pw / 2, H - 4, "Probabilidad media predicha en el decil", 9.5, 400, TINTA2, "middle"))
    return svg(W, H, "".join(o), "Calibración por decil en la prueba: la tasa observada queda por debajo de la predicha")


# ---------------------------------------------------------------- Figura 3: deriva
def figura_deriva() -> str:
    c = leer("carga_contacto.json")["bloques"]
    p = leer("prueba.json")["evaluacion"]
    años = [("entrenamiento", "2023"), ("validacion", "2024"), ("prueba", "ene–ago 2025*")]
    W, H = 660, 184
    o = [f'<defs><pattern id="rayado" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         f'<rect width="5" height="5" fill="{ACENTO}"/><line x1="0" y1="0" x2="0" y2="5" stroke="{FONDO}" stroke-width="1.6" stroke-opacity=".55"/></pattern></defs>']
    T, B = 30, 30
    ph = H - T - B

    # (a) carga del mail
    x0, pw = 8, 150
    Y = lambda v: T + (1 - v) * ph
    o.append(texto(x0, 12, "a · Mail en el registro inicial", 9.5, 600, TINTA2))
    o.append(f'<line x1="{x0}" x2="{x0 + pw}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{TINTA3}" stroke-width="1"/>')
    for i, (k, et) in enumerate(años):
        v = c[k]["d0_tiene_mail"]["tienen"]
        xc = x0 + pw * (i + .5) / 3
        o.append(barra_v(xc, Y(0), Y(v), 24, "url(#rayado)" if k == "prueba" else ACENTO))
        o.append(texto(xc, Y(v) - 5, pct(v), 10, 700, TINTA, "middle"))
        o.append(texto(xc, Y(0) + 13, et, 9, 400, TINTA3, "middle"))

    # (b) vuelven con y sin mail
    x0, pw = 196, 176
    Y = lambda v: T + (1 - v / 0.35) * ph
    o.append(texto(x0, 12, "b · Vuelven, según tengan mail cargado", 9.5, 600, TINTA2))
    for v in (0, .1, .2, .3):
        o.append(f'<line x1="{x0 + 22}" x2="{x0 + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRILLA if v else TINTA3}" stroke-width="1"/>')
        o.append(texto(x0 + 18, Y(v) + 3.5, f"{int(v * 100)}%", 9, color=TINTA3, ancla="end"))
    xs = [x0 + 36 + i * 46 for i in range(3)]
    for clave, color, rot in (("vuelven_con", ACENTO, "con mail"), ("vuelven_sin", GRIS, "sin mail")):
        vals = [c[k]["d0_tiene_mail"][clave] for k, _ in años]
        o.append(f'<polyline points="{" ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, vals))}" fill="none" '
                 f'stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for x, v in zip(xs, vals):
            o.append(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="4" fill="{color}" stroke="{FONDO}" stroke-width="2"/>')
        o.append(texto(xs[0], Y(vals[0]) - 8, pct(vals[0]), 9, 600, TINTA2, "middle"))
        o.append(texto(xs[-1] + 9, Y(vals[-1]) + 3.5, f"{pct(vals[-1])} {rot}", 9, 600, TINTA2))
    for x, (_, et) in zip(xs, años):
        o.append(texto(x, Y(0) + 13, et.replace("ene–ago ", "").replace("*", "*"), 9, 400, TINTA3, "middle"))

    # (c) probabilidad media en la prueba
    x0, pw = 410, 225
    LL = 100
    X = lambda v: x0 + LL + v / 0.34 * (pw - LL)
    o.append(texto(x0, 12, "c · Prueba: probabilidad media predicha", 9.5, 600, TINTA2))
    filas = [("Sin recalibrar", p["principal_sin_recalibrar"]["p_media"], GRIS),
             ("Recalibrada (2024)", p["principal"]["p_media"], ACENTO),
             ("Sin datos de contacto", p["sin_contacto"]["p_media"], GRIS)]
    for i, (rot, v, color) in enumerate(filas):
        yc = T + 14 + i * 34
        o.append(texto(X(0) - 6, yc + 3.5, rot, 9, 400, TINTA2, "end"))
        o.append(barra_h(X(0), X(v), yc, 12, color))
        o.append(texto(X(v) + 5, yc + 3.5, pct(v), 9.5, 700 if color == ACENTO else 400, TINTA2))
    obs = p["principal"]["tasa_observada"]
    o.append(f'<line x1="{X(obs):.1f}" x2="{X(obs):.1f}" y1="{T}" y2="{T + 104}" stroke="{TINTA}" stroke-width="1.2" stroke-dasharray="3 3"/>')
    o.append(texto(X(obs), T + 117, f"volvió el {pct(obs)}", 9.5, 700, TINTA, "middle"))
    o.append(texto(x0, H - 6, "", 9))
    return svg(W, H, "".join(o), "Carga del mail por cohorte, vuelta con y sin mail, y probabilidad media en la prueba")


def main() -> None:
    SVG.mkdir(exist_ok=True)
    figuras = {"captura": figura_captura(), "grupos": figura_grupos(), "deriva": figura_deriva(),
               "variables": figura_variables(), "calibracion": figura_calibracion()}
    for nombre, contenido in figuras.items():
        (SVG / f"{nombre}.svg").write_text(contenido, encoding="utf-8")

    html = (FUENTE / "informe.html").read_text(encoding="utf-8")
    html = re.sub(r"<!--SVG:(\w+)-->", lambda m: figuras[m.group(1)], html)
    if "<!--SVG:" in html:
        sys.exit("Quedó un marcador de figura sin reemplazar.")
    SALIDA_HTML.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    pie = ('<div style="width:100%;font:7.5pt Segoe UI,sans-serif;color:#6b7682;padding:0 17mm;'
           'display:flex;justify-content:space-between"><span>¿Vuelve a viajar? · Aprendizaje Automático I · '
           'Informe del proyecto final</span><span><span class="pageNumber"></span> / '
           '<span class="totalPages"></span></span></div>')
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page()
        pag.goto(SALIDA_HTML.as_uri())
        pag.evaluate("document.fonts.ready")
        pag.pdf(path=str(SALIDA_PDF), format="A4", print_background=True, prefer_css_page_size=True,
                display_header_footer=True, header_template="<span></span>", footer_template=pie,
                margin={"top": "13mm", "bottom": "15mm", "left": "17mm", "right": "17mm"})
        nav.close()
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", SALIDA_PDF.read_bytes()))
    print(f"{SALIDA_PDF.relative_to(RAIZ)}: {paginas} páginas")
    if paginas > MAX_PAGINAS:
        sys.exit(f"Pasa del máximo de {MAX_PAGINAS} páginas.")


if __name__ == "__main__":
    main()
