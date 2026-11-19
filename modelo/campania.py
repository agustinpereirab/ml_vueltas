"""Simulacion de campania: si la agencia contacta al `frac` de clientes con
mayor puntaje, cuantos de los que vuelven quedan contactados, contra
contactar a la misma cantidad al azar.

Mide propension, no efecto: cuenta a quienes iban a volver y quedaron en el
grupo contactado. Cuanto agrega contactarlos no se puede saber sin un
experimento (limitacion declarada en la propuesta).

Los empates en el borde se reparten en proporcion, igual que en `metricas`.
"""
import numpy as np

from modelo.metricas import _positivos_arriba


def simular(y, puntaje, frac=0.2, valor=None):
    y = np.asarray(y, dtype=float)
    n = len(y)
    k = frac * n
    vuelven = _positivos_arriba(y, puntaje, k)
    r = {"frac": frac, "contactados": int(round(k)), "vuelven_total": int(y.sum()),
         "vuelven_contactados": float(vuelven), "vuelven_contactados_azar": float(frac * y.sum()),
         "captura": float(vuelven / y.sum()), "tasa_contactados": float(vuelven / k),
         "lift": float((vuelven / k) / y.mean())}
    if valor is not None:
        peso = y * np.asarray(valor, dtype=float)
        r["valor_capturado"] = float(_positivos_arriba(peso, puntaje, k) / peso.sum())
        r["valor_capturado_azar"] = float(frac)
    return r


def curva(y, puntaje, pasos=tuple(np.round(np.arange(0.05, 1.0001, 0.05), 2))):
    return [simular(y, puntaje, float(f)) for f in pasos]
