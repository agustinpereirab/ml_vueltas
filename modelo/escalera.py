"""La escalera de modelos: cada escalon tiene que ganarle al anterior, con intervalo.

    .venv/Scripts/python -m modelo.escalera            # mide en validacion (cohorte 2024)
    .venv/Scripts/python -m modelo.escalera --prueba   # ademas en prueba: UNA vez, al final

Entrena los cuatro escalones con la cohorte 2023, elige hiperparametros
mirando la 2024 y mide. Prueba (enero a agosto de 2025) no se toca sin
`--prueba`: se abre una sola vez, cuando ya no queda nada por decidir. Los
modelos que se miden en prueba son los mismos que en validacion, entrenados
solo con 2023, que es lo que la agencia tendria en enero de 2025 (las
etiquetas de 2024 todavia no estarian cerradas).

Escribe en `resultados/`:
    escalera_<brazo>_<bloque>.json   todo: metricas, intervalos, grillas, calibracion
    escalera_<brazo>_<bloque>.md     lo mismo para leer
    modelos/escalera_<brazo>.joblib  los cuatro escalones ya entrenados
"""
import argparse
import datetime
import json
import math
import os
import sys
import time

import joblib
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos as D  # noqa: E402
from modelo import metricas as M  # noqa: E402
from modelo.escalones import CRITERIO, ESCALERA, SEMILLA  # noqa: E402

SALIDA = os.path.join(REPO, "resultados")
BLOQUE = {"entrenamiento": "entrenamiento · cohorte 2023",
          "validacion": "validación · cohorte 2024",
          "prueba": "prueba · enero a agosto de 2025"}
TABLA = [("pr_auc", "PR-AUC"), ("roc_auc", "ROC-AUC"), ("lift_10", "Lift 10 %"),
         ("lift_20", "Lift 20 %"), ("captura_20", "Captura 20 %"), ("brier", "Brier"),
         ("exactitud_05", "Exactitud (0,5)")]
COMPARA = [("pr_auc", "PR-AUC"), ("roc_auc", "ROC-AUC"), ("lift_20", "Lift 20 %"),
           ("brier", "Brier")]


def avisar(texto):
    print(texto, file=sys.stderr, flush=True)


# ------------------------------------------------------------------ medir
def medir(escalones, X, y, repeticiones):
    puntajes = {e.nombre: e.probabilidad(X) for e in escalones}
    nombres = [e.nombre for e in escalones]
    pares = list(zip(nombres[1:], nombres[:-1]))
    r = M.bootstrap(y, puntajes, pares=pares, repeticiones=repeticiones, semilla=SEMILLA)
    r["n"] = int(len(y))
    r["tasa"] = float(np.mean(y))
    r["calibracion"] = {}
    for m, p in puntajes.items():
        a, b = M.recta_calibracion(y, p)
        r["calibracion"][m] = {"ordenada": a, "pendiente": b, "p_media": float(np.mean(p)),
                               "tramos": M.calibracion(y, p)}
    return r


def gana(d, metrica):
    if metrica in M.MENOR_ES_MEJOR:
        return d["hasta"] < 0
    return d["desde"] > 0


def sin_nan(x):
    if isinstance(x, dict):
        return {k: sin_nan(v) for k, v in x.items()}
    if isinstance(x, list):
        return [sin_nan(v) for v in x]
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


