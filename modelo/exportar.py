"""Exporta una logistica entrenada a un JSON portable.

    python modelo/exportar.py

El JSON trae todo lo que hace falta para puntuar sin scikit-learn: las
categorias de cada variable con su coeficiente, la transformacion de cada
numerica (asinh, mediana para faltantes, media y escala) y su indicador de
faltante, el intercepto y la recalibracion. `modelo/puntuar.py` lo aplica con
Python estandar.

Exporta los dos modelos evaluados en la prueba, tal como se evaluaron
(entrenados con 2023, recalibrados con 2024), y comprueba que el JSON
reproduce las probabilidades del modelo original en validacion. Escribe
`modelo/exportado/principal.json` y `modelo/exportado/reducido.json`.
"""
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def exportar(pipe, cats, nums, calibrador, meta):
    """Pipeline de `modelos._logistica` ya ajustado -> dict serializable."""
    pre = pipe.named_steps["pre"]
    w = pipe.named_steps["modelo"].coef_[0]
    salida = {"formato": "logistica_v1", "meta": meta,
              "intercepto": float(pipe.named_steps["modelo"].intercept_[0]),
              "categoricas": {}, "numericas": {}, "calibrador": calibrador}
    i = 0
    for nombre, transformador, columnas in pre.transformers_:
        if transformador == "drop" or len(columnas) == 0:
            continue
        if nombre == "cat":
            for variable, categorias in zip(columnas, transformador.categories_):
                salida["categoricas"][variable] = {str(c): float(w[i + k]) for k, c in enumerate(categorias)}
                i += len(categorias)
        elif nombre == "num":
            imputador = transformador.named_steps["imputar"]
            escala = transformador.named_steps["escalar"]
            indicadores = list(imputador.indicator_.features_) if imputador.indicator_ is not None else []
            n = len(columnas)
            for k, variable in enumerate(columnas):
                salida["numericas"][variable] = {"mediana_asinh": float(imputador.statistics_[k]),
                                                 "media": float(escala.mean_[k]),
                                                 "escala": float(escala.scale_[k]), "coef": float(w[i + k])}
            for j, k in enumerate(indicadores):
                salida["numericas"][columnas[k]]["faltante"] = {
                    "media": float(escala.mean_[n + j]), "escala": float(escala.scale_[n + j]),
                    "coef": float(w[i + n + j])}
            i += n + len(indicadores)
    if i != len(w):
        raise ValueError("la exportacion no cubre todos los coeficientes (%d de %d)" % (i, len(w)))
    return salida


def main():
    import numpy as np
    from modelo import calibracion as cal
    from modelo import datos, modelos, puntuar
    from modelo.escalera import huella_tabla

    resultados = os.path.join(REPO, "modelo", "resultados")
    leer = lambda n: json.load(open(os.path.join(resultados, n), encoding="utf-8"))  # noqa: E731
    huella = huella_tabla()
    esc, calj, red, pru = (leer(n) for n in ("escalera_validacion.json", "calibracion_validacion.json",
                                             "reducido_validacion.json", "prueba.json"))
    d = datos.cargar()
    ent = d[d["bloque"] == "entrenamiento"]
    val = d[d["bloque"] == "validacion"]
    tabla_texto = __import__("pandas").read_csv(datos.RUTA, dtype=str, keep_default_na=False)
    val_texto = tabla_texto[tabla_texto["bloque"] == "validacion"].to_dict("records")

    especificaciones = {
        "principal": (datos.BRAZOS["dia0"], esc["hiperparametros"]["logistica"]["dia0"]["C"], calj["calibrador"]),
        "reducido": (red["columnas"], red["C"], red["calibracion"]["calibrador"]),
    }
    os.makedirs(os.path.join(REPO, "modelo", "exportado"), exist_ok=True)
    for nombre, (columnas, C, calibrador) in especificaciones.items():
        cats, nums = datos.tipos(columnas)
        pipe = modelos._logistica(cats, nums, C).fit(ent[columnas], ent[datos.ETIQUETA].to_numpy())
        esperado = cal.desde_parametros(calibrador).predict(pipe.predict_proba(val[columnas])[:, 1])
        meta = {
            "nombre": nombre, "exportado": datetime.datetime.now().isoformat(timespec="seconds"),
            "que_predice": "probabilidad de que un cliente nuevo vuelva a comprar con Jetmar (para el o como "
                           "pasajero en la compra de otro cliente) dentro de los 12 meses posteriores a "
                           "su primera compra, para un viaje distinto del primero",
            "entrenado_con": "cohorte 2023 (13.655 clientes)", "recalibrado_con": "cohorte 2024",
            "tabla_sha256": huella, "C": C, "variables": columnas,
            "resultado_en_la_prueba": {k: pru["evaluacion"][nombre][k]
                                       for k in ("pr_auc", "roc_auc", "lift_10", "lift_20", "p_media",
                                                 "tasa_observada")},
            "advertencias": [
                "Solo para clientes en su primera compra: no aplica a quien ya compró antes.",
                "Las filas tienen que venir en el formato de datos/tabla_modelo.csv (mismas bandas y "
                "categorías; ver datos/DICCIONARIO.md).",
                "En 2025 sobreestimó: predijo %.1f%% en promedio y volvió el %.1f%%. Sirve más para ordenar "
                "que como probabilidad exacta." % (100 * pru["evaluacion"][nombre]["p_media"],
                                                   100 * pru["evaluacion"][nombre]["tasa_observada"]),
                "Mide propensión a volver, no el efecto de contactar al cliente.",
            ],
        }
        modelo = exportar(pipe, cats, nums, calibrador, meta)
        obtenido = np.array([puntuar.probabilidad(f, modelo) for f in val_texto])
        diferencia = float(np.max(np.abs(obtenido - esperado)))
        if diferencia > 1e-9:
            raise SystemExit("%s: el JSON no reproduce el modelo (diferencia %.2e)" % (nombre, diferencia))
        modelo["meta"]["verificacion"] = ("reproduce las probabilidades del modelo original en los %d clientes "
                                          "de validación (diferencia máxima %.1e)" % (len(val_texto), diferencia))
        ruta = os.path.join(REPO, "modelo", "exportado", nombre + ".json")
        with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(modelo, fh, indent=2, ensure_ascii=False)
        print("%s: %d variables, diferencia máxima con el original %.1e -> %s" % (
            nombre, len(columnas), diferencia, os.path.relpath(ruta, REPO)))


if __name__ == "__main__":
    main()
