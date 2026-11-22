"""Cada variable sola: cuánto ordena por su cuenta a los que vuelven. Exploratorio.

    python modelo/variables_solas.py

Para cada una de las 29 variables del modelo principal, la tasa de vuelta de cada valor se
aprende con entrenamiento (2023) y se usa como puntaje en validación (2024). Las numéricas se
parten en quintiles de entrenamiento. Mide:

- ROC-AUC y PR-AUC de la variable sola en validación (azar: 0,5 y la tasa de vuelta);
- r: la correlación entre ese puntaje y la vuelta (0 o 1), y su cuadrado. Con una etiqueta de
  sí o no, r² queda bajo aunque la variable ordene: se informa porque es la pregunta habitual,
  pero la medida que corresponde es la de orden (AUC).

Como referencia, lo mismo para la logística principal (C de la escalera). No elige ni ajusta
nada y no usa el bloque de prueba. Escribe `modelo/resultados/variables_solas.*`.
"""
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos, metricas, modelos  # noqa: E402
from modelo import interpretacion as it  # noqa: E402
from modelo.escalera import SEMILLA, REPETICIONES, huella_tabla, intervalo, num  # noqa: E402

SALIDA = os.path.join(REPO, "modelo", "resultados")
NOMBRES = {
    "fue_acompaniante_antes": "Viajó antes como acompañante", "viajes_previos_acompaniante": "Viajes previos como acompañante",
    "viaja_con_cliente_previo": "Viaja con un cliente previo", "viaja_con_alguien_con_historial": "Viaja con alguien con historial",
    "pasajeros": "Pasajeros", "venta_usd": "Venta", "venta_por_pasajero_usd": "Venta por pasajero", "utilidad_indice": "Utilidad (índice)",
    "canje_millas": "Canje de millas", "pagador": "Quién pagó", "tipo_producto": "Tipo de producto", "tiene_seguro": "Seguro",
    "lleva_hotel": "Lleva hotel", "regimen_hotel": "Régimen del hotel", "aerolinea": "Aerolínea", "servicios": "Servicios",
    "region_destino": "Región de destino", "pais_destino": "País de destino", "destinos": "Cantidad de destinos", "noches": "Noches",
    "anticipacion": "Anticipación", "vendedor": "Vendedor (código)", "vendedor_es_persona": "Vendedor es persona",
    "vendedor_fichas_12m": "Cartera del vendedor", "vendedor_antiguedad": "Antigüedad del vendedor",
    "d0_tiene_mail": "Mail cargado el día 0", "d0_tiene_telefono": "Teléfono cargado el día 0",
    "d0_tiene_documento": "Documento cargado el día 0", "d0_tiene_nacimiento": "Nacimiento cargado el día 0",
}


def puntaje(col_e, y_e, col_v, numerica):
    """Tasa de vuelta del valor de cada cliente, aprendida en entrenamiento."""
    if numerica:
        cortes = np.unique(np.nanquantile(col_e, [0.2, 0.4, 0.6, 0.8]))
        banda = lambda c: np.where(np.isnan(c), -1, np.searchsorted(cortes, c, side="right"))  # noqa: E731
        col_e, col_v = banda(col_e.to_numpy(dtype=float)), banda(col_v.to_numpy(dtype=float))
    tasas = pd.Series(y_e).groupby(np.asarray(col_e)).mean()
    return pd.Series(np.asarray(col_v)).map(tasas).fillna(float(np.mean(y_e))).to_numpy(dtype=float)


def r_de(y, s):
    return float(np.corrcoef(s, y)[0, 1]) if np.std(s) > 0 else 0.0


def main():
    huella = huella_tabla()
    with open(os.path.join(SALIDA, "escalera_validacion.json"), encoding="utf-8") as fh:
        escalera = json.load(fh)
    if escalera["tabla_sha256"] != huella:
        raise SystemExit("la escalera se corrió con otra tabla: correr modelo/escalera.py")
    C = escalera["hiperparametros"]["logistica"]["dia0"]["C"]

    d = datos.cargar()
    x_e, y_e, x_v, y_v = datos.separar(d, "dia0")
    columnas = datos.BRAZOS["dia0"]
    puntajes = {c: puntaje(x_e[c], y_e, x_v[c], c in datos.NUMERICAS) for c in columnas}
    cats, nums = datos.tipos(columnas)
    puntajes["__modelo__"] = modelos._logistica(cats, nums, C).fit(x_e, y_e).predict_proba(x_v)[:, 1]

    boot = metricas.bootstrap(y_v, puntajes, {"roc_auc": metricas.roc_auc}, [], REPETICIONES, SEMILLA)
    grupo_de = {v: g for g, vs in it.GRUPOS.items() for v in vs}
    filas = []
    for c, s in puntajes.items():
        r = r_de(y_v, s)
        filas.append({"variable": c, "nombre": NOMBRES.get(c, "Logística principal (29 variables)"),
                      "grupo": grupo_de.get(c, "modelo"), "roc_auc": boot["modelos"][c]["roc_auc"],
                      "pr_auc": float(metricas.pr_auc(y_v, s)), "r": r, "r2": r * r})
    filas.sort(key=lambda f: -f["roc_auc"]["punto"])

    resultado = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "tabla_sha256": huella,
                 "aprende_con": "entrenamiento (2023)", "mide_en": "validación (2024)",
                 "clientes_validacion": int(len(y_v)), "tasa_validacion": float(np.mean(y_v)),
                 "repeticiones_bootstrap": REPETICIONES, "semilla": SEMILLA, "C_modelo": C,
                 "versiones": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                               "scikit-learn": __import__("sklearn").__version__},
                 "variables": filas}
    with open(os.path.join(SALIDA, "variables_solas.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, ensure_ascii=False, indent=1)

    # Punto de miles solo en la cantidad: un .replace sobre la frase entera cambiaría también sus comas
    clientes_val = f"{len(y_v):,}".replace(",", ".")
    md = ["# Cada variable sola · validación (cohorte 2024) · exploratorio", "",
          f"Generado por `modelo/variables_solas.py` el {resultado['generado'][:10]}. Tabla `{huella[:12]}…`. "
          "Descriptivo: no elige, no ajusta nada y no usa el bloque de prueba.", "",
          "**Cómo se midió.** Para cada variable, la tasa de vuelta de cada valor se aprende con entrenamiento (2023) "
          "y se usa como puntaje en validación (2024); las numéricas, en quintiles de entrenamiento. "
          f"Validación: {clientes_val} clientes, vuelve el {num(100 * np.mean(y_v), 1)}%. "
          "ROC-AUC con intervalo bootstrap del 95% (2000 remuestreos). Azar: ROC-AUC 0,5; PR-AUC igual a la tasa de vuelta.", "",
          "**Sobre r y r².** r es la correlación entre el puntaje y la vuelta (0 o 1). Con una etiqueta de sí o no, "
          "r² queda bajo aunque la variable ordene bien: no se lee como «porcentaje explicado». La medida que corresponde "
          "a la pregunta (ordenar a quién llamar) es la de orden.", "",
          "| Variable | Grupo | ROC-AUC | PR-AUC | r | r² |", "|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| {f['nombre']} | {f['grupo']} | {intervalo(f['roc_auc'])} | {num(f['pr_auc'])} | "
                  f"{num(f['r'])} | {num(f['r2'])} |")
    with open(os.path.join(SALIDA, "variables_solas.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md[-len(filas):]))


if __name__ == "__main__":
    main()
