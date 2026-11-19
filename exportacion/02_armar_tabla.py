"""Paso 2 · Arma la tabla del modelo a partir de la ultima foto.

    py exportacion/02_armar_tabla.py

Solo corre adentro de la empresa. Lee la foto de `~/datos/ml_vueltas/` y deja:

  en el repo (lo que sale):
    datos/tabla_modelo.csv     una fila por cliente, sin ids ni datos personales
    datos/manifiesto.json      fecha, filas, que se suprimio y huella del archivo

  fuera del repo y de OneDrive (lo que NO sale):
    ~/datos/ml_vueltas/interno/secretos.json                  semilla y constante
    ~/datos/ml_vueltas/interno/correspondencia_clientes.csv   codigo <-> id
    ~/datos/ml_vueltas/interno/correspondencia_vendedores.csv codigo <-> id

La semilla y la constante de la utilidad se generan la primera vez y despues
se reusan: volver a correr da los mismos codigos. Si la tabla no pasa las
verificaciones de `anonimato.revisar_todo`, no se escribe nada.
"""
import csv
import datetime
import glob
import hashlib
import json
import os
import random
import secrets
import sys

import duckdb

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from exportacion import anonimato, armar, reglas  # noqa: E402

RAIZ = os.path.join(os.path.expanduser("~"), "datos", "ml_vueltas")
INTERNO = os.path.join(RAIZ, "interno")
SALIDA = os.path.join(REPO, "datos")


def ultima_foto():
    fotos = sorted(glob.glob(os.path.join(RAIZ, "foto_*")))
    if not fotos:
        raise SystemExit("no hay ninguna foto en %s: correr antes el paso 1" % RAIZ)
    return fotos[-1]


def leer_secretos(internas):
    """Semilla de los codigos y constante que convierte la utilidad en indice."""
    ruta = os.path.join(INTERNO, "secretos.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    utilidades = sorted(f["utilidad"] for f in internas if f["cohorte"] == 2023)
    mediana = utilidades[len(utilidades) // 2]
    secretos = {"semilla": secrets.randbits(48),
                "k_utilidad": round(mediana * random.SystemRandom().uniform(0.8, 1.25), 2),
                "creado": datetime.datetime.now().isoformat(timespec="seconds")}
    os.makedirs(INTERNO, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(secretos, fh, indent=2)
    return secretos


def escribir_csv(ruta, columnas, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columnas)
        w.writerows(filas)


def main():
    if "OneDrive" in RAIZ:
        raise SystemExit("la carpeta interna no puede estar en OneDrive: " + RAIZ)
    foto = ultima_foto()
    with open(os.path.join(foto, "manifiesto.json"), encoding="utf-8") as fh:
        manifiesto_foto = json.load(fh)

    con = duckdb.connect()
    armar.cargar_foto(con, foto)
    armar.construir_interna(con, reglas.COHORTE_DESDE, reglas.COHORTE_HASTA)
    cur = con.execute("SELECT * FROM interna ORDER BY cid")
    columnas = [d[0] for d in cur.description]
    internas = [dict(zip(columnas, f)) for f in cur.fetchall()]

    secretos = leer_secretos(internas)
    filas, informe, mapas = anonimato.armar_publica(
        internas, semilla=secretos["semilla"], k_utilidad=secretos["k_utilidad"])

    problemas = anonimato.revisar_todo(filas, reglas)
    if informe["grupos_chicos_al_final"] != {"cuasi_1": 0, "cuasi_2": 0}:
        problemas.append("quedan grupos chicos contando el anio de viaje: %s"
                         % informe["grupos_chicos_al_final"])
    if problemas:
        print("NO SE ESCRIBE LA TABLA. Problemas:")
        for p in problemas:
            print("  - " + p)
        return 1

    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, "tabla_modelo.csv")
    escribir_csv(ruta, reglas.COLUMNAS, [[f[c] for c in reglas.COLUMNAS] for f in filas])
    with open(ruta, "rb") as fh:
        huella = hashlib.sha256(fh.read()).hexdigest()

    por_bloque = {}
    for f in filas:
        b = por_bloque.setdefault(f["bloque"], {"clientes": 0, "vuelven": 0})
        b["clientes"] += 1
        b["vuelven"] += f["vuelve_12"] == "1"
    manifiesto = {
        "archivo": "tabla_modelo.csv",
        "armado": datetime.datetime.now().isoformat(timespec="seconds"),
        "foto_tomada": manifiesto_foto["tomado"],
        "ultima_compra_en_la_foto": manifiesto_foto["ultima_compra"],
        "cohortes": [reglas.COHORTE_DESDE, reglas.COHORTE_HASTA],
        "filas": len(filas), "columnas": len(reglas.COLUMNAS), "sha256": huella,
        "por_bloque": por_bloque,
        "anonimato": {
            "k_conocido_del_viaje": reglas.K_1, "columnas_k_1": reglas.CUASI_1,
            "k_con_detalle": reglas.K_2, "columnas_k_2": reglas.CUASI_2,
            "minimo_por_categoria": reglas.MINIMO_POR_CATEGORIA,
            "nota": "los grupos se midieron ademas con el anio de viaje, que no se publica",
        },
        "armado_informe": informe,
    }
    with open(os.path.join(SALIDA, "manifiesto.json"), "w", encoding="utf-8") as fh:
        json.dump(manifiesto, fh, indent=2, ensure_ascii=False)

    os.makedirs(INTERNO, exist_ok=True)
    escribir_csv(os.path.join(INTERNO, "correspondencia_clientes.csv"),
                 ["cliente", "master_customer_id"],
                 sorted((c, o) for o, c in mapas["clientes"].items()))
    escribir_csv(os.path.join(INTERNO, "correspondencia_vendedores.csv"),
                 ["vendedor", "vendedor_clave"],
                 sorted((c, o or "") for o, c in mapas["vendedores"].items()))

    print("tabla: %s" % ruta)
    print("filas: %d (entraron %d, se retiraron %d) · columnas: %d" % (
        len(filas), informe["filas_entrada"], informe["filas_retiradas"], len(reglas.COLUMNAS)))
    for b in reglas.BLOQUES:
        d = por_bloque.get(b, {"clientes": 0, "vuelven": 0})
        print("  %-14s %6d clientes · vuelven %5d (%.1f%%)" % (
            b, d["clientes"], d["vuelven"], 100.0 * d["vuelven"] / max(d["clientes"], 1)))
    print("supresiones por lo que sabe un conocido (k=%d): %s" % (reglas.K_1, informe["supresiones_cuasi_1"]))
    print("supresiones con detalle (k=%d): %s" % (reglas.K_2, informe["supresiones_cuasi_2"]))
    print("categorias raras agrupadas: %d filas" % informe["categorias_raras_agrupadas"])
    print("cortes 60-20-20: %s" % informe["cortes_60_20_20"])
    print("correspondencias y secretos: %s (no salen de la empresa)" % INTERNO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
