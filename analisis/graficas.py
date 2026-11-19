"""Graficas de exploracion de la tabla del modelo.

    py analisis/graficas.py

Lee SOLO `datos/tabla_modelo.csv` (la tabla anonimizada) y escribe
`analisis/exploracion.html`, un archivo autonomo: sin red, sin librerias.

Todo lo que mira la etiqueta usa unicamente el bloque de entrenamiento
(cohorte 2023): validacion y prueba no se miran para explorar. Ninguna
grafica muestra un grupo de menos de 50 clientes, y no hay graficas por
vendedor (regla del repo de cohortes: los vendedores no se ordenan).
"""
import collections
import csv
import html
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from exportacion import reglas as R  # noqa: E402

TABLA = os.path.join(REPO, "datos", "tabla_modelo.csv")
SALIDA = os.path.join(REPO, "analisis", "exploracion.html")
SD = R.SIN_DATO
MINIMO = 50                      # clientes para mostrar una categoria

GRUPOS = [
    ("La compañía", [
        ("viajes_previos_acompaniante", "Viajes previos como acompañante"),
        ("fue_acompaniante_antes", "Viajó antes como acompañante"),
        ("viaja_con_alguien_con_historial", "Viaja con alguien que ya tenía historial"),
        ("viaja_con_cliente_previo", "Viaja con un cliente previo"),
        ("pasajeros", "Pasajeros")]),
    ("La compra", [
        ("venta_usd", "Venta (USD)"),
        ("venta_por_pasajero_usd", "Venta por pasajero (USD)"),
        ("utilidad_indice", "Utilidad (índice)"),
        ("tipo_producto", "Tipo de producto"),
        ("aerolinea", "Aerolínea"),
        ("regimen_hotel", "Régimen del hotel"),
        ("lleva_hotel", "Lleva hotel"),
        ("tiene_seguro", "Tiene seguro"),
        ("servicios", "Cantidad de servicios"),
        ("canje_millas", "Canje de millas"),
        ("pagador", "Quién pagó")]),
    ("El viaje", [
        ("region_destino", "Región de destino"),
        ("pais_destino", "País de destino"),
        ("destinos", "Cantidad de destinos"),
        ("noches", "Noches"),
        ("anticipacion", "Anticipación (días)")]),
    ("El vendedor", [
        ("vendedor_fichas_12m", "Fichas del vendedor en los 12 meses previos"),
        ("vendedor_antiguedad", "Antigüedad del vendedor (años)"),
        ("vendedor_es_persona", "El vendedor es una persona")]),
    ("Ficha única (estado de hoy)", [
        ("fu_tiene_mail", "Tiene mail"),
        ("fu_tiene_telefono", "Tiene teléfono"),
        ("fu_tiene_documento", "Tiene documento"),
        ("fu_tiene_nacimiento", "Tiene fecha de nacimiento"),
        ("fu_registros", "Registros de la persona")]),
    ("Ficha del día 0", [
        ("d0_tiene_mail", "Tiene mail"),
        ("d0_tiene_telefono", "Tiene teléfono"),
        ("d0_tiene_documento", "Tiene documento"),
        ("d0_tiene_nacimiento", "Tiene fecha de nacimiento")]),
]
ETIQUETA = {c: e for _, cs in GRUPOS for c, e in cs}
PREFIJO = {"Ficha única (estado de hoy)": "Ficha única: ", "Ficha del día 0": "Día 0: "}
NOMBRE = {c: PREFIJO.get(g, "") + e for g, cs in GRUPOS for c, e in cs}
NOMBRE["vuelve_12"] = "Vuelve en 12 meses"
NUMERICAS = ["venta_usd", "venta_por_pasajero_usd", "utilidad_indice"]
NOMINALES = ["pagador", "tipo_producto", "regimen_hotel", "aerolinea", "region_destino", "pais_destino"]
CONTRATO = dict(R.CONTRATO)
PAISES = {"BR": "Brasil", "AR": "Argentina", "ES": "España", "US": "Estados Unidos", "MX": "México",
          "CL": "Chile", "DO": "Rep. Dominicana", "UY": "Uruguay", "IT": "Italia", "CO": "Colombia",
          "GE": "Alemania", "PE": "Perú", "GB": "Reino Unido", "PY": "Paraguay"}
