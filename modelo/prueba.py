"""La prueba: evaluacion UNICA en el bloque de prueba (enero a agosto de 2025).

    python modelo/prueba.py

Sigue `docs/plan_de_la_prueba.md`, que se versiono antes de abrir este
bloque. No corre si el plan o este script tienen cambios sin versionar, ni si
la prueba ya se corrio. No elige ni ajusta nada con la prueba: todos los
modelos se entrenan con 2023 (salvo el secundario 2023 + 2024) y los
calibradores vienen de validacion.

Escribe `modelo/resultados/prueba.*`.
"""
import datetime
import json
import os
import subprocess
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import calibracion as cal  # noqa: E402
from modelo import campania, datos, metricas, modelos  # noqa: E402
from modelo.escalera import REGLAS, huella_tabla, intervalo, num, pct  # noqa: E402

SEMILLA = 2026
REPETICIONES = 2000
SALIDA = os.path.join(REPO, "modelo", "resultados")
PLAN = "docs/plan_de_la_prueba.md"
ESTE = "modelo/prueba.py"
METRICAS_BOOT = {"pr_auc": metricas.pr_auc, "roc_auc": metricas.roc_auc,
                 "lift_20": lambda y, p: metricas.lift_en(y, p, 0.20), "brier": metricas.brier,
                 "log_loss": metricas.log_loss}
NOMBRES = {
    "prevalencia": "Prevalencia",
    "regla_10mil": "Regla: primer viaje de 10 mil o más",
    "regla_acompaniante": "Regla: viajó antes como acompañante",
    "principal": "**Logística principal (recalibrada)**",
    "principal_sin_recalibrar": "Logística principal sin recalibrar",
    "reducido": "Logística reducida (recalibrada)",
    "catboost": "CatBoost día 0",
    "ficha_unica": "Logística ficha única",
    "sin_contacto": "Logística sin datos de contacto",
    "logistica_2023_2024": "Logística entrenada con 2023 + 2024",
}
PARES = [
    ("principal", "prevalencia"),
    ("principal", "regla_acompaniante"),
    ("regla_acompaniante", "prevalencia"),
    ("regla_10mil", "prevalencia"),
    ("reducido", "principal"),
    ("catboost", "principal"),
    ("ficha_unica", "principal"),
    ("principal", "sin_contacto"),
    ("logistica_2023_2024", "principal"),
    ("principal", "principal_sin_recalibrar"),
]
CONFIRMATORIAS = ["principal - prevalencia", "principal - regla_acompaniante"]


# ------------------------------------------------------------------ controles
def _git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True).stdout.strip()


def verificar_versionado(ruta, estado, ultimo_commit):
    """`estado`: salida de git status --porcelain para el archivo; vacia si no
    tiene cambios. `ultimo_commit`: hash y fecha; vacio si nunca se versiono."""
    if estado or not ultimo_commit:
        raise SystemExit("%s tiene que estar versionado y sin cambios antes de abrir la prueba" % ruta)
    return ultimo_commit


def verificar_no_corrida(ruta):
    if os.path.exists(ruta):
        raise SystemExit("la prueba ya se corrio (%s): se corre una sola vez" % ruta)


def veredicto_h1(diferencias):
    comparaciones = []
    for par in CONFIRMATORIAS:
        for m in ("pr_auc", "roc_auc"):
            v = diferencias[par][m]
            comparaciones.append({"par": par, "metrica": m, "intervalo": v, "gana": v["desde"] > 0})
    return {"confirmada": all(c["gana"] for c in comparaciones), "comparaciones": comparaciones}


