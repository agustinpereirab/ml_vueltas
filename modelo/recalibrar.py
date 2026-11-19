"""Recalibracion de la logistica (brazo dia 0) con el bloque de validacion.

    python modelo/recalibrar.py

1. Vuelve a ajustar la logistica en entrenamiento (2023) con el C que eligio
   `escalera.py`, y comprueba que reproduce sus predicciones de validacion.
2. Compara cuatro recalibraciones (identidad, intercepto, Platt, isotonica)
   con validacion cruzada DENTRO de validacion (2024): cada cliente se
   recalibra con un ajuste que no lo vio.
3. Elige con un criterio fijado antes de ver los resultados: menor log-loss,
   salvo que un metodo mas simple no sea peor con intervalo.
4. Ajusta el metodo elegido con toda la validacion y guarda sus parametros,
   para aplicarlo a la prueba al final.

El bloque de prueba no se carga. Escribe `modelo/resultados/calibracion_validacion.*`.
"""
import datetime
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import calibracion as cal  # noqa: E402
from modelo import datos, metricas, modelos  # noqa: E402
from modelo.escalera import huella_tabla, intervalo, num, pct  # noqa: E402

SEMILLA = 2026
PLIEGUES = 5
REPETICIONES = 2000
SALIDA = os.path.join(REPO, "modelo", "resultados")
NOMBRES = {"identidad": "Sin recalibrar", "intercepto": "Intercepto", "platt": "Platt",
           "isotonica": "Isotónica"}
METRICAS_BOOT = {"log_loss": metricas.log_loss, "brier": metricas.brier, "ece": metricas.ece}