BONITO = {
    "brasil": "Brasil", "sudamerica": "Sudamérica (resto)", "europa": "Europa",
    "caribe": "Caribe y Centroamérica", "norteamerica": "Norteamérica",
    "asia_oceania_africa": "Asia, Oceanía y África", "uruguay": "Uruguay",
    "solo_aereo": "solo aéreo", "aereo_hotel": "aéreo + hotel", "maritimo": "marítimo",
    "sin_aereo": "sin aéreo", "solo_alojamiento": "solo alojamiento", "todo_incluido": "todo incluido",
    "pension": "media pensión o completa", "sin_hotel": "sin hotel", "solo_millas": "solo millas",
    "latam": "LATAM", "copa": "Copa Airlines", "gol": "GOL", "iberia": "Iberia",
    "air_europa": "Air Europa", "aerolineas_argentinas": "Aerolíneas Argentinas", "sky": "SKY Airline",
    "avianca": "Avianca", "jetsmart": "JetSMART", "azul": "Azul", "american": "American Airlines",
    "menos_de_1": "menos de 1", "1-3": "1 a 3", "4+": "4 o más",
}


# ------------------------------------------------------------------ formato
def num(x, dec=1):
    return ("%.*f" % (dec, x)).replace(".", ",")


def miles(n):
    return "{:,}".format(int(n)).replace(",", ".")


def pct(x):
    return num(100 * x) + "%"


def lindo(columna, valor):
    if valor == SD or valor == "":
        return "sin dato"
    if CONTRATO.get(columna, {}).get("valores") == R.BINARIA:
        return "sí" if valor == "1" else "no"
    if columna == "pais_destino":
        return PAISES.get(valor, valor)
    if columna in ("region_destino", "tipo_producto", "aerolinea", "regimen_hotel", "pagador", "vendedor_antiguedad"):
        return BONITO.get(valor, valor.replace("_", " "))
    return valor.replace("_", " ")


def esc(x):
    return html.escape(str(x), quote=True)


