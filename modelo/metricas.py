"""Metricas de la escalera de modelos.

Todas reciben `y` (0/1) y un puntaje o probabilidad por cliente. Las de
"los de arriba" (tasa, captura y lift en el x% superior) reparten los empates
en el borde en proporcion: es lo que da, en promedio, desempatar al azar. Sin
eso, una regla que solo tiene dos valores daria un lift que depende del orden
del archivo.
"""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def _positivos_arriba(y, score, k):
    """Positivos esperados entre los k clientes de puntaje mas alto."""
    y = np.asarray(y, dtype=float)
    valores, grupo = np.unique(np.asarray(score, dtype=float), return_inverse=True)
    n_g = np.bincount(grupo)[::-1]
    p_g = np.bincount(grupo, weights=y)[::-1]
    acumulado = np.cumsum(n_g)
    j = int(np.searchsorted(acumulado, k - 1e-9))
    j = min(j, len(n_g) - 1)
    n_arriba = acumulado[j - 1] if j > 0 else 0
    return p_g[:j].sum() + (k - n_arriba) * p_g[j] / n_g[j]


def tasa_en(y, score, frac):
    """Tasa de vuelta esperada en el `frac` de clientes mejor puntuados."""
    k = frac * len(y)
    return float(_positivos_arriba(y, score, k) / k)


def captura_en(y, score, frac):
    """Parte de todas las vueltas que cae en el `frac` mejor puntuado."""
    return float(_positivos_arriba(y, score, frac * len(y)) / np.sum(y))


def lift_en(y, score, frac):
    """Cuantas veces mas vuelve el `frac` mejor puntuado que el promedio."""
    return tasa_en(y, score, frac) / float(np.mean(y))


def brier(y, p):
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def roc_auc(y, score):
    return float(roc_auc_score(y, score))


def pr_auc(y, score):
    return float(average_precision_score(y, score))


def log_loss(y, p):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ece(y, p, grupos=10):
    """Error de calibracion esperado: promedio, ponderado por tamanio, de la
    distancia entre probabilidad media y tasa observada en cada decil."""
    n = len(y)
    return float(sum(g["n"] / n * abs(g["p_media"] - g["observada"]) for g in calibracion(y, p, grupos)))


def pendiente_e_intercepto(y, p):
    """Regresion logistica de y sobre logit(p). Bien calibrado: pendiente 1 e
    intercepto 0. Pendiente < 1: las probabilidades son demasiado extremas."""
    from modelo.calibracion import logit, newton
    z = logit(p)
    a, b = newton(np.column_stack([z, np.ones(len(z))]), y)
    return float(a), float(b)


def calibracion(y, p, grupos=10):
    """Clientes ordenados por probabilidad y partidos en `grupos` del mismo tamanio."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    orden = np.argsort(p, kind="mergesort")
    return [{"p_media": float(p[i].mean()), "observada": float(y[i].mean()), "n": int(len(i))}
            for i in np.array_split(orden, grupos)]


def evaluar(y, p):
    return {
        "roc_auc": roc_auc(y, p),
        "pr_auc": pr_auc(y, p),
        "lift_10": lift_en(y, p, 0.10),
        "lift_20": lift_en(y, p, 0.20),
        "captura_10": captura_en(y, p, 0.10),
        "captura_20": captura_en(y, p, 0.20),
        "brier": brier(y, p),
        "p_media": float(np.mean(p)),
        "tasa_observada": float(np.mean(y)),
    }


def _intervalo(punto, muestras):
    desde, hasta = np.percentile(muestras, [2.5, 97.5])
    return {"punto": float(punto), "desde": float(desde), "hasta": float(hasta)}


def bootstrap(y, predicciones, metricas, pares, repeticiones, semilla):
    """Bootstrap pareado: cada repeticion remuestrea los MISMOS clientes para
    todos los modelos, asi la diferencia entre dos modelos tiene su intervalo.

    Devuelve {"repeticiones", "modelos": {modelo: {metrica: intervalo}},
    "diferencias": {"a - b": {metrica: intervalo}}}, con intervalo =
    {"punto", "desde", "hasta"} (percentiles 2,5 y 97,5)."""
    y = np.asarray(y)
    n = len(y)
    rng = np.random.default_rng(semilla)
    punto = {m: {k: f(y, p) for k, f in metricas.items()} for m, p in predicciones.items()}
    muestras = {m: {k: [] for k in metricas} for m in predicciones}
    hechas = 0
    while hechas < repeticiones:
        idx = rng.integers(0, n, n)
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        for m, p in predicciones.items():
            pb = p[idx]
            for k, f in metricas.items():
                muestras[m][k].append(f(yb, pb))
        hechas += 1
    salida = {"repeticiones": repeticiones,
              "modelos": {m: {k: _intervalo(punto[m][k], muestras[m][k]) for k in metricas}
                          for m in predicciones},
              "diferencias": {}}
    for a, b in pares:
        salida["diferencias"]["%s - %s" % (a, b)] = {
            k: _intervalo(punto[a][k] - punto[b][k],
                          np.asarray(muestras[a][k]) - np.asarray(muestras[b][k]))
            for k in metricas}
    return salida