# --------------------------------------------------------------------- prueba
def main():
    ruta_json = os.path.join(SALIDA, "prueba.json")
    verificar_no_corrida(ruta_json)
    plan = verificar_versionado(PLAN, _git("status", "--porcelain", "--", PLAN),
                                _git("log", "-1", "--format=%H %cI", "--", PLAN))
    script = verificar_versionado(ESTE, _git("status", "--porcelain", "--", ESTE),
                                  _git("log", "-1", "--format=%H %cI", "--", ESTE))
    huella = huella_tabla()
    leer = lambda n: json.load(open(os.path.join(SALIDA, n), encoding="utf-8"))  # noqa: E731
    esc, calj, red = leer("escalera_validacion.json"), leer("calibracion_validacion.json"), leer("reducido_validacion.json")
    for nombre, j in (("escalera", esc), ("calibracion", calj), ("reducido", red)):
        if j["tabla_sha256"] != huella:
            raise SystemExit("%s se corrio con otra tabla" % nombre)

    d = datos.cargar(bloques=("entrenamiento", "validacion", "prueba"), permitir_prueba=True)
    ent = d[d["bloque"] == "entrenamiento"].reset_index(drop=True)
    val = d[d["bloque"] == "validacion"].reset_index(drop=True)
    pru = d[d["bloque"] == "prueba"].reset_index(drop=True)
    y_e, y_v, y_p = (x[datos.ETIQUETA].to_numpy() for x in (ent, val, pru))
    print("prueba: %d clientes · vuelve %s" % (len(pru), pct(y_p.mean())), flush=True)

    def logistica(cols, C, x_ajuste, y_ajuste):
        cats, nums = datos.tipos(cols)
        return modelos._logistica(cats, nums, C).fit(x_ajuste[cols], y_ajuste).predict_proba(pru[cols])[:, 1]

    h = esc["hiperparametros"]
    dia0 = datos.BRAZOS["dia0"]
    pred = {"prevalencia": modelos.prevalencia(y_e, len(pru))}
    for clave, (_, grupo) in REGLAS.items():
        pred[clave] = modelos.regla(grupo(ent), y_e, grupo(pru))
    crudo = logistica(dia0, h["logistica"]["dia0"]["C"], ent, y_e)
    pred["principal"] = cal.desde_parametros(calj["calibrador"]).predict(crudo)
    pred["principal_sin_recalibrar"] = crudo
    pred["reducido"] = cal.desde_parametros(red["calibracion"]["calibrador"]).predict(
        logistica(red["columnas"], red["C"], ent, y_e))
    pred["ficha_unica"] = logistica(datos.BRAZOS["ficha_unica"], h["logistica"]["ficha_unica"]["C"], ent, y_e)
    pred["sin_contacto"] = logistica(datos.BRAZOS["sin_contacto"], h["logistica"]["sin_contacto"]["C"], ent, y_e)
    ev = d[d["bloque"].isin(["entrenamiento", "validacion"])]
    pred["logistica_2023_2024"] = logistica(dia0, h["logistica"]["dia0"]["C"], ev, ev[datos.ETIQUETA].to_numpy())

    from catboost import CatBoostClassifier
    cb = h["catboost"]["dia0"]
    cats, _ = datos.tipos(dia0)
    envoltura = modelos._CatBoost(None, cats)
    modelo_cb = CatBoostClassifier(iterations=cb["iteraciones"], depth=cb["params"]["depth"],
                                   l2_leaf_reg=cb["params"]["l2_leaf_reg"],
                                   learning_rate=cb["params"]["learning_rate"], loss_function="Logloss",
                                   random_seed=SEMILLA, allow_writing_files=False, logging_level="Silent")
    modelo_cb.fit(envoltura._preparar(ent[dia0]), y_e, cat_features=cats)
    pred["catboost"] = modelos._CatBoost(modelo_cb, cats).predict_proba(pru[dia0])[:, 1]
    print("modelos listos", flush=True)

    evaluacion = {}
    for m, p in pred.items():
        e = metricas.evaluar(y_p, p)
        e["log_loss"] = metricas.log_loss(y_p, p)
        e["ece"] = metricas.ece(y_p, p)
        if len(np.unique(p)) > 2:
            e["pendiente"], e["intercepto"] = metricas.pendiente_e_intercepto(y_p, p)
        evaluacion[m] = e
    boot = metricas.bootstrap(y_p, pred, METRICAS_BOOT, PARES, REPETICIONES, SEMILLA)
    print("bootstrap listo", flush=True)
    h1 = veredicto_h1(boot["diferencias"])

    u0 = np.clip(pru["utilidad_indice"].to_numpy(dtype=float), 0, None)
    p = pred["principal"]
    resultado = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "plan_commit": plan, "script_commit": script, "tabla_sha256": huella,
        "clientes_prueba": int(len(pru)), "tasa_prueba": float(y_p.mean()),
        "semilla": SEMILLA, "repeticiones_bootstrap": REPETICIONES,
        "h1": h1, "evaluacion": evaluacion, "bootstrap": boot,
        "deciles": {m: metricas.calibracion(y_p, pred[m]) for m in ("principal", "principal_sin_recalibrar", "reducido")},
        "campania": {"por_probabilidad": campania.simular(y_p, p, 0.2, valor=u0),
                     "por_probabilidad_x_utilidad": campania.simular(y_p, p * u0, 0.2, valor=u0),
                     "curva": campania.curva(y_p, p)},
    }
    with open(ruta_json, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)
    grafico_captura(resultado, os.path.join(SALIDA, "prueba_captura.png"))
    with open(os.path.join(SALIDA, "prueba.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(informe(resultado))
    print("H1 %s · resultados en modelo/resultados/prueba.md" % ("CONFIRMADA" if h1["confirmada"] else "NO confirmada"))


# ---------------------------------------------------------------------- salida
def grafico_captura(r, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    sup, tinta, tinta2, grilla, eje, azul, gris = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=160)
    fig.patch.set_facecolor(sup)
    ax.set_facecolor(sup)
    xs = [0.0] + [c["frac"] for c in r["campania"]["curva"]]
    ys = [0.0] + [c["captura"] for c in r["campania"]["curva"]]
    ax.plot([0, 1], [0, 1], color=gris, linewidth=2, zorder=2, label="Contactar al azar")
    ax.plot(xs, ys, color=azul, linewidth=2, zorder=3, label="Contactar según el modelo")
    c20 = r["campania"]["por_probabilidad"]
    ax.scatter([0.2], [c20["captura"]], s=64, color=azul, edgecolors=sup, linewidths=2, zorder=4)
    ax.annotate("Contactando al 20%%: %s de las vueltas\n(al azar: 20%%)" % pct(c20["captura"]),
                (0.2, c20["captura"]), xytext=(0.27, c20["captura"] - 0.05), color=tinta, fontsize=9)
    for f in (ax.xaxis, ax.yaxis):
        f.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, color=grilla, linewidth=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("bottom", "left"):
        ax.spines[lado].set_color(eje)
    ax.tick_params(colors=tinta2, length=0, pad=6)
    ax.set_xlabel("Clientes contactados (de mayor a menor probabilidad)", color=tinta2, labelpad=8)
    ax.set_ylabel("Parte de las vueltas que quedan contactadas", color=tinta2, labelpad=8)
    ax.set_title("Simulación de campaña en la prueba (enero a agosto de 2025)", color=tinta, loc="left",
                 fontsize=12, fontweight="bold", pad=14)
    ax.legend(loc="lower right", frameon=False, labelcolor=tinta2)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=sup)
    plt.close(fig)


def informe(r):
    ev, b = r["evaluacion"], r["bootstrap"]
    miles = lambda n: "{:,}".format(int(round(n))).replace(",", ".")  # noqa: E731
    l = ["# Prueba · enero a agosto de 2025\n"]
    l.append("Generado por `modelo/prueba.py` el %s, siguiendo [`docs/plan_de_la_prueba.md`](../../docs/plan_de_la_prueba.md) "
             "(commit `%s`, %s). Tabla `%s…`. %s clientes; vuelve el %s. Intervalos bootstrap pareados del 95%% "
             "(%d remuestreos). Esta evaluación se corre una sola vez.\n" % (
                 r["generado"][:10], r["plan_commit"].split()[0][:7], r["plan_commit"].split()[1][:10],
                 r["tabla_sha256"][:12], miles(r["clientes_prueba"]), pct(r["tasa_prueba"]), r["repeticiones_bootstrap"]))
    h1 = r["h1"]
    l.append("## Hipótesis 1: %s\n" % ("confirmada" if h1["confirmada"] else "no confirmada"))
    l.append("Criterio del plan: la logística principal le gana a la prevalencia y a la regla «viajó antes como "
             "acompañante» en PR-AUC y ROC-AUC, con el intervalo entero por encima de cero.\n")
    l.append("| Comparación | Métrica | Diferencia | ¿Gana? |")
    l.append("|---|---|---|---|")
    for c in h1["comparaciones"]:
        a, z = c["par"].split(" - ")
        l.append("| %s − %s | %s | %s | %s |" % (NOMBRES[a].strip("*"), NOMBRES[z].strip("*"),
                                                "PR-AUC" if c["metrica"] == "pr_auc" else "ROC-AUC",
                                                intervalo(c["intervalo"]), "sí" if c["gana"] else "no"))
    l.append("\n## Todos los modelos en la prueba\n")
    l.append("| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% | Captura 20% | Brier | Prob. media |")
    l.append("|---|---|---|---|---|---|---|---|")
    for m in NOMBRES:
        e, x = ev[m], b["modelos"][m]
        l.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            NOMBRES[m], intervalo(x["pr_auc"]), intervalo(x["roc_auc"]), num(e["lift_10"], 2),
            intervalo(x["lift_20"], 2), pct(e["captura_20"]), intervalo(x["brier"], 4), pct(e["p_media"])))
    l.append("\n## Comparaciones declaradas\n")
    l.append("Diferencia «primero − segundo». En Brier y log-loss, negativo = el primero es mejor. *Sí* = el "
             "intervalo no incluye el cero.\n")
    l.append("| Comparación | PR-AUC | ROC-AUC | Lift 20% | Brier | Log-loss |")
    l.append("|---|---|---|---|---|---|")
    for a, z in PARES:
        dif = b["diferencias"]["%s - %s" % (a, z)]
        celdas = []
        for k in ("pr_auc", "roc_auc", "lift_20", "brier", "log_loss"):
            v = dif[k]
            celdas.append("%s%s" % (intervalo(v, 4 if k in ("brier", "log_loss") else 3),
                                    " · sí" if (v["desde"] > 0 or v["hasta"] < 0) else ""))
        l.append("| %s − %s | %s |" % (NOMBRES[a].strip("*"), NOMBRES[z].strip("*"), " | ".join(celdas)))
    l.append("\n## Calibración en la prueba\n")
    l.append("| Modelo | Prob. media | Vuelve | ECE | Pendiente |")
    l.append("|---|---|---|---|---|")
    for m in ("principal", "principal_sin_recalibrar", "reducido"):
        e = ev[m]
        l.append("| %s | %s | %s | %s | %s |" % (NOMBRES[m].strip("*"), pct(e["p_media"]), pct(e["tasa_observada"]),
                                               num(e["ece"], 4), num(e.get("pendiente", float("nan")), 2)))
    l.append("\n| Decil | Principal: prob. media | Vuelven | Reducida: prob. media | Vuelven |")
    l.append("|---|---|---|---|---|")
    for i, (a, z) in enumerate(zip(r["deciles"]["principal"], r["deciles"]["reducido"]), 1):
        l.append("| %d | %s | %s | %s | %s |" % (i, pct(a["p_media"]), pct(a["observada"]), pct(z["p_media"]), pct(z["observada"])))
    c = r["campania"]
    cp, cu = c["por_probabilidad"], c["por_probabilidad_x_utilidad"]
    l.append("\n## Simulación de campaña\n")
    l.append("Contactar al 20%% de clientes con mayor probabilidad (%s de %s): entre ellos están %s de los %s "
             "que vuelven (%s), contra %s si se contacta a la misma cantidad al azar. Vuelve el %s de los "
             "contactados, %s veces el promedio.\n" % (
                 miles(cp["contactados"]), miles(r["clientes_prueba"]), miles(cp["vuelven_contactados"]),
                 miles(cp["vuelven_total"]), pct(cp["captura"]), miles(cp["vuelven_contactados_azar"]),
                 pct(cp["tasa_contactados"]), num(cp["lift"], 2)))
    l.append("Ordenando por probabilidad × utilidad de la primera compra: quedan contactados %s de los que "
             "vuelven (%s) y el %s de la utilidad de primera compra de quienes vuelven (ordenando solo por "
             "probabilidad: %s; al azar: 20%%).\n" % (
                 miles(cu["vuelven_contactados"]), pct(cu["captura"]), pct(cu["valor_capturado"]),
                 pct(cp["valor_capturado"])))
    l.append("![Curva de captura](prueba_captura.png)\n")
    l.append("**Límites.** Mide propensión, no efecto: cuenta a quienes iban a volver y quedaron contactados. La "
             "tabla no trae la utilidad del viaje de vuelta; el valor se mide por la primera compra.\n")
    return "\n".join(l)


if __name__ == "__main__":
    main()
