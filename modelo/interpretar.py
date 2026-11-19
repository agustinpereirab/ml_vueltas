"""Interpretacion de la logistica (brazo dia 0) para la hipotesis 2, en VALIDACION.

    python modelo/interpretar.py

H2: pesan mas el destino regional, viajar con un cliente previo o haber sido
acompaniante, y el vendedor. Se mide de tres maneras:

1. Sin cada grupo: la logistica se vuelve a ajustar en entrenamiento sin las
   variables del grupo y se compara con el modelo completo en validacion,
   con intervalo bootstrap pareado. Mide lo que el grupo aporta y ningun otro
   grupo reemplaza.
2. Cada grupo solo: cuanto ordena el grupo por su cuenta.
3. SHAP: la contribucion de cada variable al logit de cada cliente de
   validacion; de ahi, el efecto por pais, por compania y la dispersion
   entre vendedores (sin listar ni ordenar vendedores).

Se usa el C de la escalera para todas las variantes. El bloque de prueba no
se carga. Escribe `modelo/resultados/interpretacion_validacion.*`.
"""
import datetime
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos, metricas, modelos  # noqa: E402
from modelo import interpretacion as it  # noqa: E402
from modelo.escalera import huella_tabla, intervalo, num, pct  # noqa: E402

SEMILLA = 2026
REPETICIONES = 2000
SALIDA = os.path.join(REPO, "modelo", "resultados")
METRICAS_BOOT = {"pr_auc": metricas.pr_auc, "roc_auc": metricas.roc_auc, "log_loss": metricas.log_loss}
PAISES = {"BR": "Brasil", "AR": "Argentina", "ES": "España", "US": "Estados Unidos", "MX": "México",
          "CL": "Chile", "DO": "Rep. Dominicana", "UY": "Uruguay", "IT": "Italia", "CO": "Colombia",
          "GE": "Alemania", "PE": "Perú", "GB": "Reino Unido", "PY": "Paraguay", "otro": "otro país",
          "sin_dato": "sin dato"}
COMPANIA = {"fue_acompaniante_antes": "Viajó antes como acompañante",
            "viajes_previos_acompaniante": "Viajes previos como acompañante",
            "viaja_con_cliente_previo": "Viaja con un cliente previo",
            "viaja_con_alguien_con_historial": "Viaja con alguien con historial"}


def ajustar(C, cols, x_e, y_e, x_v):
    cats = [c for c in cols if c not in datos.NUMERICAS]
    nums = [c for c in cols if c in datos.NUMERICAS]
    m = modelos._logistica(cats, nums, C).fit(x_e[cols], y_e)
    return m, m.predict_proba(x_v[cols])[:, 1]


