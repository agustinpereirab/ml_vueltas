"""Lee la tabla del modelo y arma las matrices de cada bloque.

Las variables son las columnas del contrato (`exportacion/reglas.py`) salvo
las de identificacion, particion y etiqueta. Las de ficha unica (`fu_`) y
ficha del dia 0 (`d0_`) son los dos brazos de la hipotesis 3: cada modelo usa
uno solo. El brazo por defecto es `d0`, el que no trae fuga.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from exportacion import reglas as R  # noqa: E402

TABLA = os.path.join(REPO, "datos", "tabla_modelo.csv")
MANIFIESTO = os.path.join(REPO, "datos", "manifiesto.json")

ETIQUETA = "vuelve_12"
NO_SON_VARIABLES = ["cliente", "cohorte", "bloque", "bloque_60_20_20",
                    "vuelve_12", "vuelve_12_comprando"]
FICHA_UNICA = [c for c in R.COLUMNAS if c.startswith("fu_")]
FICHA_D0 = [c for c in R.COLUMNAS if c.startswith("d0_")]
NUMERICAS = [c for c, r in R.CONTRATO if r["tipo"] in ("monto", "indice")]
BRAZOS = {
    "d0": FICHA_UNICA,              # lo que se sabia el dia 0
    "fu": FICHA_D0,                 # la ficha unica de hoy: con fuga
    "ninguno": FICHA_UNICA + FICHA_D0,
}


def variables(brazo="d0"):
    fuera = set(NO_SON_VARIABLES) | set(BRAZOS[brazo])
    return [c for c in R.COLUMNAS if c not in fuera]


def categoricas(brazo="d0"):
    return [c for c in variables(brazo) if c not in NUMERICAS]


def huella():
    """sha256 de la tabla. Corta si no coincide con la del manifiesto."""
    h = hashlib.sha256()
    with open(TABLA, "rb") as fh:
        for trozo in iter(lambda: fh.read(1 << 20), b""):
            h.update(trozo)
    with open(MANIFIESTO, encoding="utf-8") as fh:
        esperada = json.load(fh)["sha256"]
    if h.hexdigest() != esperada:
        raise SystemExit("la tabla no es la del manifiesto (%s... contra %s...)"
                         % (h.hexdigest()[:12], esperada[:12]))
    return esperada


def leer():
    """La tabla con tipos: numericas en float (vacio -> NaN) y el resto como categorias.

    Las categorias salen del contrato, asi cada bloque usa los mismos codigos.
    Los codigos de vendedor salen de toda la tabla (es la lista de codigos, no
    mira la etiqueta).
    """
    crudo = pd.read_csv(TABLA, dtype=str, keep_default_na=False)
    t = pd.DataFrame(index=crudo.index)
    for c, regla in R.CONTRATO:
        x = crudo[c]
        if c in NUMERICAS:
            t[c] = pd.to_numeric(x.replace("", np.nan)).astype(float)
        elif regla["tipo"] == "categoria":
            t[c] = pd.Categorical(x, categories=regla["valores"])
        else:
            t[c] = pd.Categorical(x, categories=sorted(x.unique()))
        if c not in NUMERICAS and t[c].isna().any():
            raise SystemExit("%s trae valores fuera del contrato" % c)
    t[ETIQUETA] = crudo[ETIQUETA].astype(int)
    return t


def bloques(tabla, brazo="d0", particion="bloque"):
    """{bloque: (X, y)} para entrenamiento, validacion y prueba."""
    cols = variables(brazo)
    salida = {}
    for b in R.BLOQUES:
        f = tabla[particion] == b
        salida[b] = (tabla.loc[f, cols].reset_index(drop=True),
                     tabla.loc[f, ETIQUETA].to_numpy())
    return salida
