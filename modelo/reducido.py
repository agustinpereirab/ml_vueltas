"""Modelo secundario: la logistica solo con compania previa, datos de contacto
del dia 0 y viaje.

    python modelo/reducido.py

Los grupos salen de `interpretar.py` (los unicos con aporte propio en
validacion). Por eso sus numeros de validacion son optimistas: se eligieron
mirando ese bloque. La prueba decide. C se elige con validacion cruzada
dentro de entrenamiento, como en la escalera; la recalibracion, con el mismo
criterio que el modelo principal. El bloque de prueba no se carga.

Escribe `modelo/resultados/reducido_validacion.*`.
"""
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos, metricas, modelos  # noqa: E402
from modelo import interpretacion as it  # noqa: E402
from modelo.escalera import CS, SEMILLA, huella_tabla, intervalo, num, pct  # noqa: E402
from modelo.recalibrar import NOMBRES, REPETICIONES, comparar_calibraciones  # noqa: E402

SALIDA = os.path.join(REPO, "modelo", "resultados")
GRUPOS_REDUCIDO = ["H2 · compañía previa", "Datos de contacto (día 0)", "Viaje"]
COLUMNAS = [v for g in GRUPOS_REDUCIDO for v in it.GRUPOS[g]]
METRICAS_BOOT = {"pr_auc": metricas.pr_auc, "roc_auc": metricas.roc_auc,
                 "lift_20": lambda y, p: metricas.lift_en(y, p, 0.20), "brier": metricas.brier,
                 "log_loss": metricas.log_loss}


def main():
    huella = huella_tabla()
    with open(os.path.join(SALIDA, "escalera_validacion.json"), encoding="utf-8") as fh:
        escalera = json.load(fh)
    if escalera["tabla_sha256"] != huella:
        raise SystemExit("la escalera se corrio con otra tabla: correr modelo/escalera.py")
    C_completo = escalera["hiperparametros"]["logistica"]["dia0"]["C"]

    d = datos.cargar()
    x_e, y_e, x_v, y_v = datos.separar(d, "dia0")
    cats, nums = datos.tipos(datos.BRAZOS["dia0"])
    p_completo = modelos._logistica(cats, nums, C_completo).fit(x_e, y_e).predict_proba(x_v)[:, 1]

    cats_r, nums_r = datos.tipos(COLUMNAS)
    aj = modelos.ajustar_logistica(x_e[COLUMNAS], y_e, cats_r, nums_r, CS, SEMILLA)
    p_reducido = aj["modelo"].predict_proba(x_v[COLUMNAS])[:, 1]
    print("reducido: %d variables, C=%s" % (len(COLUMNAS), aj["C"]), flush=True)

    boot = metricas.bootstrap(y_v, {"reducido": p_reducido, "completo": p_completo}, METRICAS_BOOT,
                              [("reducido", "completo")], REPETICIONES, SEMILLA)
    c = comparar_calibraciones(p_reducido, y_v)
    print("calibracion elegida: %s" % c["elegido"], flush=True)

    resultado = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"), "tabla_sha256": huella,
        "grupos": GRUPOS_REDUCIDO, "columnas": COLUMNAS, "C": aj["C"], "pr_auc_cv": aj["cv"],
        "C_completo": C_completo, "bootstrap": boot,
        "calibracion": {"evaluacion_fuera_de_pliegue": c["evaluacion"], "mejor_por_log_loss": c["mejor"],
                        "elegido": c["elegido"], "calibrador": c["final"].parametros()},
    }
    with open(os.path.join(SALIDA, "reducido_validacion.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(SALIDA, "reducido_validacion.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(informe(resultado))
    print("listo -> modelo/resultados/reducido_validacion.md")


def informe(r):
    b = r["boot"] if "boot" in r else r["bootstrap"]
    l = ["# Modelo secundario: logística reducida · validación (cohorte 2024)\n"]
    l.append("Generado por `modelo/reducido.py` el %s. Tabla `%s…`. El bloque de prueba no se usó.\n" % (
        r["generado"][:10], r["tabla_sha256"][:12]))
    l.append("**Variables (%d):** los grupos %s.\n" % (len(r["columnas"]), ", ".join("«%s»" % g for g in r["grupos"])))
    l.append("**Advertencia.** Los grupos se eligieron mirando validación (`interpretar.py`): los números de "
             "esta página son optimistas para el modelo reducido. La comparación que cuenta es la de la "
             "prueba.\n")
    l.append("C = %s, elegido por PR-AUC en validación cruzada de 5 pliegues dentro de entrenamiento (%s).\n" % (
        num(r["C"], 3), ", ".join("C=%s: %s" % (k, num(v)) for k, v in r["pr_auc_cv"].items())))
    l.append("| Modelo | PR-AUC | ROC-AUC | Lift 20% | Brier | Log-loss |")
    l.append("|---|---|---|---|---|---|")
    for m, nombre in (("completo", "Logística completa (principal)"), ("reducido", "Logística reducida")):
        x = b["modelos"][m]
        l.append("| %s | %s | %s | %s | %s | %s |" % (nombre, intervalo(x["pr_auc"]), intervalo(x["roc_auc"]),
                                                     intervalo(x["lift_20"], 2), intervalo(x["brier"], 4),
                                                     intervalo(x["log_loss"], 4)))
    dif = b["diferencias"]["reducido - completo"]
    l.append("| Reducida − completa | %s |\n" % " | ".join(
        intervalo(dif[k], 4 if k in ("brier", "log_loss") else 3) for k in ("pr_auc", "roc_auc", "lift_20", "brier", "log_loss")))
    cal = r["calibracion"]
    l.append("## Recalibración\n")
    l.append("Mismo criterio que el modelo principal: menor log-loss fuera de pliegue; el más simple si no es "
             "peor con intervalo.\n")
    l.append("| Método | Log-loss | ECE | Prob. media | Pendiente |")
    l.append("|---|---|---|---|---|")
    for m, e in cal["evaluacion_fuera_de_pliegue"].items():
        l.append("| %s | %s | %s | %s | %s |" % (NOMBRES[m], num(e["log_loss"], 4), num(e["ece"], 4),
                                               pct(e["p_media"]), num(e["pendiente"], 2)))
    l.append("\nElegido: **%s** (menor log-loss: %s). Parámetros: `%s`.\n" % (
        NOMBRES[cal["elegido"]], NOMBRES[cal["mejor_por_log_loss"]],
        json.dumps(cal["calibrador"]) if cal["elegido"] != "isotonica" else "función escalonada"))
    return "\n".join(l)


if __name__ == "__main__":
    main()
