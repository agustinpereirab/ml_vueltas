"""Escalera de modelos, evaluada en VALIDACION (cohorte 2024).

    python modelo/escalera.py

Escalones: prevalencia -> dos reglas simples -> regresion logistica ->
CatBoost. Los dos ultimos se ajustan en tres brazos (dia0, ficha_unica,
sin_contacto) para la hipotesis 3. Los hiperparametros se eligen con
validacion cruzada dentro de entrenamiento (2023); la validacion solo se usa
para medir. El bloque de prueba (2025) no se carga.

Escribe `modelo/resultados/escalera_validacion.md` y `.json`: metricas,
intervalos bootstrap pareados y la calibracion por decil. No escribe
predicciones por cliente.
"""
import datetime
import hashlib
import json
import os
import platform
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos, metricas, modelos  # noqa: E402

SEMILLA = 2026
REPETICIONES = 2000
CS = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
CONFIGS_CATBOOST = [{"depth": d, "l2_leaf_reg": l} for d in (4, 6) for l in (3, 10)]
SALIDA = os.path.join(REPO, "modelo", "resultados")

REGLAS = {
    "regla_10mil": ("Regla: primer viaje de 10 mil USD o más",
                    lambda d: d["venta_usd"].fillna(0).to_numpy() >= 10000),
    "regla_acompaniante": ("Regla: viajó antes como acompañante",
                           lambda d: (d["fue_acompaniante_antes"] == "1").to_numpy()),
}
NOMBRES = {
    "prevalencia": "Prevalencia (a todos la misma probabilidad)",
    **{k: v[0] for k, v in REGLAS.items()},
    "logistica_dia0": "Logística · día 0",
    "catboost_dia0": "CatBoost · día 0",
    "logistica_ficha_unica": "Logística · ficha única",
    "catboost_ficha_unica": "CatBoost · ficha única",
    "logistica_sin_contacto": "Logística · sin datos de contacto",
    "catboost_sin_contacto": "CatBoost · sin datos de contacto",
}
METRICAS_BOOT = {
    "pr_auc": metricas.pr_auc,
    "roc_auc": metricas.roc_auc,
    "lift_20": lambda y, p: metricas.lift_en(y, p, 0.20),
    "brier": metricas.brier,
}
ETIQUETA_METRICA = {"pr_auc": "PR-AUC", "roc_auc": "ROC-AUC", "lift_20": "Lift 20%", "brier": "Brier"}


def huella_tabla():
    with open(datos.RUTA, "rb") as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(REPO, "datos", "manifiesto.json"), encoding="utf-8") as fh:
        esperado = json.load(fh)["sha256"]
    if h != esperado:
        raise SystemExit("datos/tabla_modelo.csv no coincide con datos/manifiesto.json: "
                         "correr exportacion/03_verificar.py")
    return h


def num(x, d=3):
    return ("%.*f" % (d, x)).replace(".", ",")


def pct(x, d=1):
    return num(100 * x, d) + "%"


def intervalo(v, d=3):
    return "%s [%s; %s]" % (num(v["punto"], d), num(v["desde"], d), num(v["hasta"], d))


