"""Puntua clientes con un modelo exportado. Solo usa Python estandar.

    python puntuar.py <modelo.json> <entrada.csv> <salida.csv>

La entrada tiene que traer, como texto, las columnas que usa el modelo, con
los mismos valores que `datos/tabla_modelo.csv` (ver `datos/DICCIONARIO.md`).
Puede traer otras columnas: se copian tal cual. La salida es la entrada con
una columna mas, `prob_vuelve_12`: la probabilidad de que el cliente vuelva a
viajar dentro de los 12 meses de su primera compra.

Lo que hay que saber antes de usarlo esta en la seccion "advertencias" del
JSON del modelo.
"""
import csv
import json
import math
import sys

EPS = 1e-9


def _sigmoide(z):
    z = max(-35.0, min(35.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def logit_crudo(fila, modelo):
    """Logit del modelo antes de recalibrar. Una categoria que el modelo no
    conoce no aporta nada (como en el entrenamiento)."""
    z = modelo["intercepto"]
    for variable, coefs in modelo["categoricas"].items():
        z += coefs.get(str(fila[variable]), 0.0)
    for variable, p in modelo["numericas"].items():
        texto = fila[variable]
        falta = texto is None or str(texto).strip() == ""
        valor = p["mediana_asinh"] if falta else math.asinh(float(texto))
        z += p["coef"] * (valor - p["media"]) / p["escala"]
        if "faltante" in p:
            f = p["faltante"]
            z += f["coef"] * ((1.0 if falta else 0.0) - f["media"]) / f["escala"]
    return z


def probabilidad(fila, modelo, recalibrar=True):
    p = _sigmoide(logit_crudo(fila, modelo))
    c = modelo["calibrador"]
    if not recalibrar or c["metodo"] == "identidad":
        return p
    q = min(max(p, EPS), 1 - EPS)
    lg = math.log(q / (1 - q))
    if c["metodo"] == "intercepto":
        return _sigmoide(lg + c["b"])
    if c["metodo"] == "platt":
        return _sigmoide(c["a"] * lg + c["b"])
    raise ValueError("calibrador no soportado: %s" % c["metodo"])


def puntuar_csv(ruta_modelo, entrada, salida, recalibrar=True):
    with open(ruta_modelo, encoding="utf-8") as fh:
        modelo = json.load(fh)
    with open(entrada, newline="", encoding="utf-8") as fh:
        lector = csv.DictReader(fh)
        columnas = list(lector.fieldnames) + ["prob_vuelve_12"]
        filas = list(lector)
    faltan = [v for v in list(modelo["categoricas"]) + list(modelo["numericas"]) if v not in columnas]
    if faltan:
        raise KeyError("a la entrada le faltan columnas del modelo: %s" % ", ".join(faltan))
    with open(salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        for f in filas:
            f["prob_vuelve_12"] = "%.10f" % probabilidad(f, modelo, recalibrar)
            w.writerow(f)
    return len(filas)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    n = puntuar_csv(*sys.argv[1:])
    print("%d clientes puntuados -> %s" % (n, sys.argv[3]))
