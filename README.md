# ¿Vuelve a viajar?

Proyecto final de Aprendizaje Automático I. El objetivo es predecir, el día de su primera compra, si un cliente nuevo de Jetmar (5M Travel Group) vuelve a viajar con la agencia dentro de los 12 meses siguientes.

## Qué hay en el repo

| Carpeta o archivo | Qué es |
|---|---|
| [`HALLAZGOS.md`](HALLAZGOS.md) | **El resumen de todo: empezar por acá.** |
| [`presentacion_propuesta.html`](presentacion_propuesta.html) | La propuesta presentada en clase (Entrega 1). |
| [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md) | Qué cambió desde la propuesta y por qué. Se actualiza con cada decisión. |
| [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md) | Qué da el modelo, qué necesita para un cliente nuevo y qué está decidido. |
| [`CLAUDE.md`](CLAUDE.md) | Instrucciones para una sesión de Claude que retome el proyecto. |
| [`datos/`](datos/) | `DICCIONARIO.md` (las columnas de la tabla) y `manifiesto.json` (fecha, filas y huella de la tabla). **La tabla no se versiona.** |
| [`exportacion/`](exportacion/) | Cómo se arma y se verifica la tabla. Los pasos 1 y 2 solo corren dentro de la empresa. |
| [`analisis/`](analisis/) | Exploración de la tabla: `exploracion.html`. |
| [`modelo/`](modelo/) | La escalera de modelos y sus métricas. Los modelos listos para usar están en `modelo/exportado/` y se aplican con `modelo/puntuar.py`. |

## La tabla

`datos/tabla_modelo.csv` no está en el repo. Está anonimizada, pero no es pública: quien tenga acceso a la base de Jetmar puede volver a cruzarla. Para trabajar, copiala a `datos/` y comprobá que es la versión correcta:

```
python exportacion/03_verificar.py
```

El verificador compara el archivo con la huella de `datos/manifiesto.json` y revisa que cumpla las reglas de anonimato.

## Entorno

Python 3.14. Creá el entorno virtual **fuera de OneDrive**: si no, sincroniza cientos de MB de librerías.

```
py -m venv <carpeta fuera de OneDrive>
<carpeta>\Scripts\python -m pip install -r requirements.txt
```

## Cómo se corre

```
python exportacion/03_verificar.py                        # verificar la tabla
python analisis/graficas.py                               # exploracion.html
python modelo/escalera.py                                 # escalera de modelos (validación), ~70 min
python modelo/recalibrar.py                               # recalibración con validación, ~1 min
python modelo/interpretar.py                              # hipótesis 2: grupos y SHAP, ~6 min
python modelo/reducido.py                                 # modelo secundario, ~1 min
python modelo/prueba.py                                   # LA PRUEBA: ya se corrió (2026-11-19) y no vuelve a correr
python modelo/exportar.py                                 # exporta los modelos a modelo/exportado/
python -m unittest discover -s exportacion/pruebas -t .   # pruebas automáticas (tests) del armado de la tabla
python -m unittest discover -s modelo/pruebas -t .        # pruebas automáticas (tests) del modelo
```

**Regla del proyecto: el bloque de prueba (enero a agosto de 2025) se usa una sola vez, al final.** Para elegir y comparar se usan entrenamiento (2023) y validación (2024). La prueba ya se corrió el 2026-11-19, siguiendo [`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md); los resultados están en [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md). Cualquier cambio de modelo posterior tiene que declararse como análisis hecho después de ver la prueba.