def main():
    t0 = time.time()
    huella = huella_tabla()
    d = datos.cargar()
    ent = d[d["bloque"] == "entrenamiento"].reset_index(drop=True)
    val = d[d["bloque"] == "validacion"].reset_index(drop=True)
    y_e = ent[datos.ETIQUETA].to_numpy()
    y_v = val[datos.ETIQUETA].to_numpy()
    print("entrenamiento %d (vuelve %s) · validacion %d (vuelve %s)" % (
        len(ent), pct(y_e.mean()), len(val), pct(y_v.mean())), flush=True)

    pred, info = {}, {"reglas": {}, "logistica": {}, "catboost": {}}
    pred["prevalencia"] = modelos.prevalencia(y_e, len(val))

    for clave, (_, grupo) in REGLAS.items():
        g_e, g_v = grupo(ent), grupo(val)
        pred[clave] = modelos.regla(g_e, y_e, g_v)
        en_ent = modelos.regla(g_e, y_e, g_e)
        info["reglas"][clave] = {"pr_auc_entrenamiento": metricas.pr_auc(y_e, en_ent),
                                 "clientes_en_la_regla_entrenamiento": int(g_e.sum()),
                                 "tasa_si": float(y_e[g_e].mean()), "tasa_no": float(y_e[~g_e].mean())}
    mejor_regla = max(info["reglas"], key=lambda k: info["reglas"][k]["pr_auc_entrenamiento"])
    info["mejor_regla"] = mejor_regla
    print("mejor regla en entrenamiento: %s" % mejor_regla, flush=True)

    for brazo in ("dia0", "ficha_unica", "sin_contacto"):
        x_e, _, x_v, _ = datos.separar(d, brazo)
        cats, nums = datos.tipos(datos.BRAZOS[brazo])
        t = time.time()
        aj = modelos.ajustar_logistica(x_e, y_e, cats, nums, CS, SEMILLA)
        pred["logistica_" + brazo] = aj["modelo"].predict_proba(x_v)[:, 1]
        info["logistica"][brazo] = {"C": aj["C"], "pr_auc_cv": aj["cv"]}
        print("logistica %-12s C=%s (%.0fs)" % (brazo, aj["C"], time.time() - t), flush=True)
        t = time.time()
        aj = modelos.ajustar_catboost(x_e, y_e, cats, CONFIGS_CATBOOST, SEMILLA)
        pred["catboost_" + brazo] = aj["modelo"].predict_proba(x_v)[:, 1]
        info["catboost"][brazo] = {"params": aj["params"], "iteraciones": aj["iteraciones"], "cv": aj["cv"]}
        print("catboost  %-12s %s, %d arboles (%.0fs)" % (brazo, aj["params"], aj["iteraciones"],
                                                         time.time() - t), flush=True)

    evaluacion = {m: metricas.evaluar(y_v, p) for m, p in pred.items()}
    otra_regla = [k for k in REGLAS if k != mejor_regla][0]
    pares = [
        (mejor_regla, "prevalencia"),
        (otra_regla, "prevalencia"),
        ("logistica_dia0", mejor_regla),
        ("catboost_dia0", "logistica_dia0"),
        ("logistica_ficha_unica", "logistica_dia0"),
        ("catboost_ficha_unica", "catboost_dia0"),
        ("logistica_dia0", "logistica_sin_contacto"),
        ("catboost_dia0", "catboost_sin_contacto"),
    ]
    t = time.time()
    boot = metricas.bootstrap(y_v, pred, METRICAS_BOOT, pares, REPETICIONES, SEMILLA)
    print("bootstrap %d repeticiones (%.0fs)" % (REPETICIONES, time.time() - t), flush=True)
    calib = {m: metricas.calibracion(y_v, pred[m]) for m in ("logistica_dia0", "catboost_dia0")}

    import catboost
    import sklearn
    resultado = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "tabla_sha256": huella,
        "bloques": {"entrenamiento": int(len(ent)), "validacion": int(len(val))},
        "semilla": SEMILLA, "repeticiones_bootstrap": REPETICIONES,
        "versiones": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                      "catboost": catboost.__version__, "numpy": np.__version__},
        "hiperparametros": info, "validacion": evaluacion, "bootstrap": boot, "calibracion": calib,
    }
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "escalera_validacion.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(SALIDA, "escalera_validacion.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(informe(resultado, pares))
    print("listo en %.0fs -> modelo/resultados/" % (time.time() - t0))


