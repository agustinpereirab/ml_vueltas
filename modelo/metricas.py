"""Metricas de la escalera de modelos.

Todas reciben `y` (0/1) y un puntaje por cliente. Las de orden (ROC-AUC,
PR-AUC, lift, captura) solo miran el orden del puntaje; las de probabilidad
(Brier, log-loss, calibracion) necesitan que el puntaje sea una probabilidad.

El lift trata los empates como un sorteo: si el corte del 20 % cae en medio
de un grupo de clientes con el mismo puntaje, entra la parte proporcional de
ese grupo y, en promedio, la parte proporcional de sus positivos. Asi la regla
simple, que solo tiene dos puntajes, se mide sin ventaja ni castigo por el
desempate.
"""
import numpy as np

METRICAS = ["roc_auc", "pr_auc", "lift_10", "lift_20", "captura_20",
            "brier", "log_loss", "exactitud_05"]
# en estas, mas chico es mejor
MENOR_ES_MEJOR = {"brier", "log_loss"}


# ------------------------------------------------------------------- orden
# Todas las metricas de orden salen de los grupos de clientes con el mismo
# puntaje, de mayor a menor: cuantos positivos y cuantos clientes tiene cada
# uno. Asi se ordena una sola vez por modelo y por repeticion del bootstrap.
def grupos(y, s):
    y = np.asarray(y, dtype=float)
    s = np.asarray(s, dtype=float)
    orden = np.argsort(-s, kind="mergesort")
    s_ord = s[orden]
    inicio = np.concatenate([[0], np.flatnonzero(np.diff(s_ord)) + 1])
    tam = np.diff(np.concatenate([inicio, [len(s)]]))
    return np.add.reduceat(y[orden], inicio), tam


def _arriba(pos, tam, frac):
    antes = np.cumsum(tam) - tam
    entra = np.clip((frac * tam.sum() - antes) / tam, 0.0, 1.0)
    return float(np.sum(entra * pos))


def _roc_auc(pos, tam):
    """Probabilidad de que un positivo tenga mas puntaje que un negativo (empate: 1/2)."""
    neg = tam - pos
    P, N = pos.sum(), neg.sum()
    negativos_abajo = N - np.cumsum(neg)
    return float((np.sum(pos * negativos_abajo) + 0.5 * np.sum(pos * neg)) / (P * N))


def _pr_auc(pos, tam):
    """Precision promedio, como `average_precision_score`: un umbral por puntaje distinto."""
    vp = np.cumsum(pos)
    precision = vp / np.cumsum(tam)
    sensibilidad = vp / vp[-1]
    return float(np.sum(np.diff(np.concatenate([[0.0], sensibilidad])) * precision))


def positivos_arriba(y, s, frac):
    """Positivos esperados entre el `frac` de clientes de mayor puntaje."""
    return _arriba(*grupos(y, s), frac)


def lift(y, s, frac):
    """Tasa de positivos en el `frac` de arriba, dividida por la tasa general."""
    y = np.asarray(y, dtype=float)
    return (positivos_arriba(y, s, frac) / (frac * len(y))) / y.mean()


def captura(y, s, frac):
    """Parte de todos los positivos que cae en el `frac` de arriba."""
    y = np.asarray(y, dtype=float)
    return positivos_arriba(y, s, frac) / y.sum()


# ------------------------------------------------------------ probabilidad
def brier(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def log_loss(y, p):
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calibracion(y, p, grupos=10):
    """Tramos de probabilidad predicha: cuantos clientes, cuanto se predijo y cuanto volvio.

    Con mas de `grupos` valores distintos, parte a los clientes ordenados en
    `grupos` partes iguales; con menos, hace un tramo por valor.
    """
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    orden = np.argsort(p, kind="mergesort")
    valores = np.unique(p)
    if len(valores) <= grupos:
        partes = [orden[p[orden] == v] for v in valores]
    else:
        partes = np.array_split(orden, grupos)
    return [{"n": int(len(i)), "p_media": float(p[i].mean()), "tasa": float(y[i].mean())}
            for i in partes]


def recta_calibracion(y, p):
    """Ordenada y pendiente de la logistica de y sobre logit(p). Bien calibrado: (0, 1)."""
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    if np.ptp(p) == 0:
        return float("nan"), float("nan")
    X = np.column_stack([np.ones_like(p), np.log(p / (1 - p))])
    beta = np.array([0.0, 1.0])
    for _ in range(100):
        mu = 1 / (1 + np.exp(-(X @ beta)))
        paso = np.linalg.solve(X.T @ (X * (mu * (1 - mu))[:, None]), X.T @ (y - mu))
        beta += paso
        if np.max(np.abs(paso)) < 1e-10:
            break
    return float(beta[0]), float(beta[1])


# ------------------------------------------------------------------- todas
def todas(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    pos, tam = grupos(y, p)
    tasa, total = y.mean(), y.sum()
    return {
        "roc_auc": _roc_auc(pos, tam),
        "pr_auc": _pr_auc(pos, tam),
        "lift_10": _arriba(pos, tam, 0.10) / (0.10 * len(y)) / tasa,
        "lift_20": _arriba(pos, tam, 0.20) / (0.20 * len(y)) / tasa,
        "captura_20": _arriba(pos, tam, 0.20) / total,
        "brier": brier(y, p),
        "log_loss": log_loss(y, p),
        "exactitud_05": float(np.mean((p >= 0.5) == (y == 1))),
    }


def _intervalo(valor, muestras, nivel):
    cola = (1 - nivel) / 2 * 100
    desde, hasta = np.percentile(muestras, [cola, 100 - cola])
    return {"valor": float(valor), "desde": float(desde), "hasta": float(hasta)}


def bootstrap(y, puntajes, pares=(), repeticiones=2000, semilla=0, nivel=0.95):
    """Intervalos bootstrap de cada metrica, y de la diferencia entre pares de modelos.

    Pareado: en cada repeticion todos los modelos se miden sobre la misma
    muestra de clientes, asi la diferencia descuenta lo que se mueve igual
    para todos. `pares` es una lista de (a, b) y se reporta a - b.
    """
    y = np.asarray(y)
    puntajes = {m: np.asarray(p, dtype=float) for m, p in puntajes.items()}
    rng = np.random.default_rng(semilla)
    n = len(y)
    puntos = {m: todas(y, p) for m, p in puntajes.items()}
    muestras = {m: {k: np.empty(repeticiones) for k in METRICAS} for m in puntajes}
    for b in range(repeticiones):
        i = rng.integers(0, n, n)
        yb = y[i]
        for m, p in puntajes.items():
            for k, v in todas(yb, p[i]).items():
                muestras[m][k][b] = v
    modelos = {m: {k: _intervalo(puntos[m][k], muestras[m][k], nivel) for k in METRICAS}
               for m in puntajes}
    diferencias = {}
    for a, b in pares:
        diferencias["%s - %s" % (a, b)] = {
            k: _intervalo(puntos[a][k] - puntos[b][k], muestras[a][k] - muestras[b][k], nivel)
            for k in METRICAS}
    return {"repeticiones": repeticiones, "semilla": semilla, "nivel": nivel,
            "modelos": modelos, "diferencias": diferencias}