# ---------------------------------------------------------------- escribir
def num(x, dec=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return ("%.*f" % (dec, x)).replace(".", ",").replace("-", "−")


def pct(x, dec=1):
    return num(100 * x, dec) + " %"


def miles(n):
    return "{:,}".format(int(n)).replace(",", ".")


def celda(d, metrica):
    if metrica in ("captura_20", "exactitud_05"):
        return "%s (%s–%s)" % (pct(d["valor"]), num(100 * d["desde"], 1), num(100 * d["hasta"], 1))
    dec = 2 if metrica.startswith("lift") else 3
    return "%s (%s–%s)" % (num(d["valor"], dec), num(d["desde"], dec), num(d["hasta"], dec))


def markdown(res, bloque):
    ent, med = res["entrenamiento"], res["medida"]
    esc = res["escalones"]
    L = ["# Escalera de modelos · %s" % BLOQUE[bloque], "",
         "%s · tabla `%s…` · brazo `%s` (%s)" % (
             res["fecha"][:10], res["huella"][:12], res["brazo"],
             "sin las columnas de ficha única" if res["brazo"] == "d0" else "ver modelo/datos.py"),
         "",
         "Entrenados con la cohorte 2023: %s clientes, vuelve el %s. Medidos sobre %s: "
         "%s clientes, vuelve el %s. Entre paréntesis, intervalo bootstrap del 95 %% "
         "(%s repeticiones, pareadas: en cada una, todos los modelos se miden sobre la misma "
         "muestra de clientes)." % (miles(ent["n"]), pct(ent["tasa"]), BLOQUE[bloque],
                                     miles(med["n"]), pct(med["tasa"]),
                                     miles(med["repeticiones"])),
         ""]
    if bloque == "validacion":
        L += ["Los hiperparámetros de la logística y del boosting se eligieron mirando este "
              "mismo bloque, así que sus números acá salen algo optimistas. La medida final es "
              "la de prueba.", ""]

    L += ["## Métricas", "",
          "| Escalón | " + " | ".join(t for _, t in TABLA) + " |",
          "|---" * (len(TABLA) + 1) + "|"]
    for i, e in enumerate(esc, 1):
        fila = med["modelos"][e["nombre"]]
        L.append("| %d. **%s** — %s | " % (i, e["nombre"], e["descripcion"])
                 + " | ".join(celda(fila[k], k) for k, _ in TABLA) + " |")
    L += ["",
          "- **PR-AUC** arranca en la prevalencia (%s) y **ROC-AUC** en 0,5: es lo que da "
          "ordenar al azar." % num(med["tasa"]),
          "- **Lift 20 %**: cuántas veces más vuelve el 20 % de mayor puntaje que el promedio. "
          "**Captura 20 %**: qué parte de los que vuelven cae en ese 20 % (al azar, 20 %).",
          "- **Brier**: error cuadrático de la probabilidad; más chico es mejor.",
          "- **Exactitud (0,5)** está para mostrar por qué no sirve: predecir que nadie vuelve "
          "ya acierta el %s." % pct(1 - med["tasa"]),
          "- Los empates de puntaje (la regla tiene solo dos) se reparten como un sorteo.",
          ""]

    L += ["## ¿Cada escalón le gana al anterior?", "",
          "Diferencia entre un escalón y el anterior, con su intervalo. ✔: el intervalo entero "
          "queda del lado bueno (en Brier, por debajo de 0). El escalón **gana** si gana en "
          "PR-AUC, la métrica principal.", "",
          "| Comparación | " + " | ".join(t for _, t in COMPARA) + " | ¿Gana? |",
          "|---" * (len(COMPARA) + 2) + "|"]
    for par, d in med["diferencias"].items():
        celdas = []
        for k, _ in COMPARA:
            c = "%s (%s a %s)" % (num(d[k]["valor"]), num(d[k]["desde"]), num(d[k]["hasta"]))
            celdas.append(c + (" ✔" if gana(d[k], k) else ""))
        L.append("| %s | %s | %s |" % (par.replace(" - ", " − "), " | ".join(celdas),
                                         "**sí**" if gana(d[CRITERIO], CRITERIO) else "no"))
    L.append("")

    L += ["## Calibración", "",
          "Recta de calibración: logística de la etiqueta sobre el logit de la probabilidad. "
          "Bien calibrado es ordenada 0 y pendiente 1; pendiente menor que 1 quiere decir "
          "probabilidades demasiado extremas.", "",
          "| Escalón | Predicho medio | Observado | Ordenada | Pendiente |", "|---|---|---|---|---|"]
    for e in esc:
        c = med["calibracion"][e["nombre"]]
        L.append("| %s | %s | %s | %s | %s |" % (e["nombre"], pct(c["p_media"]), pct(med["tasa"]),
                                                  num(c["ordenada"], 2), num(c["pendiente"], 2)))
    L += ["", "Por décimos de probabilidad predicha (predicho → observado, en %):", "",
          "| Décimo | " + " | ".join(e["nombre"] for e in esc[2:]) + " |",
          "|---" * (len(esc) - 1) + "|"]
    for i in range(10):
        celdas = []
        for e in esc[2:]:
            t = med["calibracion"][e["nombre"]]["tramos"][i]
            celdas.append("%s → %s" % (num(100 * t["p_media"], 1), num(100 * t["tasa"], 1)))
        L.append("| %d | %s |" % (i + 1, " | ".join(celdas)))
    L.append("")

    L += ["## Hiperparámetros", "",
          "Elegidos con el %s de validación. Con cualquier otro criterio esto se tiene que "
          "volver a correr antes de abrir prueba." % "PR-AUC", ""]
    for e in esc:
        L.append("- **%s**: %s" % (e["nombre"], ", ".join(
            "%s = %s" % (k, num(v, 3) if isinstance(v, float) else v) for k, v in e["elegido"].items())))
    for e in esc:
        if not e.get("grilla"):
            continue
        claves = [k for k in e["grilla"][0] if k not in M.METRICAS]
        L += ["", "Grilla de **%s** (validación):" % e["nombre"], "",
              "| " + " | ".join(claves) + " | PR-AUC | ROC-AUC | Lift 20 % | Brier |",
              "|---" * (len(claves) + 4) + "|"]
        for g in e["grilla"]:
            L.append("| " + " | ".join(str(g[k]) for k in claves) + " | %s | %s | %s | %s |" % (
                num(g["pr_auc"]), num(g["roc_auc"]), num(g["lift_20"], 2), num(g["brier"], 4)))
    L += ["", "---", "", "Generado por `modelo/escalera.py` (semilla %d). Se regenera con "
          "`.venv/Scripts/python -m modelo.escalera%s`." % (SEMILLA, " --prueba" if bloque == "prueba" else ""),
          ""]
    return "\n".join(L)


# -------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prueba", action="store_true", help="medir tambien en prueba (una vez, al final)")
    ap.add_argument("--brazo", default="d0", choices=sorted(D.BRAZOS))
    ap.add_argument("--repeticiones", type=int, default=2000)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    huella = D.huella()
    tabla = D.leer()
    B = D.bloques(tabla, brazo=args.brazo)
    X, y = B["entrenamiento"]
    Xv, yv = B["validacion"]

    escalones = []
    for clase in ESCALERA:
        t0 = time.time()
        escalones.append(clase().ajustar(X, y, Xv, yv))
        avisar("%-12s ajustado en %.1f s: %s" % (clase.nombre, time.time() - t0, escalones[-1].elegido))

    os.makedirs(os.path.join(SALIDA, "modelos"), exist_ok=True)
    joblib.dump({e.nombre: e for e in escalones},
                os.path.join(SALIDA, "modelos", "escalera_%s.joblib" % args.brazo))

    base = {
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "huella": huella,
        "brazo": args.brazo,
        "variables": D.variables(args.brazo),
        "criterio": CRITERIO,
        "entrenamiento": {"n": int(len(y)), "tasa": float(np.mean(y))},
        "escalones": [{"nombre": e.nombre, "descripcion": e.descripcion, "elegido": e.elegido,
                       "grilla": getattr(e, "grilla", None)} for e in escalones],
    }
    for bloque in ["validacion"] + (["prueba"] if args.prueba else []):
        t0 = time.time()
        Xb, yb = B[bloque]
        res = dict(base, bloque=bloque, medida=medir(escalones, Xb, yb, args.repeticiones))
        avisar("%s medido en %.1f s" % (bloque, time.time() - t0))
        nombre = os.path.join(SALIDA, "escalera_%s_%s" % (args.brazo, bloque))
        with open(nombre + ".json", "w", encoding="utf-8") as fh:
            json.dump(sin_nan(res), fh, ensure_ascii=False, indent=1)
        with open(nombre + ".md", "w", encoding="utf-8") as fh:
            fh.write(markdown(res, bloque))
        print("\n%s (%s clientes, vuelve el %s)" % (BLOQUE[bloque], miles(res["medida"]["n"]),
                                                   pct(res["medida"]["tasa"])))
        print("%-12s %8s %8s %8s %8s %8s" % ("", "PR-AUC", "ROC-AUC", "lift10", "lift20", "Brier"))
        for e in escalones:
            m = res["medida"]["modelos"][e.nombre]
            print("%-12s %8.3f %8.3f %8.2f %8.2f %8.4f" % (
                e.nombre, m["pr_auc"]["valor"], m["roc_auc"]["valor"], m["lift_10"]["valor"],
                m["lift_20"]["valor"], m["brier"]["valor"]))
        for par, d in res["medida"]["diferencias"].items():
            print("  %-24s PR-AUC %+.3f [%+.3f, %+.3f] %s" % (
                par, d["pr_auc"]["valor"], d["pr_auc"]["desde"], d["pr_auc"]["hasta"],
                "gana" if gana(d["pr_auc"], "pr_auc") else "no gana"))
        print("-> %s.md" % os.path.relpath(nombre, REPO))


if __name__ == "__main__":
    main()