def informe(r, pares):
    ev, boot, info = r["validacion"], r["bootstrap"], r["hiperparametros"]
    escalera = ["prevalencia", "regla_10mil", "regla_acompaniante", "logistica_dia0", "catboost_dia0"]
    brazos = ["logistica_sin_contacto", "logistica_dia0", "logistica_ficha_unica",
              "catboost_sin_contacto", "catboost_dia0", "catboost_ficha_unica"]
    l = []
    l.append("# Escalera de modelos · validación (cohorte 2024)\n")
    l.append("Generado por `modelo/escalera.py` el %s. Tabla `%s…`. Entrenamiento: %s clientes (2023). "
             "Validación: %s clientes (2024). El bloque de prueba no se usó.\n" % (
                 r["generado"][:10], r["tabla_sha256"][:12],
                 "{:,}".format(r["bloques"]["entrenamiento"]).replace(",", "."),
                 "{:,}".format(r["bloques"]["validacion"]).replace(",", ".")))
    l.append("Entre corchetes, intervalo bootstrap del 95%% (%d remuestreos pareados de los clientes de "
             "validación). Brier: más bajo es mejor; el resto, más alto es mejor.\n" % r["repeticiones_bootstrap"])

    def tabla(modelos_):
        l.append("| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% | Captura 20% | Brier | Prob. media |")
        l.append("|---|---|---|---|---|---|---|---|")
        for m in modelos_:
            e, b = ev[m], boot["modelos"][m]
            l.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                NOMBRES[m], intervalo(b["pr_auc"]), intervalo(b["roc_auc"]), num(e["lift_10"], 2),
                intervalo(b["lift_20"], 2), pct(e["captura_20"]), intervalo(b["brier"], 4),
                pct(e["p_media"])))
        l.append("")

    l.append("## La escalera (brazo día 0)\n")
    tabla(escalera)
    l.append("Tasa de vuelta observada en validación: %s. Captura 20%%: parte de todas las vueltas que cae "
             "en el 20%% de clientes con mayor probabilidad (al azar sería 20%%).\n" % pct(ev["prevalencia"]["tasa_observada"]))

    l.append("## ¿Cada escalón le gana al anterior?\n")
    l.append("Diferencia «modelo − referencia» en validación, con su intervalo. *Sí* = el intervalo no "
             "incluye el cero.\n")
    l.append("| Comparación | PR-AUC | ROC-AUC | Lift 20% | Brier |")
    l.append("|---|---|---|---|---|")
    for a, b in pares[:4]:
        dif = boot["diferencias"]["%s - %s" % (a, b)]
        celdas = []
        for k in ("pr_auc", "roc_auc", "lift_20", "brier"):
            v = dif[k]
            gana = (v["hasta"] < 0) if k == "brier" else (v["desde"] > 0)
            pierde = (v["desde"] > 0) if k == "brier" else (v["hasta"] < 0)
            marca = "sí" if gana else ("peor" if pierde else "no")
            celdas.append("%s · %s" % (intervalo(v, 4 if k == "brier" else 3), marca))
        l.append("| %s − %s | %s |" % (NOMBRES[a], NOMBRES[b], " | ".join(celdas)))
    l.append("")

    l.append("## Hipótesis 3: los tres brazos\n")
    l.append("Mismas variables salvo los datos de contacto: sin ellos, como estaban el día 0 (registro de "
             "la primera compra) y como están hoy en la ficha única.\n")
    tabla(brazos)
    l.append("| Comparación | PR-AUC | ROC-AUC | Lift 20% | Brier |")
    l.append("|---|---|---|---|---|")
    for a, b in pares[4:]:
        dif = boot["diferencias"]["%s - %s" % (a, b)]
        l.append("| %s − %s | %s |" % (NOMBRES[a], NOMBRES[b], " | ".join(
            intervalo(dif[k], 4 if k == "brier" else 3) for k in ("pr_auc", "roc_auc", "lift_20", "brier"))))
    l.append("")

    l.append("## Calibración (brazo día 0)\n")
    l.append("Clientes de validación ordenados por probabilidad y partidos en diez grupos iguales.\n")
    l.append("| Grupo | Logística: prob. media | Logística: vuelven | CatBoost: prob. media | CatBoost: vuelven |")
    l.append("|---|---|---|---|---|")
    for i, (a, b) in enumerate(zip(r["calibracion"]["logistica_dia0"], r["calibracion"]["catboost_dia0"]), 1):
        l.append("| %d | %s | %s | %s | %s |" % (i, pct(a["p_media"]), pct(a["observada"]),
                                                 pct(b["p_media"]), pct(b["observada"])))
    l.append("")

    l.append("## Cómo se eligió cada cosa (solo con entrenamiento)\n")
    for k, v in info["reglas"].items():
        l.append("- **%s:** %s clientes de entrenamiento la cumplen; vuelven %s contra %s del resto; "
                 "PR-AUC en entrenamiento %s." % (NOMBRES[k], "{:,}".format(v["clientes_en_la_regla_entrenamiento"]).replace(",", "."),
                                                  pct(v["tasa_si"]), pct(v["tasa_no"]), num(v["pr_auc_entrenamiento"])))
    l.append("- **Mejor regla** (la que se compara con la logística): %s." % NOMBRES[info["mejor_regla"]])
    for brazo, v in info["logistica"].items():
        l.append("- **Logística · %s:** C = %s, elegido por PR-AUC en validación cruzada de 5 pliegues "
                 "(%s)." % (brazo, v["C"], ", ".join("C=%s: %s" % (c, num(s)) for c, s in v["pr_auc_cv"].items())))
    for brazo, v in info["catboost"].items():
        l.append("- **CatBoost · %s:** profundidad %s, l2 %s, tasa %s, %d árboles (parada temprana por "
                 "log-loss en validación cruzada de 5 pliegues; configuración elegida por PR-AUC entre %d)." % (
                     brazo, v["params"]["depth"], v["params"]["l2_leaf_reg"], v["params"]["learning_rate"],
                     v["iteraciones"], len(v["cv"])))
    l.append("\nVersiones: %s. Semilla %d.\n" % (
        ", ".join("%s %s" % kv for kv in r["versiones"].items()), r["semilla"]))
    return "\n".join(l)


if __name__ == "__main__":
    main()