# -------------------------------------------------------------------- datos
def leer():
    with open(TABLA, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cortes_quintiles(filas, columna):
    xs = sorted(int(f[columna]) for f in filas if f[columna] != "")
    return sorted(set(xs[int(len(xs) * q / 5)] for q in range(1, 5)))


def en_tramos(valor, cortes):
    if valor == "":
        return SD
    v, i = int(valor), 0
    while i < len(cortes) and v >= cortes[i]:
        i += 1
    desde = None if i == 0 else cortes[i - 1]
    hasta = None if i == len(cortes) else cortes[i]
    if desde is None:
        return "menos de %s" % miles(hasta)
    if hasta is None:
        return "%s o más" % miles(desde)
    return "%s a %s" % (miles(desde), miles(hasta))


def preparar(filas, entrenamiento):
    """Devuelve filas con las numericas pasadas a tramos, y el orden de cada columna."""
    orden = {}
    for c in NUMERICAS:
        cortes = cortes_quintiles(entrenamiento, c)
        for f in filas:
            f[c + "__t"] = en_tramos(f[c], cortes)
        etiquetas = []
        for v in [str(x) for x in ([cortes[0] - 1] + cortes)]:
            e = en_tramos(v, cortes)
            if e not in etiquetas:
                etiquetas.append(e)
        orden[c] = etiquetas + [SD]
    for c, regla in R.CONTRATO:
        if c not in orden and regla["tipo"] == "categoria":
            orden[c] = list(regla["valores"])
    return orden


def valor(f, c):
    return f[c + "__t"] if c in NUMERICAS else f[c]


def tasas(filas, c):
    n, pos = collections.Counter(), collections.Counter()
    for f in filas:
        v = valor(f, c)
        n[v] += 1
        pos[v] += f["vuelve_12"] == "1"
    return {v: (pos[v] / n[v], n[v]) for v in n}


def cramer(filas, a, b):
    """V de Cramer con correccion de sesgo, sobre las filas donde los dos tienen dato."""
    tabla = collections.Counter()
    for f in filas:
        x, y = valor(f, a), valor(f, b)
        if x != SD and y != SD and x != "" and y != "":
            tabla[(x, y)] += 1
    n = sum(tabla.values())
    fa, fb = collections.Counter(), collections.Counter()
    for (x, y), k in tabla.items():
        fa[x] += k
        fb[y] += k
    r, k = len(fa), len(fb)
    if n < 500 or r < 2 or k < 2:
        return None
    chi2 = sum((tabla.get((x, y), 0) - fa[x] * fb[y] / n) ** 2 / (fa[x] * fb[y] / n) for x in fa for y in fb)
    phi2 = max(0.0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    rc, kc = r - (r - 1) ** 2 / (n - 1), k - (k - 1) ** 2 / (n - 1)
    return math.sqrt(phi2 / min(kc - 1, rc - 1))


# ---------------------------------------------------------------------- svg
def barra(x, y, ancho, alto, clase, tip):
    r = min(4, ancho)
    d = "M%.1f,%.1f H%.1f Q%.1f,%.1f %.1f,%.1f V%.1f Q%.1f,%.1f %.1f,%.1f H%.1f Z" % (
        x, y, x + ancho - r, x + ancho, y, x + ancho, y + r, y + alto - r,
        x + ancho, y + alto, x + ancho - r, y + alto, x)
    return '<path class="%s" d="%s" data-tip="%s" tabindex="0"/>' % (clase, d, esc(tip))


def grafico_barras(filas_g, ancho_total=372, x_bar=150, ancho_bar=118, maximo=1.0, base=None, con_n=True):
    """filas_g: [(etiqueta, fraccion, n, es_sin_dato)]. Barras horizontales, valor en la punta."""
    paso, alto = 24, 14
    h = len(filas_g) * paso + 6
    p = ['<svg viewBox="0 0 %d %d" role="img" style="max-width:%dpx">' % (ancho_total, h, int(ancho_total * 1.15))]
    if base is not None:
        xb = x_bar + ancho_bar * base / maximo
        p.append('<line class="ref" x1="%.1f" y1="0" x2="%.1f" y2="%d"/>' % (xb, xb, h))
    for i, (etq, frac, n, gris) in enumerate(filas_g):
        y = 4 + i * paso
        p.append('<text class="cat" x="%d" y="%.1f" text-anchor="end">%s</text>' % (x_bar - 8, y + 11, esc(etq)))
        w = max(1.0, ancho_bar * frac / maximo)
        tip = "%s|%s · %s clientes" % (pct(frac), etq, miles(n)) if con_n else "%s|%s" % (pct(frac), etq)
        p.append(barra(x_bar, y, w, alto, "bar gris" if gris else "bar", tip))
        p.append('<text class="val" x="%.1f" y="%.1f">%s</text>' % (x_bar + w + 6, y + 11, pct(frac)))
        if con_n:
            p.append('<text class="n" x="%d" y="%.1f" text-anchor="end">%s</text>' % (ancho_total - 2, y + 11, miles(n)))
    p.append("</svg>")
    return "".join(p)


def tarjeta_variable(c, t, orden, base, maximo):
    datos = [(v, t[v]) for v in orden[c] if v in t and t[v][1] >= MINIMO]
    if c in NOMINALES:
        cola = [d for d in datos if d[0] in (SD, R.OTRO, R.OTRA, R.SIN_AEREO, R.SIN_HOTEL)]
        datos = sorted((d for d in datos if d not in cola), key=lambda d: -d[1][0]) + cola
    filas_g = [(lindo(c, v), tasa, n, v == SD) for v, (tasa, n) in datos]
    ocultas = sum(1 for v in t if t[v][1] < MINIMO)
    nota = '<p class="nota">%d categoría%s con menos de %d clientes no se muestra%s.</p>' % (
        ocultas, "s" if ocultas > 1 else "", MINIMO, "n" if ocultas > 1 else "") if ocultas else ""
    return '<article class="card"><h4>%s</h4>%s%s</article>' % (
        esc(ETIQUETA[c]), grafico_barras(filas_g, maximo=maximo, base=base), nota)


PASOS_V = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70]
PASOS_TASA = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]


def paso(x, cortes):
    return sum(1 for c in cortes if x >= c)


def mapa_asociacion(variables, v):
    n, celda, salto, izq, arriba = len(variables), 15, 17, 262, 196
    w, h = izq + n * salto + 150, arriba + n * salto + 6
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Asociación entre variables" style="max-width:%dpx">' % (w, h, w)]
    for i, a in enumerate(variables):
        p.append('<text class="cat" x="%d" y="%.1f" text-anchor="end">%s</text>' % (
            izq - 8, arriba + i * salto + 11, esc(NOMBRE[a])))
        cx = izq + i * salto + 10
        p.append('<text class="cat" transform="translate(%.1f,%d) rotate(-55)">%s</text>' % (
            cx, arriba - 8, esc(NOMBRE[a])))
        for j, b in enumerate(variables):
            x, y = izq + j * salto, arriba + i * salto
            if i == j:
                continue
            val = v.get((a, b))
            if val is None:
                p.append('<rect class="vacia" x="%d" y="%d" width="%d" height="%d" rx="2"/>' % (x, y, celda, celda))
                continue
            p.append('<rect class="seq%d" x="%d" y="%d" width="%d" height="%d" rx="2" data-tip="%s"/>' % (
                paso(val, PASOS_V), x, y, celda, celda,
                esc("%s|%s × %s" % (num(val, 2), NOMBRE[a], NOMBRE[b]))))
    p.append("</svg>")
    return "".join(p)