def main():
    huella = huella_tabla()
    with open(os.path.join(SALIDA, "escalera_validacion.json"), encoding="utf-8") as fh:
        escalera = json.load(fh)
    if escalera["tabla_sha256"] != huella:
        raise SystemExit("la escalera se corrio con otra tabla: correr modelo/escalera.py")
    C = escalera["hiperparametros"]["logistica"]["dia0"]["C"]

    d = datos.cargar()
    x_e, y_e, x_v, y_v = datos.separar(d, "dia0")
    cats, nums = datos.tipos(datos.BRAZOS["dia0"])
    p_v = modelos._logistica(cats, nums, C).fit(x_e, y_e).predict_proba(x_v)[:, 1]
    esperado = escalera["validacion"]["logistica_dia0"]["pr_auc"]
    if abs(metricas.pr_auc(y_v, p_v) - esperado) > 1e-9:
        raise SystemExit("la logistica no reproduce la escalera (PR-AUC %.6f contra %.6f)"
                         % (metricas.pr_auc(y_v, p_v), esperado))

    oof = {m: cal.fuera_de_pliegue(p_v, y_v, m, PLIEGUES, SEMILLA) for m in cal.ORDEN}
    evaluacion = {}
    for m, q in oof.items():
        pendiente, intercepto = metricas.pendiente_e_intercepto(y_v, q)
        evaluacion[m] = {"log_loss": metricas.log_loss(y_v, q), "brier": metricas.brier(y_v, q),
                         "ece": metricas.ece(y_v, q), "p_media": float(q.mean()),
                         "tasa_observada": float(y_v.mean()), "pendiente": pendiente,
                         "intercepto": intercepto, "pr_auc": metricas.pr_auc(y_v, q),
                         "roc_auc": metricas.roc_auc(y_v, q), "lift_20": metricas.lift_en(y_v, q, 0.2)}

    puntual = {m: e["log_loss"] for m, e in evaluacion.items()}
    mejor = min(puntual, key=puntual.get)
    pares = [(m, "identidad") for m in cal.ORDEN if m != "identidad"]
    pares += [(m, mejor) for m in cal.ORDEN if m != mejor and (m, mejor) not in pares]
    boot = metricas.bootstrap(y_v, oof, METRICAS_BOOT, pares, REPETICIONES, SEMILLA)
    contra_mejor = {m: (boot["diferencias"]["%s - %s" % (m, mejor)]["log_loss"]["desde"],
                        boot["diferencias"]["%s - %s" % (m, mejor)]["log_loss"]["hasta"])
                    for m in cal.ORDEN if m != mejor}
    elegido = cal.elegir(puntual, contra_mejor)
    final = cal.METODOS[elegido]().fit(p_v, y_v)

    resultado = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "tabla_sha256": huella, "modelo": "logistica_dia0", "C": C,
        "validacion_clientes": int(len(y_v)), "pliegues": PLIEGUES, "semilla": SEMILLA,
        "repeticiones_bootstrap": REPETICIONES,
        "criterio": "menor log-loss fuera de pliegue; si un método más simple no es peor con "
                    "intervalo del 95%%, el más simple (orden: %s)" % ", ".join(cal.ORDEN),
        "evaluacion_fuera_de_pliegue": evaluacion, "bootstrap": boot,
        "mejor_por_log_loss": mejor, "elegido": elegido, "calibrador": final.parametros(),
        "deciles": {"sin_recalibrar": metricas.calibracion(y_v, oof["identidad"]),
                    "recalibrada": metricas.calibracion(y_v, oof[elegido])},
    }
    with open(os.path.join(SALIDA, "calibracion_validacion.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)
    grafico(resultado, os.path.join(SALIDA, "calibracion_validacion.png"))
    with open(os.path.join(SALIDA, "calibracion_validacion.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(informe(resultado, pares))
    print("elegido: %s · %s" % (elegido, final.parametros() if elegido != "isotonica" else "isotonica"))
    for m in cal.ORDEN:
        e = evaluacion[m]
        print("  %-10s log-loss %.4f · Brier %.4f · ECE %.4f · prob. media %.1f%% · pendiente %.2f" % (
            m, e["log_loss"], e["brier"], e["ece"], 100 * e["p_media"], e["pendiente"]))


def grafico(r, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    superficie, tinta, tinta2, grilla, eje = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
    series = [("sin_recalibrar", "Sin recalibrar", "#2a78d6"),
              ("recalibrada", "Recalibrada (%s, fuera de pliegue)" % NOMBRES[r["elegido"]].lower(), "#eb6834")]
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    fig, ax = plt.subplots(figsize=(7.2, 5.4), dpi=160, facecolor=superficie)
    ax.set_facecolor(superficie)
    tope = 0.55
    ax.plot([0, tope], [0, tope], color=eje, linewidth=1, zorder=1)
    ax.text(0.405, 0.43, "calibración perfecta", color=tinta2, fontsize=9, rotation=36,
            rotation_mode="anchor")
    for clave, nombre, color in series:
        g = r["deciles"][clave]
        x = [v["p_media"] for v in g]
        y = [v["observada"] for v in g]
        ax.plot(x, y, color=color, linewidth=2, solid_capstyle="round", zorder=3, label=nombre)
        ax.scatter(x, y, s=64, color=color, edgecolors=superficie, linewidths=2, zorder=4)
    ax.set_xlim(0, tope)
    ax.set_ylim(0, tope)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(True, color=grilla, linewidth=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("bottom", "left"):
        ax.spines[lado].set_color(eje)
    ax.tick_params(colors=tinta2, length=0, pad=6)
    ax.set_xlabel("Probabilidad media del grupo", color=tinta2, labelpad=8)
    ax.set_ylabel("Tasa de vuelta observada", color=tinta2, labelpad=8)
    ax.set_title("Calibración de la logística en validación (2024), por decil",
                 color=tinta, loc="left", fontsize=12, fontweight="bold", pad=14)
    ley = ax.legend(loc="upper left", frameon=False, labelcolor=tinta2, handlelength=1.6)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=superficie)
    plt.close(fig)


def informe(r, pares):
    ev, boot = r["evaluacion_fuera_de_pliegue"], r["bootstrap"]
    l = ["# Recalibración · logística día 0 · validación (cohorte 2024)\n"]
    l.append("Generado por `modelo/recalibrar.py` el %s. Tabla `%s…`. %s clientes de validación. "
             "El bloque de prueba no se usó.\n" % (
                 r["generado"][:10], r["tabla_sha256"][:12], "{:,}".format(r["validacion_clientes"]).replace(",", ".")))
    l.append("**Cómo se midió.** La logística se entrenó con 2023 (C = %s, el de la escalera). Cada método "
             "de recalibración se evaluó con validación cruzada de %d pliegues dentro de validación: cada "
             "cliente recibe una probabilidad recalibrada con un ajuste que no lo vio. Intervalos: bootstrap "
             "pareado del 95%% (%d remuestreos).\n" % (num(r["C"], 1), r["pliegues"], r["repeticiones_bootstrap"]))
    l.append("**Criterio, fijado antes de ver los resultados:** %s.\n" % r["criterio"])
    l.append("## Los cuatro métodos, fuera de pliegue\n")
    l.append("| Método | Log-loss | Brier | ECE | Prob. media | Pendiente | Intercepto | PR-AUC | ROC-AUC | Lift 20% |")
    l.append("|---|---|---|---|---|---|---|---|---|---|")
    for m in cal.ORDEN:
        e, b = ev[m], boot["modelos"][m]
        l.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            NOMBRES[m], intervalo(b["log_loss"], 4), intervalo(b["brier"], 4), intervalo(b["ece"], 4),
            pct(e["p_media"]), num(e["pendiente"], 2), num(e["intercepto"], 2), num(e["pr_auc"]),
            num(e["roc_auc"]), num(e["lift_20"], 2)))
    l.append("\nTasa de vuelta observada: %s. ECE: distancia promedio entre probabilidad y tasa observada "
             "en cada decil. Pendiente e intercepto: regresión logística de la vuelta sobre logit(p); "
             "calibración perfecta es pendiente 1 e intercepto 0.\n" % pct(ev["identidad"]["tasa_observada"]))
    l.append("## Diferencias\n")
    l.append("Negativo = el primero es mejor. *Sí* = el intervalo no incluye el cero.\n")
    l.append("| Comparación | Log-loss | Brier | ECE |")
    l.append("|---|---|---|---|")
    for a, b in pares:
        dif = boot["diferencias"]["%s - %s" % (a, b)]
        celdas = []
        for k in ("log_loss", "brier", "ece"):
            v = dif[k]
            marca = "sí" if (v["hasta"] < 0 or v["desde"] > 0) else "no"
            celdas.append("%s · %s" % (intervalo(v, 4), marca))
        l.append("| %s − %s | %s |" % (NOMBRES[a], NOMBRES[b], " | ".join(celdas)))
    c = r["calibrador"]
    signo = "−" if c.get("b", 0) < 0 else "+"
    detalle = {"intercepto": "sigmoide(logit(p) %s %s)" % (signo, num(abs(c.get("b", 0)), 4)),
               "platt": "sigmoide(%s · logit(p) %s %s)" % (num(c.get("a", 0), 4), signo,
                                                           num(abs(c.get("b", 0)), 4)),
               "isotonica": "función escalonada de %d tramos" % len(c.get("x", [])),
               "identidad": "sin cambios"}[r["elegido"]]
    l.append("\n## Elegido: %s\n" % NOMBRES[r["elegido"]])
    l.append("Menor log-loss: %s. Ajustado con toda la validación: %s. Los parámetros están en "
             "`calibracion_validacion.json` y se aplican a la prueba sin volver a ajustar.\n" % (
                 NOMBRES[r["mejor_por_log_loss"]], detalle))
    l.append("## Por decil\n")
    l.append("![Calibración por decil](calibracion_validacion.png)\n")
    l.append("| Grupo | Sin recalibrar: prob. media | Vuelven | Recalibrada: prob. media | Vuelven |")
    l.append("|---|---|---|---|---|")
    for i, (a, b) in enumerate(zip(r["deciles"]["sin_recalibrar"], r["deciles"]["recalibrada"]), 1):
        l.append("| %d | %s | %s | %s | %s |" % (i, pct(a["p_media"]), pct(a["observada"]),
                                                 pct(b["p_media"]), pct(b["observada"])))
    l.append("\n**Límite.** El calibrador se ajustó con 2024 y supone que 2025 se le parece. Si la carga "
             "de datos de contacto siguió cambiando, la prueba lo va a mostrar.\n")
    return "\n".join(l)


if __name__ == "__main__":
    main()