def main():
    huella = huella_tabla()
    with open(os.path.join(SALIDA, "escalera_validacion.json"), encoding="utf-8") as fh:
        escalera = json.load(fh)
    if escalera["tabla_sha256"] != huella:
        raise SystemExit("la escalera se corrio con otra tabla: correr modelo/escalera.py")
    C = escalera["hiperparametros"]["logistica"]["dia0"]["C"]

    d = datos.cargar()
    x_e, y_e, x_v, y_v = datos.separar(d, "dia0")
    brazo = datos.BRAZOS["dia0"]
    completo, p_completo = ajustar(C, brazo, x_e, y_e, x_v)
    if abs(metricas.pr_auc(y_v, p_completo) - escalera["validacion"]["logistica_dia0"]["pr_auc"]) > 1e-9:
        raise SystemExit("la logistica no reproduce la escalera")

    pred = {"completo": p_completo}
    for g, vs in it.GRUPOS.items():
        pred["sin · " + g] = ajustar(C, [c for c in brazo if c not in vs], x_e, y_e, x_v)[1]
        pred["solo · " + g] = ajustar(C, vs, x_e, y_e, x_v)[1]
    pred["sin código de vendedor"] = ajustar(C, [c for c in brazo if c != "vendedor"], x_e, y_e, x_v)[1]
    xr_e, xr_v = it.con_regional(x_e), it.con_regional(x_v)
    pred["destino como regional sí/no"] = ajustar(C, list(xr_e.columns), xr_e, y_e, xr_v)[1]
    print("%d variantes ajustadas" % len(pred), flush=True)

    pares = [("completo", "sin · " + g) for g in it.GRUPOS]
    pares += [("completo", "sin código de vendedor"),
              ("completo", "destino como regional sí/no"),
              ("destino como regional sí/no", "sin · H2 · destino")]
    boot = metricas.bootstrap(y_v, pred, METRICAS_BOOT, pares, REPETICIONES, SEMILLA)
    print("bootstrap listo", flush=True)

    base, s = it.shap_lineal(completo, x_e, x_v)
    sg = it.por_grupo(s, it.GRUPOS)
    shap_variables = {v: float(s[v].abs().mean()) for v in s.columns}
    shap_grupos = {g: float(sg[g].abs().mean()) for g in sg.columns}

    destino = sg["H2 · destino"]
    por_pais = []
    for p, idx in x_v.groupby("pais_destino").groups.items():
        por_pais.append({"pais": p, "n": int(len(idx)), "shap_medio": float(destino.loc[idx].mean()),
                         "vuelven": float(y_v[x_v.index.get_indexer(idx)].mean()),
                         "regional": p in it.REGIONALES})
    por_pais.sort(key=lambda r: -r["shap_medio"])
    es_regional = x_v["pais_destino"].isin(it.REGIONALES).to_numpy()
    con_pais = ~x_v["pais_destino"].isin(["otro", "sin_dato"]).to_numpy()
    regional = {"regional": {"n": int(es_regional.sum()), "shap_medio": float(destino[es_regional].mean()),
                             "vuelven": float(y_v[es_regional].mean())},
                "no_regional_con_pais": {"n": int((~es_regional & con_pais).sum()),
                                         "shap_medio": float(destino[~es_regional & con_pais].mean()),
                                         "vuelven": float(y_v[~es_regional & con_pais].mean())}}

    compania = {}
    for v in COMPANIA:
        ors = it.odds_ratios(completo, v, "0")
        filas = []
        for c, idx in x_v.groupby(v).groups.items():
            pos = x_v.index.get_indexer(idx)
            filas.append({"valor": c, "n": int(len(idx)), "vuelven": float(y_v[pos].mean()),
                          "shap_medio": float(s[v].loc[idx].mean()), "odds_ratio_vs_0": ors.get(str(c))})
        compania[v] = sorted(filas, key=lambda r: r["valor"])

    cod = s["vendedor"].to_numpy()
    vendedor = {"codigos_en_validacion": int(x_v["vendedor"].nunique()),
                "clientes_en_V_otros": int((x_v["vendedor"] == "V-otros").sum()),
                "percentiles_shap_codigo": {str(q): float(np.percentile(cod, q)) for q in (10, 25, 50, 75, 90)},
                "shap_medio_abs_codigo": float(np.abs(cod).mean())}

    resultado = {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"), "tabla_sha256": huella,
        "C": C, "validacion_clientes": int(len(y_v)), "semilla": SEMILLA,
        "repeticiones_bootstrap": REPETICIONES, "grupos": it.GRUPOS,
        "metricas": {m: {k: f(y_v, p) for k, f in METRICAS_BOOT.items()} for m, p in pred.items()},
        "bootstrap": boot, "shap_base": base, "shap_medio_abs_variable": shap_variables,
        "shap_medio_abs_grupo": shap_grupos, "destino_por_pais": por_pais, "destino_regional": regional,
        "compania": compania, "vendedor": vendedor,
    }
    with open(os.path.join(SALIDA, "interpretacion_validacion.json"), "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)
    grafico_grupos(resultado, os.path.join(SALIDA, "interpretacion_grupos.png"))
    grafico_destino(resultado, os.path.join(SALIDA, "interpretacion_destino.png"))
    with open(os.path.join(SALIDA, "interpretacion_validacion.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(informe(resultado))
    print("listo -> modelo/resultados/interpretacion_validacion.md")


# ------------------------------------------------------------------ graficos
SUP, TINTA, TINTA2, GRILLA, EJE, AZUL, GRIS = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#2a78d6", "#898781"


def _ejes(fig, ax):
    import matplotlib.pyplot as plt  # noqa: F401
    fig.patch.set_facecolor(SUP)
    ax.set_facecolor(SUP)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(EJE)
    ax.tick_params(colors=TINTA2, length=0, pad=6)
    ax.grid(True, axis="x", color=GRILLA, linewidth=1)
    ax.set_axisbelow(True)


def grafico_grupos(r, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    filas = sorted(((g, r["bootstrap"]["diferencias"]["completo - sin · " + g]["pr_auc"]) for g in it.GRUPOS),
                   key=lambda t: t[1]["punto"])
    fig, ax = plt.subplots(figsize=(7.6, 4.4), dpi=160)
    _ejes(fig, ax)
    for i, (g, v) in enumerate(filas):
        color = AZUL if g.startswith("H2") else GRIS
        ax.barh(i, v["punto"], height=0.5, color=color, zorder=3)
        ax.plot([v["desde"], v["hasta"]], [i, i], color=TINTA2, linewidth=1.2, zorder=4)
        ax.text(max(v["hasta"], 0) + 0.0012, i, num(v["punto"]), va="center", color=TINTA, fontsize=9)
    ax.axvline(0, color=EJE, linewidth=1, zorder=2)
    ax.set_yticks(range(len(filas)), [g for g, _ in filas], color=TINTA2)
    ax.set_xlabel("PR-AUC que pierde el modelo sin el grupo (línea: intervalo del 95%)", color=TINTA2, labelpad=8)
    ax.set_title("Cuánto aporta cada grupo de variables · validación 2024", color=TINTA, loc="left",
                 fontsize=12, fontweight="bold", pad=14)
    ax.legend(handles=[Patch(color=AZUL, label="grupos de la hipótesis 2"), Patch(color=GRIS, label="otros grupos")],
              loc="lower right", frameon=False, labelcolor=TINTA2)
    ax.set_xlim(min(-0.004, min(v["desde"] for _, v in filas) - 0.002), max(v["hasta"] for _, v in filas) + 0.012)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=SUP)
    plt.close(fig)


def grafico_destino(r, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10})
    filas = [f for f in r["destino_por_pais"] if f["n"] >= 50][::-1]
    fig, ax = plt.subplots(figsize=(7.6, 5.6), dpi=160)
    _ejes(fig, ax)
    ax.axvline(1, color=EJE, linewidth=1, zorder=2)
    for i, f in enumerate(filas):
        mult = float(np.exp(f["shap_medio"]))
        color = AZUL if f["regional"] else GRIS
        ax.plot([1, mult], [i, i], color=color, linewidth=2, zorder=3, solid_capstyle="round")
        ax.scatter([mult], [i], s=64, color=color, edgecolors=SUP, linewidths=2, zorder=4)
        ax.text(mult + (0.012 if mult >= 1 else -0.012), i, "×" + num(mult, 2), va="center",
                ha="left" if mult >= 1 else "right", color=TINTA, fontsize=9)
    ax.set_yticks(range(len(filas)), ["%s (%s)" % (PAISES.get(f["pais"], f["pais"]), "{:,}".format(f["n"]).replace(",", "."))
                                      for f in filas], color=TINTA2)
    lo = min(np.exp(f["shap_medio"]) for f in filas)
    hi = max(np.exp(f["shap_medio"]) for f in filas)
    ax.set_xlim(lo - 0.08, hi + 0.1)
    ax.set_xlabel("Cuánto multiplica el destino las chances de volver, respecto del cliente promedio",
                  color=TINTA2, labelpad=8)
    ax.set_title("Efecto del destino en el modelo, por país · validación 2024", color=TINTA, loc="left",
                 fontsize=12, fontweight="bold", pad=14)
    ax.legend(handles=[Line2D([], [], marker="o", color=AZUL, label="regional (AR, BR, CL, PY)", markersize=7),
                       Line2D([], [], marker="o", color=GRIS, label="resto", markersize=7)],
              loc="lower right", frameon=False, labelcolor=TINTA2)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=SUP)
    plt.close(fig)


# ------------------------------------------------------------------- informe
def informe(r):
    b = r["bootstrap"]
    l = ["# Hipótesis 2 · interpretación de la logística día 0 · validación (cohorte 2024)\n"]
    l.append("Generado por `modelo/interpretar.py` el %s. Tabla `%s…`. %s clientes de validación. El bloque "
             "de prueba no se usó. Todas las variantes son la misma logística (C = %s) entrenada con 2023; "
             "intervalos bootstrap pareados del 95%% (%d remuestreos). SHAP se lee como asociación, no como "
             "causa.\n" % (r["generado"][:10], r["tabla_sha256"][:12],
                           "{:,}".format(r["validacion_clientes"]).replace(",", "."), num(r["C"], 1),
                           r["repeticiones_bootstrap"]))
    l.append("## 1. Cuánto aporta cada grupo\n")
    l.append("«Sin el grupo»: cuánto empeora el modelo si se lo vuelve a entrenar sin esas variables (lo que el "
             "grupo aporta y ningún otro grupo reemplaza). «Solo el grupo»: cuánto ordena por su cuenta. "
             "SHAP: contribución media, en valor absoluto, al logit de cada cliente.\n")
    l.append("| Grupo | Variables | Pierde sin él: PR-AUC | ROC-AUC | Log-loss | Solo el grupo: PR-AUC | ROC-AUC | SHAP medio |")
    l.append("|---|---|---|---|---|---|---|---|")
    orden = sorted(it.GRUPOS, key=lambda g: -b["diferencias"]["completo - sin · " + g]["pr_auc"]["punto"])
    for g in orden:
        dif = b["diferencias"]["completo - sin · " + g]
        solo = b["modelos"]["solo · " + g]
        l.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            g, len(it.GRUPOS[g]), intervalo(dif["pr_auc"]), intervalo(dif["roc_auc"]),
            intervalo({k: -v for k, v in dif["log_loss"].items()} | {"desde": -dif["log_loss"]["hasta"],
                                                                     "hasta": -dif["log_loss"]["desde"]}, 4),
            intervalo(solo["pr_auc"]), intervalo(solo["roc_auc"]), num(r["shap_medio_abs_grupo"][g])))
    c = b["modelos"]["completo"]
    l.append("\nModelo completo: PR-AUC %s, ROC-AUC %s. Prevalencia en validación: PR-AUC de referencia 0,204. "
             "En log-loss, la columna muestra cuánto *sube* sin el grupo (positivo = el grupo ayuda).\n" % (
                 intervalo(c["pr_auc"]), intervalo(c["roc_auc"])))
    l.append("![Aporte de cada grupo](interpretacion_grupos.png)\n")

    l.append("## 2. Compañía previa\n")
    l.append("Odds ratio: cuánto multiplica las chances de volver tener ese valor contra «0», con el resto de las "
             "variables fijas (coeficientes de la logística). SHAP medio: contribución media de la variable "
             "para los clientes con ese valor, en la escala logit.\n")
    l.append("| Variable | Valor | Clientes | Vuelven | Odds ratio vs 0 | SHAP medio |")
    l.append("|---|---|---|---|---|---|")
    for v, filas in r["compania"].items():
        for f in filas:
            l.append("| %s | %s | %s | %s | %s | %s |" % (
                COMPANIA[v], f["valor"], "{:,}".format(f["n"]).replace(",", "."), pct(f["vuelven"]),
                "—" if f["odds_ratio_vs_0"] is None else "×" + num(f["odds_ratio_vs_0"], 2), num(f["shap_medio"])))
    l.append("")

    l.append("## 3. Destino\n")
    rg = r["destino_regional"]
    l.append("Efecto del destino (país y región juntos) por país, como multiplicador de las chances respecto del "
             "cliente promedio: exp(SHAP medio). Solo países con 50 clientes o más en validación.\n")
    l.append("| País | Regional | Clientes | Vuelven | Multiplicador |")
    l.append("|---|---|---|---|---|")
    for f in r["destino_por_pais"]:
        l.append("| %s | %s | %s | %s | ×%s |" % (PAISES.get(f["pais"], f["pais"]), "sí" if f["regional"] else "",
                                                 "{:,}".format(f["n"]).replace(",", "."), pct(f["vuelven"]),
                                                 num(float(np.exp(f["shap_medio"])), 2)))
    l.append("\nRegional (AR, BR, CL, PY): %s clientes, vuelven %s, multiplicador medio ×%s. Resto con país "
             "conocido: %s clientes, vuelven %s, ×%s.\n" % (
                 "{:,}".format(rg["regional"]["n"]).replace(",", "."), pct(rg["regional"]["vuelven"]),
                 num(float(np.exp(rg["regional"]["shap_medio"])), 2),
                 "{:,}".format(rg["no_regional_con_pais"]["n"]).replace(",", "."),
                 pct(rg["no_regional_con_pais"]["vuelven"]), num(float(np.exp(rg["no_regional_con_pais"]["shap_medio"])), 2)))
    l.append("| Comparación | PR-AUC | ROC-AUC |")
    l.append("|---|---|---|")
    for a, z in (("completo", "destino como regional sí/no"), ("destino como regional sí/no", "sin · H2 · destino")):
        dif = b["diferencias"]["%s - %s" % (a, z)]
        l.append("| %s − %s | %s | %s |" % (a, z, intervalo(dif["pr_auc"]), intervalo(dif["roc_auc"])))
    l.append("\n«Destino como regional sí/no» reemplaza país y región por una sola marca regional, que es como "
             "está formulada H2. La segunda fila dice si esa marca aporta algo frente a no tener destino.\n")
    l.append("![Destino por país](interpretacion_destino.png)\n")

    l.append("## 4. Vendedor\n")
    vd = r["vendedor"]
    pc = vd["percentiles_shap_codigo"]
    dif = b["diferencias"]["completo - sin código de vendedor"]
    l.append("No se listan ni se ordenan vendedores. %d códigos en validación; %s clientes en `V-otros` "
             "(vendedores con menos de 50 clientes en la tabla).\n" % (
                 vd["codigos_en_validacion"], "{:,}".format(vd["clientes_en_V_otros"]).replace(",", ".")))
    l.append("- Sin el código de vendedor (con antigüedad y cartera): PR-AUC %s, ROC-AUC %s." % (
        intervalo(dif["pr_auc"]), intervalo(dif["roc_auc"])))
    l.append("- Cuánto multiplica el vendedor las chances de su cliente, respecto del promedio: percentil 10 "
             "×%s, mediana ×%s, percentil 90 ×%s (contribución del código, escala logit exponenciada).\n" % (
                 num(float(np.exp(pc["10"])), 2), num(float(np.exp(pc["50"])), 2), num(float(np.exp(pc["90"])), 2)))

    l.append("## 5. Las variables una por una\n")
    l.append("Contribución media, en valor absoluto, al logit (SHAP). Las 12 primeras.\n")
    l.append("| Variable | SHAP medio |")
    l.append("|---|---|")
    for v, x in sorted(r["shap_medio_abs_variable"].items(), key=lambda t: -t[1])[:12]:
        l.append("| %s | %s |" % (v, num(x)))
    l.append("")
    return "\n".join(l)


if __name__ == "__main__":
    main()
