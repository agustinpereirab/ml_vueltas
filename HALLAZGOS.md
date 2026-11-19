# ¿Vuelve a viajar? · Hallazgos

Proyecto final de Aprendizaje Automático I, con datos de Jetmar (5M Travel Group). Este documento resume qué se hizo, qué se encontró y dónde está cada cosa. Cifras al 2026-11-19.

## En una página

- **La pregunta.** El día de su primera compra, ¿se puede predecir si un cliente nuevo de Jetmar va a volver a viajar con la agencia dentro de los 12 meses?
- **Los datos.** 37.398 clientes nuevos, con primera compra entre enero de 2023 y agosto de 2025, en una tabla anonimizada de 40 columnas. Vuelve el 20% al 22%, según el año.
- **La respuesta: sí, por encima del azar y de una regla simple.** Medido en clientes que el modelo nunca vio (enero a agosto de 2025), evaluados una sola vez con un plan fijado antes:
  - el 10% de clientes con mayor probabilidad vuelve 1,87 veces más que el promedio;
  - contactando al 20% de mayor probabilidad se llega al 31,8% de los que vuelven, contra el 20% contactando al azar.
- **Lo que más pesa:**
  - **Haber viajado antes con Jetmar como acompañante de otro cliente.** Frente a no haberlo hecho, multiplica las chances de volver por 1,51 con un viaje previo, por 2,15 con dos y por 4,23 con tres o más.
  - **Tener mail y teléfono cargados en el registro de la primera compra.**
- **Lo que no pesa,** una vez que están las variables anteriores: el destino (tampoco «regional»), el vendedor, los montos y el tipo de producto.
- **Límites:**
  - El modelo sobreestima: en 2025 predijo 23,9% y volvió el 20,8%, porque cambió la forma en que la agencia carga los datos de contacto.
  - Mide quién tiende a volver, no cuánto suma contactarlo.

## 1. Los datos

| | Clientes | Vuelven a 12 meses |
|---|---|---|
| Entrenamiento: primera compra en 2023 | 13.655 | 21,9% |
| Validación: primera compra en 2024 | 13.595 | 20,4% |
| Prueba: primera compra de enero a agosto de 2025 | 10.148 | 20,8% |

- **Cliente nuevo.** Su primera compra facturada como titular, mirando todo el historial desde 2019, cae en el período. Quedan afuera quienes entraron con una compra corporativa (2.493) y los menores de 18 (264).
- **Vuelve.** Tiene otra compra facturada (como titular o como pasajero) dentro de los 12 meses, para un viaje distinto del primero.
- **Variables.** Solo lo que se sabía el día de la primera compra:
  - la compañía: si viajó antes como acompañante, si viaja con clientes previos;
  - la compra: montos, producto, aerolínea, hotel, quién pagó;
  - el viaje: destino, noches, anticipación, pasajeros;
  - el vendedor;
  - los datos de contacto cargados.
- **Por qué arranca en 2023.** Jetmar no tiene detalle de servicios antes de enero de 2023.
- **Anonimización.** Sin nombres, documentos, mails, teléfonos, fechas ni ids; códigos al azar; bandas y montos redondeados. Cada combinación de lo que alguien de afuera podría saber de un viaje aparece en al menos 5 clientes. Detalle en [`datos/DICCIONARIO.md`](datos/DICCIONARIO.md).

## 2. Cómo se trabajó

1. **Exploración** de cada variable contra la vuelta, solo con entrenamiento: [`analisis/exploracion.html`](analisis/exploracion.html). Se abre en el navegador.
2. **Escalera de modelos.** Cada escalón tiene que ganarle al anterior con intervalo:
   - prevalencia (a todos la misma probabilidad);
   - dos reglas simples;
   - regresión logística;
   - CatBoost (gradient boosting).

   Los hiperparámetros se eligieron dentro de entrenamiento; la validación se usó solo para comparar.
