"""Carga de la tabla del modelo y los tres brazos de variables.

Los brazos son las tres versiones de la hipotesis 3:

- `dia0`: lo que se sabia el dia de la primera compra. Es el modelo principal.
- `ficha_unica`: lo mismo, pero con los datos de contacto como estan HOY en
  la ficha unica (brazo con fuga).
- `sin_contacto`: sin ningun dato de contacto, como referencia.

El bloque de prueba no se carga salvo que se pida con `permitir_prueba=True`.
"""
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from exportacion import reglas  # noqa: E402

RUTA = os.path.join(REPO, "datos", "tabla_modelo.csv")
ETIQUETA = "vuelve_12"
NO_VARIABLES = ["cliente", "cohorte", "bloque", "bloque_60_20_20", "vuelve_12", "vuelve_12_comprando"]
DIA0 = ["d0_tiene_mail", "d0_tiene_telefono", "d0_tiene_documento", "d0_tiene_nacimiento"]
FICHA_UNICA = ["fu_tiene_mail", "fu_tiene_telefono", "fu_tiene_documento", "fu_tiene_nacimiento",
               "fu_registros"]
NUMERICAS = ["venta_usd", "venta_por_pasajero_usd", "utilidad_indice"]
CATEGORICAS = [c for c in reglas.COLUMNAS if c not in NO_VARIABLES + NUMERICAS]
BASE = [c for c in reglas.COLUMNAS if c not in NO_VARIABLES + DIA0 + FICHA_UNICA]
BRAZOS = {
    "dia0": BASE + DIA0,
    "ficha_unica": BASE + FICHA_UNICA,
    "sin_contacto": BASE,
}


def cargar(ruta=RUTA, bloques=("entrenamiento", "validacion"), permitir_prueba=False):
    """Lee la tabla y deja solo los bloques pedidos. Numericas como float (vacio
    = faltante), el resto como texto, la etiqueta como entero 0/1."""
    if "prueba" in bloques and not permitir_prueba:
        raise ValueError("el bloque de prueba se usa una sola vez, al final: "
                         "pedilo con permitir_prueba=True")
    d = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    d = d[d["bloque"].isin(bloques)].reset_index(drop=True)
    for c in NUMERICAS:
        d[c] = pd.to_numeric(d[c].replace("", np.nan))
    for c in CATEGORICAS:
        d[c] = d[c].astype(object)
    d[ETIQUETA] = (d[ETIQUETA] == "1").astype(int)
    return d


def separar(d, brazo):
    """(X entrenamiento, y entrenamiento, X validacion, y validacion) del brazo."""
    columnas = BRAZOS[brazo]
    ent = d[d["bloque"] == "entrenamiento"]
    val = d[d["bloque"] == "validacion"]
    return (ent[columnas].reset_index(drop=True), ent[ETIQUETA].to_numpy(),
            val[columnas].reset_index(drop=True), val[ETIQUETA].to_numpy())


def tipos(columnas):
    """(categoricas, numericas) de una lista de columnas."""
    return [c for c in columnas if c in CATEGORICAS], [c for c in columnas if c in NUMERICAS]
