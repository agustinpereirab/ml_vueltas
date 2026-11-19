"""Interpretacion de la logistica: grupos de variables, SHAP y odds ratios.

SHAP de un modelo lineal, con las variables tratadas como independientes, es
exacto y tiene forma cerrada: la contribucion de la columna j al logit del
cliente i es w_j * (x_ij - media_j), con la media tomada sobre el fondo
(entrenamiento). La contribucion de una variable es la suma de sus columnas
(todas las categorias de una variable en one-hot, o la numerica y su
indicador de faltante). Base + suma de contribuciones = logit del modelo.

Se lee como asociacion, no como causa.
"""
import numpy as np
import pandas as pd

from modelo import datos

GRUPOS = {
    "H2 · compañía previa": ["fue_acompaniante_antes", "viajes_previos_acompaniante",
                             "viaja_con_cliente_previo", "viaja_con_alguien_con_historial"],
    "H2 · destino": ["region_destino", "pais_destino"],
    "H2 · vendedor": ["vendedor", "vendedor_es_persona", "vendedor_fichas_12m", "vendedor_antiguedad"],
    "Datos de contacto (día 0)": list(datos.DIA0),
    "Montos": ["venta_usd", "venta_por_pasajero_usd", "utilidad_indice"],
    "Producto": ["tipo_producto", "aerolinea", "regimen_hotel", "lleva_hotel", "tiene_seguro",
                 "servicios", "canje_millas", "pagador"],
    "Viaje": ["pasajeros", "destinos", "noches", "anticipacion"],
}
REGIONALES = ("AR", "BR", "CL", "PY")


def transformar(modelo, x):
    z = modelo.named_steps["pre"].transform(x)
    return z.toarray() if hasattr(z, "toarray") else np.asarray(z)


def columnas_por_variable(modelo):
    """La variable original de cada columna de la matriz transformada."""
    salida = []
    for nombre, transformador, columnas in modelo.named_steps["pre"].transformers_:
        if transformador == "drop" or len(columnas) == 0:
            continue
        if nombre == "cat":
            for variable, categorias in zip(columnas, transformador.categories_):
                salida += [variable] * len(categorias)
        elif nombre == "num":
            imputador = transformador.named_steps["imputar"]
            salida += list(columnas)
            if imputador.indicator_ is not None:
                salida += [columnas[i] for i in imputador.indicator_.features_]
    return salida


def shap_lineal(modelo, x_fondo, x):
    """(base, contribuciones): base es un numero; contribuciones, un DataFrame
    clientes x variables en la escala logit."""
    lr = modelo.named_steps["modelo"]
    w = lr.coef_[0]
    media = transformar(modelo, x_fondo).mean(axis=0)
    aporte = (transformar(modelo, x) - media) * w
    variables = np.array(columnas_por_variable(modelo))
    orden = list(dict.fromkeys(variables))
    s = pd.DataFrame({v: aporte[:, variables == v].sum(axis=1) for v in orden}, index=x.index)
    return float(lr.intercept_[0] + media @ w), s


def por_grupo(s, grupos):
    return pd.DataFrame({g: s[[v for v in vs if v in s.columns]].sum(axis=1) for g, vs in grupos.items()})


def odds_ratios(modelo, variable, referencia):
    """Odds ratio de cada categoria de `variable` contra `referencia`, con el
    resto de las variables fijas: exp(coef_categoria - coef_referencia)."""
    pre = modelo.named_steps["pre"]
    w = modelo.named_steps["modelo"].coef_[0]
    inicio = 0
    for nombre, transformador, columnas in pre.transformers_:
        if nombre != "cat":
            continue
        for v, categorias in zip(columnas, transformador.categories_):
            if v == variable:
                coefs = {str(c): w[inicio + i] for i, c in enumerate(categorias)}
                ref = coefs[str(referencia)]
                return {c: float(np.exp(b - ref)) for c, b in coefs.items()}
            inicio += len(categorias)
    raise KeyError(variable)


def con_regional(x):
    """Cambia pais y region de destino por una sola marca: viaja a Argentina,
    Brasil, Chile o Paraguay (la formulacion de H2)."""
    r = x.drop(columns=["pais_destino", "region_destino"]).copy()
    r["destino_regional"] = np.where(x["pais_destino"].isin(REGIONALES), "1", "0").astype(object)
    return r
