# ¿Vuelve a viajar? · Hallazgos

Proyecto final de Aprendizaje Automático I, con datos de Jetmar (5M Travel Group). Este documento resume qué se hizo, qué se encontró y dónde está cada cosa. Cifras al 2026-11-19. Junto a cada cifra se indica de qué bloque de clientes sale: entrenamiento (2023), validación (2024) o prueba (enero a agosto de 2025).

## En una página

- **La pregunta.** El día de su primera compra, ¿se puede predecir si un cliente nuevo de Jetmar vuelve a comprar con la agencia dentro de los 12 meses, sea para él o como pasajero en la compra de otro cliente?
- **Los datos.** 37.398 clientes nuevos, con primera compra entre enero de 2023 y agosto de 2025, en una tabla anonimizada de 40 columnas. Vuelve entre el 20% y el 22%, según el año.
- **La respuesta: sí, por encima del azar y de una regla simple.** Se midió en la **prueba**: clientes que el modelo nunca vio, evaluados una sola vez con un plan fijado antes.
  - El 10% de clientes con mayor probabilidad vuelve 1,87 veces el promedio: alrededor del 39%, contra el 20,8% del total.
  - Contactando al 20% de mayor probabilidad se llega al 31,8% de los que vuelven, contra el 20% contactando al azar.
- **Lo que más pesa,** medido en validación:
  - **Haber viajado antes con Jetmar como acompañante de otro cliente.** Frente a no haberlo hecho, multiplica las chances de volver por 1,51 con un viaje previo, por 2,15 con dos y por 4,23 con tres o más. Son odds ratios del modelo entrenado con 2023, combinando dos variables anidadas.
  - **Tener cargados el mail y la fecha de nacimiento en el registro de la primera compra,** sobre todo el mail.
- **Sin evidencia de aporte adicional** una vez que están las variables anteriores, también medido en validación: el destino (tampoco la marca «regional»), el vendedor, los montos y el tipo de producto.
- **Límites:**
  - El modelo sobreestima: en la prueba, ya recalibrado con 2024, predijo 23,9% y volvió el 20,8%. Una explicación plausible, no demostrada, es que cambió la carga del mail: se cargaba al 42,7% de los clientes nuevos en 2023, al 59,2% en 2024 y al 94,7% en enero–agosto de 2025, así que tenerlo dejó de distinguir. La cifra de 2025 es un descriptivo hecho después de la prueba.
  - El modelo mide quién tiende a volver, no cuánto suma contactarlo.

## 1. Los datos

| | Clientes | Vuelven a 12 meses |
|---|---|---|
| Entrenamiento: primera compra en 2023 | 13.655 | 21,9% |
| Validación: primera compra en 2024 | 13.595 | 20,4% |
| Prueba: primera compra de enero a agosto de 2025 | 10.148 | 20,8% |

- **Cliente nuevo.** Su primera compra facturada como titular, mirando todo el historial desde 2019, cae en el período.
- **Cuántos quedan.** De 40.186 clientes nuevos se descontaron:
  - 2.493 que entraron con una compra corporativa;
  - 264 menores de 18;
  - 31 que no se podían anonimizar.

  Quedan 37.398.
- **Vuelve.** Tiene otra compra facturada dentro de los 12 meses, como titular o como pasajero, para un viaje distinto del primero (con la fecha de viaje a más de 7 días). Lo que tiene que caer dentro de los 12 meses es la **compra**, no el viaje.
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

   Los hiperparámetros se eligieron con validación cruzada dentro de entrenamiento.