3. **Recalibración** de las probabilidades con validación.
4. **Interpretación** para la hipótesis 2: SHAP, y además reentrenar el modelo sin cada grupo de variables para ver cuánto aporta cada uno.
5. **Prueba única.** El plan ([`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md)) se versionó en git antes de abrir 2025 (commit `69632ac`). El script se niega a correr una segunda vez.

## 3. Resultados en la prueba

| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% |
|---|---|---|---|---|
| Prevalencia | 0,208 | 0,500 | 1,00 | 1,00 |
| Regla: primer viaje de 10 mil USD o más (la de la propuesta) | 0,206 | 0,494 | 0,91 | 0,96 |
| Regla: viajó antes como acompañante | 0,243 | 0,566 | 1,61 | 1,51 |
| **Regresión logística (modelo principal)** | **0,319** | **0,620** | **1,87** | **1,59** |
| Regresión logística reducida (12 variables) | 0,319 | 0,628 | 1,84 | 1,58 |
| CatBoost | 0,312 | 0,614 | 1,85 | 1,53 |

- **Escalera:** la logística le gana a la prevalencia y a la mejor regla en PR-AUC y ROC-AUC, con intervalo. CatBoost no le gana a la logística. La regla de la propuesta no le gana a la prevalencia.
- **Campaña:** contactando al 20% de mayor probabilidad (2.030 clientes) quedan contactados 670 de los 2.109 que vuelven, contra 422 contactando al azar.
- **Modelo reducido:** con 12 variables (compañía, contacto y viaje) ordena igual que el completo y está mejor calibrado. Es más fácil de explicar en la agencia.

Detalle completo, con intervalos: [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md).

## 4. Las hipótesis

| Hipótesis | Resultado |
|---|---|
| **H1.** La recompra se puede predecir por encima de la prevalencia y de una regla simple. | **Confirmada** en la prueba, con el criterio fijado antes de abrirla. |
| **H2.** Pesan el destino regional, viajar con un cliente previo o haber sido acompañante, y el vendedor. | **En parte.** Pesa haber sido acompañante, que es el grupo que más aporta. No pesan el destino regional ni el vendedor, ni viajar con un cliente previo una vez que está lo anterior. |
| **H3.** Parte de la asociación entre «datos de contacto cargados» y volver es fuga de información. | **No se sostiene.** Entrenar con la ficha de hoy rinde igual que con la ficha del día de la primera compra. Los datos de contacto del día 0 sí aportan. |

Las mediciones de cada una están al final de [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md).

## 5. Qué cambió respecto de la propuesta

Los 18 cambios, cada uno con la medición que lo motivó, están en [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md). Los que cambian lo que se presentó:

- **Prevalencia:** vuelve el 21,9%, no «entre 10 y 20».
- **Cohortes:** 2023 a agosto de 2025, no 2021 a 2025, por falta de detalle de servicios antes de 2023.
- **Partición:** entrenamiento 2023, validación 2024 y prueba enero–agosto de 2025, en lugar de entrenar con 2021–2023 y probar con 2024.
- **Variables:** no están el mes de compra ni el de viaje, la ciudad ni la categoría del hotel. Identificaban clientes y casi no aportaban.
- **Regla simple:** se sumó «viajó antes como acompañante», porque la regla de la propuesta no separa.
- **Recalibración y plan de la prueba:** no estaban previstos.

## 6. Límites

- **Sobreestimación.** En 2023 se cargaba el mail al 42,7% de los clientes nuevos y en 2024 al 59,2%; tenerlo pasó a separar menos. El modelo sobreestima, y la recalibración con 2024 corrigió solo parte en 2025. Para usarlo hay que recalibrar cada año.
- **Propensión, no efecto.** Cuánto suma contactar a un cliente solo se sabe con un experimento.
- **Un solo canal.** No se cuentan las vueltas por otras marcas del grupo.
- **Valor medido por la primera compra.** La tabla no trae la utilidad del viaje de vuelta.
- **Identidad sin auditar.** La identidad del cliente viene resuelta por la base de la empresa; este proyecto no la audita.

## 7. Usar el modelo en otra computadora

Los dos modelos evaluados en la prueba están exportados en [`modelo/exportado/`](modelo/exportado/), como JSON con los coeficientes, las transformaciones y la recalibración. [`modelo/puntuar.py`](modelo/puntuar.py) los aplica usando solo Python estándar, sin instalar nada:

```
python modelo/puntuar.py modelo/exportado/principal.json clientes.csv clientes_con_probabilidad.csv
```

- **Qué devuelve:** agrega la columna `prob_vuelve_12`, la probabilidad de que cada cliente vuelva dentro de los 12 meses de su primera compra.
- **Qué necesita la entrada:** las columnas en el formato de la tabla del modelo, con las mismas bandas y categorías.
- **Qué no hace:** no lee una ficha del sistema de gestión tal como viene. Antes hay que calcular las variables del día 0 con la base de la empresa.
  - Del timeline del cliente salen 13 de las 29 variables del modelo principal y 5 de las 12 del reducido.
  - El resto necesita otras tablas: los acompañantes, el vendedor, el registro de contacto, quién pagó y los servicios.
  - El 2026-11-19 se decidió no automatizarlo por ahora.
  - Detalle variable por variable: [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md).
- **Comprobado:** el JSON reproduce las probabilidades del modelo original en los 13.595 clientes de validación.

## 8. Estado y pendientes (2026-11-19)

- **Terminado:** la tabla, la exploración, la escalera, la recalibración, la interpretación, la prueba y los modelos exportados.
- **La prueba ya se usó.** No se vuelve a correr ni se usa para elegir nada. Un análisis nuevo sobre esos clientes se declara como posterior a la prueba.
- **Decidido no hacer por ahora:** el script que puntúa fichas nuevas desde la base.
- **Pendiente:** el material para la defensa (informe o presentación). Falta definir el formato y la fecha. Todo el contenido está en este documento y en los archivos que enlaza.

## 9. Dónde está cada cosa

| Archivo | Qué es |
|---|---|
| [`HALLAZGOS.md`](HALLAZGOS.md) | Este resumen. |
| [`CLAUDE.md`](CLAUDE.md) | Instrucciones para una sesión de Claude que retome el proyecto: orden de lectura, estado y reglas. |
| [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md) | Qué da el modelo, qué necesita para un cliente nuevo y qué está decidido. |
| [`presentacion_propuesta.html`](presentacion_propuesta.html) | La propuesta presentada en clase (Entrega 1). |
| [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md) | Los 18 cambios respecto de la propuesta, con su medición, y el estado de las hipótesis. |
| [`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md) | El plan fijado antes de abrir la prueba. |
| [`datos/DICCIONARIO.md`](datos/DICCIONARIO.md) | Las 40 columnas de la tabla, cómo se definió cada cosa y cómo se anonimizó. |
| [`analisis/exploracion.html`](analisis/exploracion.html) | Gráficas de exploración (abrir en el navegador). |
| [`modelo/resultados/escalera_validacion.md`](modelo/resultados/escalera_validacion.md) | La escalera de modelos en validación. |
| [`modelo/resultados/calibracion_validacion.md`](modelo/resultados/calibracion_validacion.md) | La recalibración. |
| [`modelo/resultados/interpretacion_validacion.md`](modelo/resultados/interpretacion_validacion.md) | Hipótesis 2: qué pesa en el modelo. |
| [`modelo/resultados/reducido_validacion.md`](modelo/resultados/reducido_validacion.md) | El modelo reducido. |
| [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md) | **Resultados finales en la prueba.** |
| [`modelo/exportado/`](modelo/exportado/) | Los modelos listos para usar. |
| `exportacion/`, `modelo/`, `analisis/` | El código. Todo tiene pruebas automáticas. |

**Qué no está:** la tabla de datos (`datos/tabla_modelo.csv`). Está anonimizada, pero no es pública. Sin ella el código no corre, salvo `modelo/puntuar.py` con datos propios en el mismo formato.

## Glosario

- **PR-AUC:** mide qué tan bien el modelo pone arriba a los que vuelven. Ordenar al azar da la tasa de vuelta (alrededor de 0,21); un orden perfecto da 1.
- **ROC-AUC:** probabilidad de que, tomando un cliente que vuelve y uno que no, el modelo le dé más probabilidad al que vuelve. 0,5 es azar; 1 es perfecto.
- **Lift en el x%:** cuántas veces más vuelve el x% de clientes con mayor probabilidad que el promedio.
- **Captura en el 20%:** qué parte de todos los que vuelven queda en el 20% de mayor probabilidad. Al azar sería 20%.
- **Calibración:** que la probabilidad que da el modelo coincida con la tasa que se observa.
- **Intervalo (entre corchetes):** el rango plausible del 95%, por bootstrap. Si una diferencia no incluye el cero, no se explica por azar.
- **SHAP:** cuánto contribuye cada variable a la probabilidad de cada cliente. Se lee como asociación, no como causa.
- **Odds ratio:** cuánto multiplica una característica las chances de volver, con el resto de las variables fijas.