def leyenda_escala(cortes, formato):
    marcas = ["menos de %s" % formato(cortes[0])] + [
        "%s a %s" % (formato(cortes[i]), formato(cortes[i + 1])) for i in range(len(cortes) - 1)
    ] + ["%s o más" % formato(cortes[-1])]
    return '<div class="escala">' + "".join(
        '<span><i class="seq%d"></i>%s</span>' % (i, esc(m)) for i, m in enumerate(marcas)) + "</div>"


def mapa_tasas(filas, a, b, orden):
    n, pos = collections.Counter(), collections.Counter()
    for f in filas:
        k = (valor(f, a), valor(f, b))
        n[k] += 1
        pos[k] += f["vuelve_12"] == "1"
    fa = [x for x in orden[a] if x != SD and sum(n[(x, y)] for y in orden[b]) >= MINIMO]
    fb = [y for y in orden[b] if y != SD and sum(n[(x, y)] for x in orden[a]) >= MINIMO]
    cw, ch, izq, arriba = 96, 30, 190, 30
    w, h = izq + len(fb) * (cw + 2) + 4, arriba + len(fa) * (ch + 2) + 4
    p = ['<svg viewBox="0 0 %d %d" role="img" style="max-width:%dpx;min-width:%dpx">' % (w, h, w, min(w, 560))]
    for j, y in enumerate(fb):
        p.append('<text class="cat" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (
            izq + j * (cw + 2) + cw / 2, arriba - 10, esc(lindo(b, y))))
    for i, x in enumerate(fa):
        yy = arriba + i * (ch + 2)
        p.append('<text class="cat" x="%d" y="%.1f" text-anchor="end">%s</text>' % (izq - 8, yy + 19, esc(lindo(a, x))))
        for j, y in enumerate(fb):
            xx, k = izq + j * (cw + 2), n[(x, y)]
            if k < MINIMO:
                p.append('<rect class="vacia" x="%d" y="%d" width="%d" height="%d" rx="3"/>' % (xx, yy, cw, ch))
                continue
            t = pos[(x, y)] / k
            s = paso(t, PASOS_TASA)
            p.append('<rect class="seq%d" x="%d" y="%d" width="%d" height="%d" rx="3" data-tip="%s" tabindex="0"/>' % (
                s, xx, yy, cw, ch, esc("%s|%s · %s · %s clientes" % (pct(t), lindo(a, x), lindo(b, y), miles(k)))))
            p.append('<text class="tinta%d" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (
                s, xx + cw / 2, yy + 19, pct(t)))
    p.append("</svg>")
    return ('<article class="card ancha"><h4>%s × %s</h4><p class="nota">Filas: %s. Columnas: %s. '
            'Celdas vacías: menos de %d clientes.</p>%s</article>') % (
        esc(ETIQUETA[a]), esc(ETIQUETA[b]), esc(ETIQUETA[a].lower()), esc(ETIQUETA[b].lower()), MINIMO, "".join(p))