3. **Usos de la validación.** Sirvió para comparar los escalones, recalibrar las probabilidades, interpretar el modelo (SHAP y reentrenar sin cada grupo de variables) y elegir las variables del modelo reducido.
4. **Prueba única.**
   - El plan ([`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md)) y el script se versionaron en git antes de abrir 2025 (commit `69632ac`, 16:46). Los resultados están en el commit `4fb21b8` (16:53).
   - Antes de abrirla se conocían el tamaño del bloque y su tasa de vuelta (20,8%), porque están en el manifiesto de la tabla. Ningún modelo se había entrenado ni evaluado con esos clientes.
   - El script se niega a correr una segunda vez.
   - **Es una evaluación retrospectiva entre cohortes.** El ajuste usó solo 2023, pero la elección y la recalibración usaron etiquetas de 2024 que se cerraron durante 2025, cuando ya entraban clientes de prueba. Detalle en el registro de cambios, punto 21.

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
- **Modelo reducido.** Usa 12 variables: compañía previa, datos de contacto del día 0 y viaje.
  - Ordena igual que el principal en PR-AUC (+0,000 [−0,007; 0,008]) y algo mejor en ROC-AUC (+0,009 [0,0003; 0,017]).
  - Está mejor calibrado.
  - Se definió como secundario antes de la prueba. Adoptarlo ahora como modelo final sería una elección hecha después de verla, y habría que decirlo así.

Detalle completo, con intervalos: [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md).

## 4. Las hipótesis

| Hipótesis | Resultado |
|---|---|
| **H1.** La recompra se puede predecir por encima de la prevalencia y de una regla simple. | **Confirmada** en la prueba, con el criterio fijado antes de abrirla. |
| **H2.** Pesan más el destino regional, viajar con un cliente previo o haber sido acompañante, y el vendedor. | **En parte,** medido en validación. El grupo que más aporta es la compañía previa (4 variables), y dentro de él, haber sido acompañante. Sin evidencia de aporte adicional del destino regional ni del vendedor. Viajar con un cliente previo agrega poco por encima de viajar con alguien con historial (×1,02). |
| **H3.** Parte de la asociación entre «datos de contacto cargados» y volver es fuga de información. | **Señal adicional incierta** (antes «no se sostiene»; registro de cambios, punto 21). Entrenar con la ficha única rinde igual que con el registro de la primera compra, en validación y en la prueba. Los dos se observaron al exportar y pueden compartir ediciones posteriores, así que no se descarta esa fuga. Los datos de contacto del registro inicial sí aportan frente a no tenerlos. |

Las mediciones de cada una están al final de [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md).

## 5. Qué cambió respecto de la propuesta

Los 22 cambios, cada uno con la medición que lo motivó, están en [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md). Los que cambian lo que se presentó:

- **Prevalencia:** vuelve el 21,9%, no «entre 10 y 20».
- **Cohortes:** 2023 a agosto de 2025, no 2021 a 2025, por falta de detalle de servicios antes de 2023.
- **Partición:** la propuesta entrenaba con 2021–2023 (2021 analizada aparte) y probaba con 2024. Ahora: entrenamiento 2023, validación 2024 y prueba enero–agosto de 2025.
- **Variables:** no están el mes de compra ni el de viaje, la ciudad ni la categoría del hotel. Identificaban clientes y casi no aportaban.
- **Regla simple:** se sumó «viajó antes como acompañante», porque la regla de la propuesta no separa.
- **Lo que no estaba previsto:** la recalibración, el modelo reducido y el plan de la prueba.
- **Lo que se prometió y no se hizo:**
  - verificar que la identidad del cliente no use información posterior;
  - la extensión de la página escrita. Para el segundo modelo, al regreso del viaje, no hay datos posteriores a la compra que se puedan fechar: la devolución queda marcada, pero su fecha depende del vendedor. El análisis de supervivencia era posible con la base, pero quedó fuera del alcance;
  - la muestra disociada para replicar: el repositorio es público y la tabla no se publica; si el docente la pide, el acceso se evalúa en ese momento (registro de cambios, punto 22).
- **La regla de decisión:** la propuesta decía que, si CatBoost no le ganaba a la logística, alcanzaba con la regla simple. CatBoost no le ganó, pero la logística sí le ganó a la regla, así que se recomienda la logística.

## 6. Límites

- **Sobreestimación.** Sin recalibrar, el modelo principal predijo 27,9% en la prueba, y volvió el 20,8%: 7,1 puntos de más.
  - **La logística entrenada sin datos de contacto predice 22,5%,** 5,4 puntos menos que la principal sin recalibrar. Es la diferencia entre dos modelos: compatible con que parte del exceso venga de los datos de contacto, no una prueba de la causa (registro de cambios, punto 21).
  - **El mail figura cada vez más.** El modelo aprendió con 2023 que tener mail separa, y la carga del mail pasó del 42,7% de los clientes nuevos en 2023 al 59,2% en 2024 y al 94,7% en enero–agosto de 2025. Es un descriptivo posterior a la prueba: [`modelo/resultados/carga_contacto.md`](modelo/resultados/carga_contacto.md).
  - **La recalibración con 2024** corrigió la parte que ya se veía ese año y dejó el modelo en 23,9%. Quedan 3,1 puntos; la tasa de vuelta incluso subió de 2024 a 2025 (20,4% → 20,8%), así que no los explica una caída de la tasa.
  - **Para usarlo** hay que reentrenar y recalibrar con datos recientes.
- **Propensión, no efecto.** Cuánto suma contactar a un cliente solo se sabe con un experimento.
- **Un solo canal.** No se cuentan las vueltas por otras marcas del grupo.
- **Valor medido por la primera compra.** La tabla no trae la utilidad del viaje de vuelta.
- **Identidad sin auditar.** La identidad del cliente viene resuelta por la base de la empresa; no se verificó.

## 7. Usar el modelo en otra computadora

El modelo principal y el reducido (dos de los siete evaluados en la prueba) están exportados en [`modelo/exportado/`](modelo/exportado/), como JSON con los coeficientes, las transformaciones y la recalibración. [`modelo/puntuar.py`](modelo/puntuar.py) los aplica usando solo Python estándar, sin instalar nada:

```
python modelo/puntuar.py modelo/exportado/principal.json clientes.csv clientes_con_probabilidad.csv
```

- **Qué devuelve:** agrega la columna `prob_vuelve_12`, la probabilidad de que el cliente vuelva dentro de los 12 meses de su primera compra.
- **Qué necesita la entrada:** las columnas en el formato de la tabla del modelo, con las mismas bandas y categorías.
- **Qué no hace:** no lee una ficha del sistema de gestión tal como viene. Antes hay que calcular las variables del día 0 con la base de la empresa.
  - Del timeline del cliente salen 13 de las 29 variables del modelo principal y 5 de las 12 del reducido.
  - El 2026-11-19 se decidió no automatizarlo por ahora.
- **Cuidado con el mail:** en enero–agosto de 2025 casi todos los clientes nuevos lo tenían cargado (94,7%, descriptivo posterior a la prueba), así que esa variable ya no separa como en 2023.
- **Comprobado:** el JSON reproduce las probabilidades del modelo original en los 13.595 clientes de validación.

Detalle: [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md).

## 8. Estado y pendientes (2026-11-20)

- **Terminado:** la tabla, la exploración, la escalera, la recalibración, la interpretación, la prueba y los modelos exportados.
- **La prueba ya se usó.** No se vuelve a correr ni se usa para elegir nada. Un análisis nuevo sobre esos clientes se declara como posterior a la prueba. Uno ya hecho: la carga del mail en 2025.
- **Decidido no hacer por ahora:** el script que puntúa fichas nuevas desde la base.
- **No evaluado:** la etiqueta alternativa `vuelve_12_comprando` y la partición `bloque_60_20_20`. Están en la tabla por si se piden.
- **Material de la defensa (2026-11-20):** el informe (`informe/informe.pdf`) y la presentación (`presentacion/presentacion.html`, con su PDF, `GUION.md` y `GUIA.md`). Ninguno de los dos se versiona. Las cifras salen de este resumen y de `modelo/resultados/`.
- **Historial de git.** El zip de hallazgos trae `HISTORIAL_GIT.txt` y `repo.bundle`, con las fechas de cada commit. Con `git clone repo.bundle` se recupera el historial completo.

## 9. Dónde está cada cosa

| Archivo | Qué es |
|---|---|
| [`HALLAZGOS.md`](HALLAZGOS.md) | Este resumen. |
| [`CLAUDE.md`](CLAUDE.md) | Instrucciones para una sesión de Claude que retome el proyecto: orden de lectura, estado y reglas. |
| [`presentacion_propuesta.html`](presentacion_propuesta.html) | La propuesta presentada en clase (Entrega 1). Sus cifras están superadas. |
| `informe/` | El informe final (6 páginas, el máximo de la consigna), armado con `informe/armar_informe.py`. No se versiona. |
| `presentacion/` | La defensa oral: `presentacion.html` (sin conexión), su PDF, `GUION.md` y `GUIA.md`. No se versiona: está solo en la máquina del equipo. |
| [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md) | Los 22 cambios respecto de la propuesta, con su medición, y el estado de las hipótesis. **Es la fuente de verdad.** |
| [`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md) | El plan fijado antes de abrir la prueba. No se edita. |
| [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md) | Qué da el modelo, qué necesita para un cliente nuevo y qué está decidido. |
| [`datos/DICCIONARIO.md`](datos/DICCIONARIO.md) | Las 40 columnas de la tabla, cómo se definió cada cosa y cómo se anonimizó. |
| [`analisis/exploracion.html`](analisis/exploracion.html) | Gráficas de exploración con entrenamiento (abrir en el navegador). |
| [`modelo/resultados/escalera_validacion.md`](modelo/resultados/escalera_validacion.md) | La escalera de modelos en validación. |
| [`modelo/resultados/calibracion_validacion.md`](modelo/resultados/calibracion_validacion.md) | La recalibración. |
| [`modelo/resultados/interpretacion_validacion.md`](modelo/resultados/interpretacion_validacion.md) | Hipótesis 2: qué pesa en el modelo, con los odds ratios. |
| [`modelo/resultados/reducido_validacion.md`](modelo/resultados/reducido_validacion.md) | El modelo reducido. |
| [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md) | **Resultados finales en la prueba.** |
| [`modelo/resultados/carga_contacto.md`](modelo/resultados/carga_contacto.md) | Carga de los datos de contacto por año. Descriptivo posterior a la prueba. |
| [`modelo/resultados/campania_regla.md`](modelo/resultados/campania_regla.md) | Cómo llena la regla del acompañante el cupo del 20% en la prueba (1.748 acompañantes previos). Descriptivo posterior a la prueba. |
| [`modelo/resultados/variables_solas.md`](modelo/resultados/variables_solas.md) | Cuánto ordena cada variable por sí sola, en validación (ROC-AUC, PR-AUC, r y r²). Exploratorio. |
| [`modelo/exportado/`](modelo/exportado/) | Los modelos listos para usar. |
| `exportacion/`, `modelo/` | El código, con pruebas automáticas (tests) en sus carpetas `pruebas/`. |
| `analisis/` | El código de las gráficas, sin tests. |

**Qué no está:** la tabla de datos (`datos/tabla_modelo.csv`). Está anonimizada, pero no es pública. Sin ella corren las pruebas automáticas, que usan datos inventados, y `modelo/puntuar.py` con datos propios en el mismo formato. Los demás scripts necesitan la tabla.

## Glosario

- **Prueba / bloque de prueba:** los clientes con primera compra entre enero y agosto de 2025, evaluados una sola vez. No confundir con las **pruebas automáticas** (tests) de las carpetas `pruebas/`.
- **Ficha:** en la base, una compra (una «ficha» facturada). **Ficha única** y **ficha del día 0** son otra cosa: los datos de contacto de la persona, como están hoy (ficha única) o como estaban en el registro usado en su primera compra (ficha del día 0).
- **PR-AUC:** mide qué tan bien el modelo pone arriba a los que vuelven. Ordenar al azar da la tasa de vuelta (alrededor de 0,21); un orden perfecto da 1.
- **ROC-AUC:** probabilidad de que, tomando un cliente que vuelve y uno que no, el modelo le dé más probabilidad al que vuelve. 0,5 es azar; 1 es perfecto.
- **Lift en el x%:** cuántas veces la tasa de vuelta del x% de clientes con mayor probabilidad es la tasa promedio. Un lift de 1,87 quiere decir que esa tasa es 1,87 veces la promedio, o sea un 87% más alta.
- **Captura en el 20%:** qué parte de todos los que vuelven queda en el 20% de mayor probabilidad. Al azar sería 20%.
- **Brier:** error cuadrático medio entre la probabilidad y lo que pasó (0 o 1). Más bajo es mejor.
- **Log-loss:** penaliza más las probabilidades seguras y equivocadas. Más bajo es mejor.
- **Calibración:** que la probabilidad que da el modelo coincida con la tasa que se observa. El **ECE** es la distancia promedio entre las dos en cada décimo de clientes. La **pendiente de calibración** vale 1 si está bien calibrado; menor que 1 quiere decir probabilidades demasiado extremas.
- **Recalibración por intercepto:** corre todas las probabilidades en la escala logit, p' = sigmoide(logit(p) + b). En el modelo principal b = −0,2229; en el reducido, b = −0,2152. No confundir con el **intercepto del modelo** (el término fijo de la regresión) ni con el **intercepto de calibración** (un diagnóstico, junto a la pendiente).
- **Intervalo (entre corchetes):** el rango plausible del 95%, por **bootstrap pareado**: se remuestrean 2.000 veces los mismos clientes para todos los modelos. Si una diferencia no incluye el cero, no se explica por azar.
- **SHAP:** cuánto contribuye cada variable a la probabilidad de cada cliente. Se lee como asociación, no como causa.
- **Odds ratio:** cuánto multiplica una característica las chances de volver, con el resto de las variables fijas. Para variables anidadas (por ejemplo, «viajó antes como acompañante» y «cuántas veces»), el efecto contra «ninguna» es el producto de los dos.
- **Alemania (GE):** en la base, el código GE agrupa sobre todo destinos de Alemania (Fráncfort, Múnich, Düsseldorf, Hamburgo) y unos pocos de Georgia. Berlín figura aparte como DE y en la tabla cae en «otro».

## Referencias sugeridas para el informe

Las dos primeras están en la propuesta. Antes de citar las demás, revisar el formato que pida la cátedra.

- Lemmens, A. y Croux, C. (2006). Bagging and boosting classification trees to predict churn. *Journal of Marketing Research*, 43(2), 276–286.
- Kaufman, S., Rosset, S., Perlich, C. y Stitelman, O. (2012). Leakage in data mining: formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data*, 6(4).
- Prokhorenkova, L. et al. (2018). CatBoost: unbiased boosting with categorical features. *NeurIPS 31*.
- Lundberg, S. M. y Lee, S.-I. (2017). A unified approach to interpreting model predictions. *NeurIPS 30*.
- Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. En *Advances in Large Margin Classifiers*. MIT Press.
- Zadrozny, B. y Elkan, C. (2002). Transforming classifier scores into accurate multiclass probability estimates. *KDD 2002*.
- Van Calster, B. et al. (2019). Calibration: the Achilles heel of predictive analytics. *BMC Medicine*, 17, 230.
- Saito, T. y Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLoS ONE*, 10(3), e0118432.
- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1), 1–3.
- Efron, B. y Tibshirani, R. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Sweeney, L. (2002). k-anonymity: a model for protecting privacy. *International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems*, 10(5), 557–570.
- Uruguay. Ley N.º 18.331 de Protección de Datos Personales y Acción de «Habeas Data» (2008).
