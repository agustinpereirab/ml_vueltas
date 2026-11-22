"""Cómo llena la regla del acompañante el cupo del 20% en la prueba · posterior a la prueba.

    python modelo/campania_regla.py

Descriptivo hecho DESPUÉS de correr la prueba, para respaldar una cifra del informe y de la
defensa: cuántos clientes de la prueba viajaron antes como acompañantes y cuántas vueltas capta la
regla «viajó antes como acompañante» al seleccionar el 20%. No entrena, no ajusta ni elige nada.

La regla da la misma probabilidad a todos los acompañantes previos y otra, más baja, al resto.
Si el cupo supera a los acompañantes, los toma a todos y completa el cupo con el resto; como ahí
hay empate, se cuenta lo esperado al desempatar al azar (igual que `modelo/metricas.py`). La
captura así calculada tiene que coincidir con la de la regla en `prueba.json`.

Escribe `modelo/resultados/campania_regla.*`.
"""
import datetime
import json
import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos  # noqa: E402
from modelo.escalera import huella_tabla, num, pct  # noqa: E402

SALIDA = os.path.join(REPO, "modelo", "resultados")
FRAC = 0.20


def main():
    huella = huella_tabla()
    with open(os.path.join(SALIDA, "prueba.json"), encoding="utf-8") as fh:
        prueba = json.load(fh)
    if prueba["tabla_sha256"] != huella:
        raise SystemExit("la prueba se corrió con otra tabla")

    d = pd.read_csv(datos.RUTA, dtype=str, keep_default_na=False)
    d = d[d["bloque"] == "prueba"]
    y = (d[datos.ETIQUETA] == "1").astype(int)
    acomp = d["fue_acompaniante_antes"] == "1"

    n, vueltas = len(d), int(y.sum())
    n_a, v_a = int(acomp.sum()), int(y[acomp].sum())
    n_o, v_o = n - n_a, vueltas - v_a
    plazas = FRAC * n
    if plazas >= n_a:
        esperadas = v_a + (plazas - n_a) * v_o / n_o
    else:
        esperadas = plazas * v_a / n_a
    captura = esperadas / vueltas
    referencia = prueba["evaluacion"]["regla_acompaniante"]["captura_20"]
    if abs(captura - referencia) > 1e-9:
        raise SystemExit(f"no coincide con prueba.json: {captura} contra {referencia}")

    modelo = prueba["campania"]["por_probabilidad"]
    lift = prueba["bootstrap"]["diferencias"]["principal - regla_acompaniante"]["lift_20"]
    dif = {k: FRAC * lift[k] for k in ("punto", "desde", "hasta")}   # captura = lift × 0,20

    r = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "tabla_sha256": huella,
         "posterior_a_la_prueba": True, "clientes": n, "vuelven": vueltas, "plazas": plazas,
         "acompaniantes_previos": n_a, "vuelven_acompaniantes": v_a, "resto": n_o, "vuelven_resto": v_o,
         "regla": {"vueltas_esperadas": esperadas, "captura": captura},
         "logistica": {"vueltas": modelo["vuelven_contactados"], "captura": modelo["captura"]},
         "diferencia_captura_logistica_menos_regla": dif,
         "fuente_diferencia": "prueba.json, diferencia declarada de lift al 20% (logística − regla) multiplicada por 0,20"}
    with open(os.path.join(SALIDA, "campania_regla.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)

    md = [
        "# La regla del acompañante con el cupo del 20% · *posterior a la prueba*", "",
        f"Generado por `modelo/campania_regla.py` el {r['generado'][:10]}. Tabla `{huella[:12]}…`. Descriptivo hecho "
        "**después** de correr la prueba, para respaldar cifras del informe. No entrena, no ajusta ni elige nada.", "",
        "| | Prueba (enero a agosto de 2025) |", "|---|---|",
        f"| Clientes | {n:,} |".replace(",", "."),
        f"| Vuelven | {vueltas:,} |".replace(",", "."),
        f"| Cupo del 20% | {num(plazas, 1)} plazas |",
        f"| Viajaron antes como acompañantes | {n_a:,} (vuelven {v_a:,}) |".replace(",", "."),
        f"| Resto | {n_o:,} (vuelven {v_o:,}) |".replace(",", "."),
        f"| Regla: vueltas en el cupo (esperadas) | {num(esperadas, 1)} ({pct(captura)}) |",
        f"| Logística principal: vueltas en el cupo | {num(modelo['vuelven_contactados'], 0)} ({pct(modelo['captura'])}) |", "",
        "**Cómo llena el cupo la regla.** Toma a todos los acompañantes previos y completa las plazas con el resto; como "
        "ahí todos empatan, se cuenta lo esperado al desempatar al azar. Coincide con la captura de la regla en `prueba.json`.", "",
        f"**Diferencia de captura, logística − regla:** {num(100 * dif['punto'], 2)} puntos porcentuales "
        f"[{num(100 * dif['desde'], 2)}; {num(100 * dif['hasta'], 2)}]. No es un cálculo nuevo: es la diferencia de lift al 20% "
        "declarada en el plan de la prueba (`prueba.json`), multiplicada por 0,20.",
    ]
    with open(os.path.join(SALIDA, "campania_regla.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