def mancuernas(ent):
    """Ficha unica contra ficha del dia 0: tasa de vuelta sin el dato y con el dato."""
    datos = [("mail", "Mail"), ("telefono", "Teléfono"), ("documento", "Documento"), ("nacimiento", "Fecha de nacimiento")]
    izq, ancho, maximo, paso_y = 150, 330, 0.35, 26
    h = 30 + len(datos) * (2 * paso_y + 14) + 4
    p = ['<svg viewBox="0 0 %d %d" role="img" style="max-width:%dpx">' % (izq + ancho + 150, h, int((izq + ancho + 150) * 1.15))]
    for g in range(0, 36, 5):
        x = izq + ancho * (g / 100) / maximo
        p.append('<line class="grid" x1="%.1f" y1="22" x2="%.1f" y2="%d"/>' % (x, x, h - 4))
        p.append('<text class="eje" x="%.1f" y="14" text-anchor="middle">%d%%</text>' % (x, g))
    filas_tabla = []
    for i, (clave, nombre) in enumerate(datos):
        y0 = 30 + i * (2 * paso_y + 14)
        p.append('<text class="cat fuerte" x="%d" y="%.1f" text-anchor="end">%s</text>' % (izq - 12, y0 + paso_y + 3, esc(nombre)))
        for k, (brazo, clase, rotulo) in enumerate((("fu", "s1", "ficha única"), ("d0", "s2", "día 0"))):
            t = tasas(ent, "%s_tiene_%s" % (brazo, clave))
            sin, con = t.get("0"), t.get("1")
            y = y0 + 8 + k * paso_y
            tiene = con[1] / (con[1] + (sin[1] if sin else 0))
            if sin and sin[1] >= MINIMO:
                x1, x2 = izq + ancho * sin[0] / maximo, izq + ancho * con[0] / maximo
                p.append('<line class="hilo %s" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (clase, x1, y, x2, y))
                p.append('<circle class="hueco %s" cx="%.1f" cy="%d" r="5" data-tip="%s" tabindex="0"/>' % (
                    clase, x1, y, esc("%s|%s, %s: sin el dato · %s clientes" % (pct(sin[0]), nombre, rotulo, miles(sin[1])))))
                p.append('<text class="val" x="%.1f" y="%d" text-anchor="end">%s</text>' % (min(x1, x2) - 10, y + 4, pct(sin[0])))
            else:
                x2 = izq + ancho * con[0] / maximo
            p.append('<circle class="lleno %s" cx="%.1f" cy="%d" r="5" data-tip="%s" tabindex="0"/>' % (
                clase, x2, y, esc("%s|%s, %s: con el dato · %s clientes" % (pct(con[0]), nombre, rotulo, miles(con[1])))))
            p.append('<text class="val" x="%.1f" y="%d">%s</text>' % (x2 + 10, y + 4, pct(con[0])))
            p.append('<text class="n" x="%d" y="%d" text-anchor="end">%s lo tiene</text>' % (izq + ancho + 148, y + 4, pct(tiene)))
            filas_tabla.append((nombre, rotulo, pct(tiene), pct(sin[0]) if sin and sin[1] >= MINIMO else "—", pct(con[0])))
    p.append("</svg>")
    tabla = ('<details><summary>Ver como tabla</summary><table><thead><tr><th>Dato</th><th>Ficha</th>'
             '<th>Lo tiene</th><th>Vuelve sin el dato</th><th>Vuelve con el dato</th></tr></thead><tbody>%s</tbody></table></details>'
             % "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % esc(x) for x in f) for f in filas_tabla))
    return "".join(p) + tabla


# --------------------------------------------------------------------- pagina
ESTILO = """
:root{color-scheme:light;--plano:#f9f9f7;--sup:#fcfcfb;--tinta:#0b0b0b;--tinta2:#52514e;--muda:#898781;
--grid:#e1e0d9;--eje:#c3c2b7;--borde:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;
--q0:#cde2fb;--q1:#9ec5f4;--q2:#6da7ec;--q3:#3987e5;--q4:#256abf;--q5:#184f95;--q6:#0d366b;--q7:#0d366b;
--t0:#0b0b0b;--t1:#0b0b0b;--t2:#0b0b0b;--t3:#fff;--t4:#fff;--t5:#fff;--t6:#fff;--t7:#fff}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--plano:#0d0d0d;--sup:#1a1a19;
--tinta:#f0efec;--tinta2:#c3c2b7;--muda:#898781;--grid:#2c2c2a;--eje:#383835;--borde:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;
--q0:#0d366b;--q1:#104281;--q2:#184f95;--q3:#256abf;--q4:#3987e5;--q5:#6da7ec;--q6:#9ec5f4;--q7:#cde2fb;
--t0:#fff;--t1:#fff;--t2:#fff;--t3:#fff;--t4:#fff;--t5:#0b0b0b;--t6:#0b0b0b;--t7:#0b0b0b}}
:root[data-theme="dark"]{color-scheme:dark;--plano:#0d0d0d;--sup:#1a1a19;--tinta:#f0efec;--tinta2:#c3c2b7;--muda:#898781;
--grid:#2c2c2a;--eje:#383835;--borde:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;
--q0:#0d366b;--q1:#104281;--q2:#184f95;--q3:#256abf;--q4:#3987e5;--q5:#6da7ec;--q6:#9ec5f4;--q7:#cde2fb;
--t0:#fff;--t1:#fff;--t2:#fff;--t3:#fff;--t4:#fff;--t5:#0b0b0b;--t6:#0b0b0b;--t7:#0b0b0b}
*{box-sizing:border-box}
body{margin:0;background:var(--plano);color:var(--tinta);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1200px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;line-height:1.2;margin:0 0 6px;text-wrap:balance}
h2{font-size:20px;margin:48px 0 4px}
h3{font-size:13px;margin:28px 0 10px;color:var(--tinta2);font-weight:600;letter-spacing:.02em;text-transform:uppercase}
h4{font-size:14px;margin:0 0 8px;font-weight:600}
p{margin:0 0 10px;max-width:78ch}
.sub{color:var(--tinta2)}
.nota{color:var(--muda);font-size:12px;margin:8px 0 0}
.fila{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px;margin:20px 0 0}
.dato{background:var(--sup);border:1px solid var(--borde);border-radius:10px;padding:14px 16px}
.dato b{display:block;font-size:22px;font-weight:600;line-height:1.2}
.dato span{color:var(--tinta2);font-size:13px}
.heroe b{font-size:52px}
.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.card{background:var(--sup);border:1px solid var(--borde);border-radius:10px;padding:14px 16px;min-width:0}
.card.ancha{grid-column:1/-1;overflow-x:auto}
.card.ancha>svg{min-width:560px}
svg{display:block;width:100%;height:auto;overflow:visible}
text{font:12px system-ui,-apple-system,"Segoe UI",sans-serif;fill:var(--tinta2)}
text.val{fill:var(--tinta);font-weight:600;font-variant-numeric:tabular-nums}
text.n,text.eje{fill:var(--muda);font-size:11px;font-variant-numeric:tabular-nums}
text.fuerte{fill:var(--tinta);font-weight:600;font-size:13px}
.bar{fill:var(--s1)}.bar.gris{fill:var(--muda)}
.ref,.grid{stroke:var(--grid);stroke-width:1}.ref{stroke:var(--eje)}
.vacia{fill:none;stroke:var(--grid);stroke-width:1}
.hilo{stroke-width:2;stroke-linecap:round}.hilo.s1{stroke:var(--s1)}.hilo.s2{stroke:var(--s2)}
circle{stroke:var(--sup);stroke-width:2}
circle.lleno.s1{fill:var(--s1)}circle.lleno.s2{fill:var(--s2)}
circle.hueco{fill:var(--sup)}circle.hueco.s1{stroke:var(--s1)}circle.hueco.s2{stroke:var(--s2)}
[data-tip]{cursor:default;outline:none}[data-tip]:hover,[data-tip]:focus-visible{filter:brightness(1.18)}
[data-tip]:focus-visible{stroke:var(--tinta);stroke-width:1.5}
.leyenda,.escala{display:flex;flex-wrap:wrap;gap:6px 16px;color:var(--tinta2);font-size:12px;margin:0 0 10px}
.leyenda i,.escala i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.leyenda i.s1{background:var(--s1)}.leyenda i.s2{background:var(--s2)}
.leyenda i.punto{border-radius:50%;background:var(--tinta2)}.leyenda i.aro{border-radius:50%;border:2px solid var(--tinta2);background:none}
.leyenda i.raya{height:0;border-top:1px solid var(--eje);width:16px;vertical-align:4px;border-radius:0}
details{margin-top:10px}summary{cursor:pointer;color:var(--tinta2);font-size:13px}
table{border-collapse:collapse;margin-top:8px;font-size:13px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:5px 14px 5px 0;border-bottom:1px solid var(--grid)}th{color:var(--tinta2);font-weight:600}
.tabla{overflow-x:auto}
#tip{position:fixed;z-index:9;pointer-events:none;background:var(--tinta);color:var(--sup);padding:6px 10px;border-radius:6px;
font-size:12px;max-width:280px;box-shadow:0 4px 14px rgba(0,0,0,.18)}#tip b{display:block;font-size:14px}
footer{margin-top:48px;color:var(--muda);font-size:12px}
""" + "".join(".seq%d{fill:var(--q%d);background:var(--q%d)}text.tinta%d{fill:var(--t%d);font-weight:600;font-variant-numeric:tabular-nums}" % (i, i, i, i, i) for i in range(8))

GUION = """
(function(){var t=document.getElementById('tip');
function ver(el,x,y){var p=(el.getAttribute('data-tip')||'').split('|');t.textContent='';
var b=document.createElement('b');b.textContent=p[0];t.appendChild(b);t.appendChild(document.createTextNode(p[1]||''));
t.hidden=false;var w=t.offsetWidth,h=t.offsetHeight;
t.style.left=Math.max(8,Math.min(window.innerWidth-w-8,x+14))+'px';t.style.top=Math.max(8,y-h-12)+'px';}
document.addEventListener('pointermove',function(e){var el=e.target.closest&&e.target.closest('[data-tip]');
if(el){ver(el,e.clientX,e.clientY);}else{t.hidden=true;}});
document.addEventListener('focusin',function(e){var el=e.target.closest&&e.target.closest('[data-tip]');
if(el){var r=el.getBoundingClientRect();ver(el,r.left+r.width/2,r.top);}});
document.addEventListener('focusout',function(){t.hidden=true;});})();
"""


def main():
    filas = leer()
    ent = [f for f in filas if f["bloque"] == "entrenamiento"]
    orden = preparar(filas, ent)
    base = sum(f["vuelve_12"] == "1" for f in ent) / len(ent)
    por_bloque = collections.Counter(f["bloque"] for f in filas)
    variables = [c for _, cs in GRUPOS for c, _ in cs]

    todas = {c: tasas(ent, c) for c in variables}
    maximo = math.ceil(max(t for d in todas.values() for t, n in d.values() if n >= MINIMO) * 10) / 10

    # 1. cuanto separa cada variable
    separa = []
    for c in variables:
        ts = [t for v, (t, n) in todas[c].items() if n >= 100 and v != SD]
        if len(ts) > 1:
            separa.append((NOMBRE[c], max(ts) - min(ts), 0, False))
    separa.sort(key=lambda x: -x[1])
    alcance = math.ceil(max(s[1] for s in separa) * 10) / 10
    ranking = grafico_barras(separa, ancho_total=640, x_bar=300, ancho_bar=270, maximo=alcance, con_n=False)
    ranking = ranking.replace("%</text>", " pts</text>").replace("%|", " pts|")

    # 2. una tarjeta por variable
    secciones = []
    for grupo, cs in GRUPOS:
        secciones.append("<h3>%s</h3><div class='rejilla'>%s</div>" % (
            esc(grupo), "".join(tarjeta_variable(c, todas[c], orden, base, maximo) for c, _ in cs)))

    # 3. asociacion entre variables
    con_etiqueta = ["vuelve_12"] + variables
    v = {}
    for i, a in enumerate(con_etiqueta):
        for b in con_etiqueta[i + 1:]:
            x = cramer(ent, a, b)
            v[(a, b)] = v[(b, a)] = x
    pares = sorted(((x, a, b) for (a, b), x in v.items() if x is not None and con_etiqueta.index(a) < con_etiqueta.index(b)),
                   reverse=True)[:30]
    tabla_pares = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(NOMBRE[a]), esc(NOMBRE[b]), num(x, 2))
                          for x, a, b in pares)

    # 4. interacciones
    interacciones = "".join(mapa_tasas(ent, a, b, orden) for a, b in (
        ("viajes_previos_acompaniante", "viaja_con_cliente_previo"),
        ("region_destino", "tipo_producto"),
        ("anticipacion", "pasajeros")))

    # 5. cuanto quedo sin dato (toda la tabla, no mira la etiqueta)
    faltan = []
    for c, _ in R.CONTRATO:
        k = sum(1 for f in filas if f[c] in (SD, ""))
        if k:
            faltan.append((NOMBRE.get(c, c), k / len(filas), k, False))
    faltan.sort(key=lambda x: -x[1])
    sin_dato = grafico_barras(faltan, ancho_total=640, x_bar=300, ancho_bar=220,
                              maximo=math.ceil(max(f[1] for f in faltan) * 10) / 10)

    with open(os.path.join(REPO, "datos", "manifiesto.json"), encoding="utf-8") as fh:
        man = json.load(fh)

    cuerpo = """
<h1>¿Vuelve a viajar? Exploración de la tabla del modelo</h1>
<p class="sub">Una fila por cliente nuevo de Jetmar, con lo que se sabía el día de su primera compra. Todo lo que
mira la etiqueta usa solo el bloque de entrenamiento (cohorte 2023): validación y prueba no se miran para explorar.</p>
<div class="fila">
  <div class="dato heroe"><b>%(base)s</b><span>de los clientes de entrenamiento vuelve dentro de los 12 meses</span></div>
  <div class="dato"><b>%(n)s</b><span>clientes en la tabla, %(cols)d columnas</span></div>
  <div class="dato"><b>%(ne)s</b><span>entrenamiento · cohorte 2023</span></div>
  <div class="dato"><b>%(nv)s</b><span>validación · cohorte 2024</span></div>
  <div class="dato"><b>%(np)s</b><span>prueba · enero a agosto de 2025</span></div>
</div>

<h2>Cuánto separa cada variable</h2>
<p class="sub">Diferencia, en puntos porcentuales, entre la categoría que más vuelve y la que menos, contando solo
categorías con 100 clientes o más y sin contar «sin dato». Es cada variable sola: no dice nada de cómo se combinan.</p>
<article class="card medio">%(ranking)s</article>

<h2>Vuelta según cada variable</h2>
<p class="sub">Porcentaje de clientes que vuelve dentro de los 12 meses, por categoría. La columna de la derecha es la
cantidad de clientes. Todas las tarjetas usan la misma escala.</p>
<div class="leyenda"><span><i class="s1"></i>categoría con dato</span>
<span><i style="background:var(--muda)"></i>sin dato</span>
<span><i class="raya"></i>promedio del bloque, %(base)s</span></div>
%(secciones)s

<h2>Ficha única contra ficha del día 0</h2>
<p class="sub">Para cada dato de contacto, cuánto vuelve quien no lo tiene cargado y quien sí, según se mire la ficha
única de hoy o el registro que se usó en la primera compra. Es la comparación de la hipótesis 3. El registro del día 0
se ve como está hoy: si alguien lo completó después sobre el mismo registro, esa parte de la fuga no se quita.</p>
<article class="card medio">
<div class="leyenda"><span><i class="s1"></i>ficha única (hoy)</span><span><i class="s2"></i>ficha del día 0</span>
<span><i class="aro"></i>sin el dato</span><span><i class="punto"></i>con el dato</span></div>
%(mancuernas)s</article>

<h2>Relaciones entre variables</h2>
<p class="sub">V de Cramér con corrección de sesgo entre cada par de variables: 0 es sin relación y 1 es que una
determina a la otra. Las numéricas van en cinco tramos. Se calcula con los clientes que tienen dato en las dos
variables, para que lo suprimido por anonimato no invente relaciones. La primera fila es la etiqueta.</p>
<article class="card ancha">%(escala_v)s%(mapa)s
<details><summary>Ver los 30 pares más asociados como tabla</summary><div class="tabla"><table><thead><tr><th>Variable</th>
<th>Variable</th><th>V</th></tr></thead><tbody>%(pares)s</tbody></table></div></details></article>

<h2>Tres cruces</h2>
<p class="sub">Porcentaje que vuelve en cada combinación de dos variables.</p>
%(escala_t)s
<div class="rejilla">%(interacciones)s</div>

<h2>Cuánto quedó sin dato</h2>
<p class="sub">Porcentaje de filas sin dato en cada columna, sobre toda la tabla. Incluye lo que la base no trae y lo
que se suprimió para que ningún cliente quede en un grupo chico; el detalle está en <code>datos/DICCIONARIO.md</code>.</p>
<article class="card medio">%(sin_dato)s</article>

<footer>Generado por <code>analisis/graficas.py</code> desde <code>datos/tabla_modelo.csv</code>
(armada el %(armado)s, huella %(huella)s…). No se muestran grupos de menos de %(minimo)d clientes ni resultados por vendedor.</footer>
""" % {
        "base": pct(base), "n": miles(len(filas)), "cols": len(R.COLUMNAS),
        "ne": miles(por_bloque["entrenamiento"]), "nv": miles(por_bloque["validacion"]),
        "np": miles(por_bloque["prueba"]), "ranking": ranking, "secciones": "".join(secciones),
        "mancuernas": mancuernas(ent), "escala_v": leyenda_escala(PASOS_V, lambda x: num(x, 2)),
        "mapa": mapa_asociacion(con_etiqueta, v), "pares": tabla_pares,
        "escala_t": leyenda_escala(PASOS_TASA, lambda x: "%d%%" % round(100 * x)),
        "interacciones": interacciones, "sin_dato": sin_dato,
        "armado": man["armado"][:10], "huella": man["sha256"][:12], "minimo": MINIMO}

    pagina = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1">'
              '<title>Exploración · ¿Vuelve a viajar?</title><style>%s</style></head>'
              '<body><main>%s</main><div id="tip" hidden></div><script>%s</script></body></html>'
              % (ESTILO, cuerpo, GUION))
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(pagina)
    print("%s · %d KB" % (SALIDA, os.path.getsize(SALIDA) // 1024))

    # resumen en texto, para leer las relaciones sin abrir el archivo
    sys.stdout.reconfigure(encoding="utf-8")
    print("\nentrenamiento: %d clientes · vuelve %s" % (len(ent), pct(base)))
    print("\ncuanto separa cada variable (puntos entre la categoria que mas y la que menos vuelve):")
    for nombre, d, _, _ in separa:
        print("   %5.1f  %s" % (100 * d, nombre))
    print("\npares de variables mas asociados (V de Cramer):")
    for x, a, b in pares[:22]:
        print("   %.2f  %s  ×  %s" % (x, NOMBRE[a], NOMBRE[b]))
    print("\nasociacion de cada variable con la etiqueta:")
    for x, c in sorted(((v[("vuelve_12", c)] or 0, c) for c in variables), reverse=True)[:12]:
        print("   %.2f  %s" % (x, NOMBRE[c]))


if __name__ == "__main__":
    main()
