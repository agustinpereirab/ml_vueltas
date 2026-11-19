# Cambios respecto de la propuesta

Este registro compara la propuesta presentada en clase ([`presentacion_propuesta.html`](../presentacion_propuesta.html), Entrega 1) con lo que efectivamente se hizo. Cada entrada dice qué decía la propuesta, qué se hizo, qué medición lo motivó y qué implica para la defensa.

**De dónde salen las cifras.** Salvo que se indique otra fuente, salen de la tabla del modelo ([`datos/tabla_modelo.csv`](../datos/DICCIONARIO.md)). La tabla se armó el 2026-11-11 sobre una foto de la base de ese mismo día, con compras hasta el 2026-11-09. En los puntos 1 a 10, las cifras que miran la etiqueta usan solo el bloque de entrenamiento (cohorte 2023). Hay tres excepciones: los conteos por bloque, la comparación por estación del punto 2 (que usa 2023 y 2024) y los conteos de fichas en proceso del punto 4. Desde el punto 11, cada cifra dice si es de validación (2024) o de la prueba (2025). Los análisis hechos después de correr la prueba están marcados *(posterior a la prueba)*. Las cifras marcadas como *preliminares* son de una copia anterior de la base (septiembre de 2026), con un universo aproximado; sirvieron para decidir, no para citar como resultado.

## Resumen

| # | Tema | Propuesta | Ahora |
|---|---|---|---|
| 1 | Cohortes | primera compra entre 2021 y 2025 | primera compra entre enero de 2023 y agosto de 2025 |
| 2 | Partición | entrenar con 2021–2023, evaluar en 2024 | entrenar con 2023, validar con 2024, probar con enero–agosto de 2025 |
| 3 | Prevalencia | vuelven entre 10 y 20 de cada 100 | vuelven 21,9 de cada 100 |
| 4 | Etiqueta | otra ficha en 12 meses, con viaje a más de 7 días | igual, con tres precisiones |
| 5 | Universo | sin quienes entraron con una compra corporativa | igual, y además sin menores de 18 y sin 31 clientes retirados por anonimato |
| 6 | Variables | la lista de la diapositiva 6 | sin mes de compra ni de viaje, sin ciudad ni categoría de hotel; montos redondeados; utilidad como índice; variables nuevas |
| 7 | Anonimización | ids reemplazados por códigos, sin datos de contacto | además bandas, redondeo, grupos de al menos 5 y 3 clientes, y supresión |
| 8 | Ficha del día 0 | «reconstruida con lo que se sabía ese día» | el registro usado en la primera compra, tal como está hoy |
| 9 | Regla simple | primer viaje de más de 10 mil ⇒ vuelve | se mantiene y se suma «viajó antes como acompañante ⇒ vuelve» |
| 10 | Simulación de campaña | sobre la cohorte 2024 | sobre el bloque de prueba (enero a agosto de 2025) |
| 11 | Hiperparámetros | no se decía | validación cruzada dentro de entrenamiento; validación solo para comparar |
| 12 | Resultado de la escalera | cada escalón tiene que ganarle al anterior | la logística gana; CatBoost no le gana a la logística; la regla de 10 mil no le gana a la prevalencia |
| 13 | Calibración | — | los modelos sobreestiman en 2024 porque cambió cómo se cargan los datos de contacto |
| 14 | Recalibración | no estaba prevista | la logística se recalibra con validación corriendo el intercepto |
| 15 | Interpretación (H2) | SHAP sobre el mejor modelo | SHAP más reentrenar sin cada grupo de variables, con intervalo |
| 16 | Prueba | un modelo, evaluado en la cohorte nueva | principal más secundarios declarados en un plan versionado antes de abrir la prueba |
| 17 | Resultado final | rendimiento moderado pero útil, lift claro en el decil superior | H1 confirmada en la prueba: lift 1,87 en el 10% y 1,59 en el 20% superior |
| 18 | Uso del modelo | no se preveía dejarlo para usar | exportado y portable; puntuar fichas nuevas desde la base, sin automatizar por decisión del usuario |
| 19 | Identidad del cliente | «verificamos que no use información posterior» | no se verificó |

El estado de las tres hipótesis está al final.

---

## 1. Cohortes: de 2021–2025 a enero de 2023 – agosto de 2025

**Propuesta.** Primera compra facturada entre 2021 y 2025. La cohorte 2021 (salida del COVID) se analizaba aparte y 2025 se etiquetaba hasta la fecha de corte.

**Ahora.** Primera compra entre el 2023-01-01 y el 2025-08-31. Son 37.398 clientes.

**Por qué.**

- **Jetmar no tiene detalle de servicios antes de enero de 2023.**
  - En la base, el tipo de producto figura como `sin_detalle` en el 100% de las fichas de titular compradas entre 2019 y 2022, y en menos del 2% desde 2023.
  - La tabla de servicios (aerolínea, hotel, régimen) empieza en 2023.
  - El destino falta en el 34% al 55% de las fichas anteriores a 2023, y en el 10% al 12% de las posteriores.
  - Las otras cinco marcas del grupo sí tienen detalle desde 2019, así que es un hueco de carga de Jetmar.
- **El corte en agosto de 2025 deja margen para la facturación.**
  - La ventana de 12 meses del último cliente se cierra en agosto de 2026, unos dos meses antes de la foto.
  - La etiqueta solo cuenta fichas facturadas, y facturar demora. En la copia de septiembre, el 31,2% de las fichas abiertas en el último mes seguía en proceso, contra el 0,6% de las de 2024 *(preliminar)*.

**Implica.**

- La discusión sobre 2021 y el COVID deja de aplicar.
- Todas las cohortes del modelo tienen las mismas variables disponibles.
- Para usar 2021–2022 habría que conseguir el detalle de servicios de esos años en el back-office. No se sabe si existe.

## 2. Partición: tres bloques por año

**Propuesta.** Partición por tiempo: entrenar con 2021–2023 (2021 aparte) y evaluar en 2024. No había bloque de validación.

**Ahora.** Tres bloques por año calendario, en la columna `bloque`:

| Bloque | Primera compra | Clientes |
|---|---|---|
| Entrenamiento | 2023 | 13.655 |
| Validación | 2024 | 13.595 |
| Prueba | enero a agosto de 2025 | 10.148 |

La tabla trae además `bloque_60_20_20`, que corta en septiembre de 2024 y en marzo de 2025 (23.017 / 6.551 / 7.830 clientes).

**Por qué.**

- Hace falta un bloque para elegir hiperparámetros y comparar escalones sin tocar la prueba.
- Con años enteros, la etiqueta del último cliente de entrenamiento se cierra el 2024-12-31, antes de que compre el primero de prueba. El modelo evaluado podría haber existido el 1 de enero de 2025.
- Con el 60-20-20 eso no se cumple: las etiquetas de entrenamiento se cierran durante el período de prueba. Se dejó la columna por si la cátedra pide esa proporción.

**Implica.**

- El bloque de prueba se usa una sola vez, al final.
- Si el modelo final se reentrena con 2023 + 2024, sus etiquetas se cierran durante 2025 y se superponen con la prueba. Ese resultado se reporta como secundario.
- La prueba no tiene clientes de septiembre a diciembre. En 2023–2024 esos meses son el 30,8% de los clientes nuevos (8.391 de 27.277, contados antes de retirar los 31 clientes por anonimato) y vuelven el 19,8%, contra el 21,8% de los de enero a agosto.

## 3. Prevalencia: 21,9%, no «entre 10 y 20»

**Propuesta.** «De cada 100 clientes nuevos, vuelven entre 10 y 20» (diapositiva 2). «Un modelo que dice "nadie vuelve" acierta el 85%» (diapositiva 11).

**Ahora.** Vuelve el 21,9% del entrenamiento (2.985 de 13.655), el 20,4% de la validación y el 20,8% de la prueba. Predecir que nadie vuelve acierta el 78,1%.

**Por qué.** La cifra de la propuesta era una estimación previa a fijar el universo y la etiqueta.

**Implica.** Cambian los números de las diapositivas 2, 11 y 13. El argumento para no usar accuracy se mantiene.

## 4. Etiqueta: la misma definición, con tres precisiones

**Propuesta.** `vuelve_12` = 1 si el cliente tiene otra ficha dentro de los 12 meses, con fecha de viaje a más de 7 días del primer viaje; solo para clientes con 12 meses observados.

**Ahora.** Igual, con estas precisiones:

1. **Vuelve también quien vuelve como pasajero de otro cliente.** Se agregó la etiqueta alternativa `vuelve_12_comprando`, que solo cuenta las vueltas como titular. Vale 16,9% en entrenamiento, contra 21,9% de `vuelve_12`.
2. **Solo cuentan fichas facturadas.** La base trae ahora también fichas en proceso. Contarlas cambiaría la etiqueta de 1, 10 y 29 clientes de las cohortes 2023, 2024 y 2025.
3. **La primera compra se calcula sobre todo el historial desde 2019.** Quien ya compraba antes de 2023 no entra como nuevo. Si el día 0 compró más de una ficha, todas son la primera compra: venta y utilidad se suman, y el viaje se describe con la ficha de más pasajeros.

## 5. Universo: también sin menores de edad

**Propuesta.** «Fuera quienes entraron con una compra corporativa.»

**Ahora.**

| Paso | Clientes |
|---|---|
| Primera compra entre enero de 2023 y agosto de 2025 | 40.186 |
| − entraron con una compra corporativa | 2.493 |
| − menores de 18 el día 0 (con fecha de nacimiento cargada) | 264 |
| = universo | 37.429 |
| − retirados porque ni suprimiendo todo quedaban en un grupo de al menos 5 | 31 |
| = tabla | 37.398 |

**Definición de corporativo.** Alguna ficha del día 0 tiene la marca `es_corporativa`. En las fichas facturadas de Jetmar esa marca coincide con «pagó una empresa» en el 98,5% de los casos (51.238 de 52.033). Ya no marca los canjes de millas de Itaú Volar, que el análisis de cohortes tenía que corregir a mano.

## 6. Variables

| Propuesta (diapositiva 6) | En la tabla | Por qué cambió |
|---|---|---|
| venta y gasto por pasajero | `venta_usd`, `venta_por_pasajero_usd`, redondeados y con tope | el monto exacto junto al mes de compra dejaba único al 53% de los clientes *(preliminar)* |
| productos | `tipo_producto`, `lleva_hotel`, `tiene_seguro`, `servicios` | — |
| categoría y régimen del hotel | solo `regimen_hotel` | la «categoría» de la base es la de la habitación (estándar, superior…) y está cargada en 13.744 de 33.009 fichas con hotel desde 2023 |
| aerolínea | `aerolinea`: 11 aerolíneas y «otra» | se suprimió en el 29% de las filas por anonimato (punto 7) |
| quién pagó | `pagador`, `canje_millas` | — |
| destino y región | `pais_destino` (14 países y «otro»), `region_destino`; sin ciudad | 283 de 428 ciudades tenían menos de 10 clientes *(preliminar)* |
| cantidad de destinos | `destinos`: 1, 2, 3+ | — |
| duración | `noches`, en 4 bandas | — |
| anticipación | `anticipacion`, en 7 bandas | — |
| **mes de compra y de viaje** | **no está** | ver abajo |
| tipo de grupo | `pasajeros`: 1, 2, 3, 4, 5-9, 10+ | — |
| viaja con clientes previos | `viaja_con_cliente_previo` y `viaja_con_alguien_con_historial` | se separó «ya había comprado» de «ya había viajado» |
| viajó antes como acompañante | `fue_acompaniante_antes`, `viajes_previos_acompaniante` | — |
| antigüedad del vendedor | `vendedor_antiguedad`, en 3 bandas | la base arranca en 2019: «4+» quiere decir «desde antes de 2020» |
| cartera al momento de la venta | `vendedor_fichas_12m`, en 5 bandas | se aproxima con las fichas del vendedor en los 12 meses previos |

**Por qué no están los meses.**

- **Reidentifican.** Con mes de viaje, ciudad y cantidad de pasajeros, el 28,3% de los clientes quedaba en grupos de menos de 5 *(preliminar)*.
- **No ordenaban.** Medidos solos, el AUC fue de 0,499 para el mes de compra y de 0,504 para el de viaje *(preliminar)*.
- **Se perdió la estacionalidad fina.** La temporada del viaje queda en parte reflejada en `anticipacion` y `noches`.

**Variables nuevas.**

- `utilidad_indice`: la utilidad del día 0 dividida por una constante que no se publica.
- `vendedor` (código) y `vendedor_es_persona`.
- Los datos de contacto en dos versiones, `fu_*` y `d0_*`, más `fu_registros`, para la hipótesis 3 (punto 8).
- `vuelve_12_comprando` (punto 4).

**Quedaron afuera sin estar en la propuesta: edad, género y nacionalidad.** Medido sobre el universo definitivo, agregar edad (3 bandas) y género a cohorte, año y trimestre de viaje, país y pasajeros lleva los clientes en grupos de menos de 5 del 1,6% al 25,4%. La fecha de nacimiento queda solo como «está cargada o no».

## 7. Anonimización

**Propuesta.** «Exportación única y disociada»; ids de cliente y vendedor reemplazados por códigos; sin nombres, documentos, mails ni teléfonos (Ley 18.331).

**Ahora.** Además de eso:

- **Bandas y montos.** Bandas en todas las variables numéricas, montos redondeados y con tope, y utilidad como índice.
- **Códigos al azar.** No son un hash del id. La tabla de correspondencia queda dentro de la empresa.
- **Vendedores chicos agrupados.** Los vendedores con menos de 50 clientes van en `V-otros` (1.831 clientes).
- **Grupos de al menos 5 clientes** en la combinación de lo que alguien de afuera puede saber del viaje de un conocido: cohorte, región, país, pasajeros, noches, tipo de producto y hotel.
- **Grupos de al menos 3 clientes** sumando aerolínea, régimen del hotel y cantidad de destinos.
- **Ninguna categoría con menos de 20 clientes.**

El detalle está en [`datos/DICCIONARIO.md`](../datos/DICCIONARIO.md). La verificación ([`exportacion/03_verificar.py`](../exportacion/03_verificar.py)) la puede correr cualquiera que reciba la tabla.

**Implica.**

- **Para llegar a esos grupos se suprimieron valores:**
  - aerolínea en el 29% de las filas;
  - régimen en el 19,7%;
  - cantidad de destinos en el 16%;
  - noches en el 12,2%.
- **`sin_dato` mezcla dos cosas:** «la base no lo trae» y «se suprimió». Se trata como una categoría más.
- **Límite declarado.** Mirando todas las columnas juntas, el 93,6% de las filas es única: quien tenga la base de Jetmar puede volver a cruzarlas. La tabla no es pública.

## 8. Ficha del día 0: el registro de la primera compra, tal como está hoy

**Propuesta.** Entrenar dos veces: con las variables de la ficha única (`dim_persona`, que junta todos los registros del cliente) y con las mismas variables «reconstruidas con lo que se sabía el día 0». El ejemplo era la fecha de nacimiento: vuelve el 10,4% de quienes no la tienen, contra 16% a 20% de quienes sí.

**Ahora.**

- **`fu_tiene_*`:** el dato está cargado hoy en la ficha única o en cualquier registro de la persona.
- **`d0_tiene_*`:** el dato está cargado en el registro de cliente que se usó en la primera compra.
- **`fu_registros`:** cuántos registros junta hoy la ficha única. Solo existe en la versión con fuga.

**Limitación.** El registro del día 0 se ve como está hoy. Si alguien completó el mail después sobre ese mismo registro, cuenta como cargado el día 0. La reconstrucción saca la fuga que viene de registros nuevos, pero no la que viene de editar el mismo registro. La base no guarda la fecha de cada dato.

**Lo que se ve, en entrenamiento, cada variable sola.** La cifra de la propuesta sobre la fecha de nacimiento queda así: vuelve el 12,3% de quienes no la tienen hoy y el 22,8% de quienes sí.

| Dato | Cargado el día 0 | Cargado después | No cargado |
|---|---|---|---|
| Mail | 30,1% (5.824) | 17,2% (2.191) | 15,2% (5.640) |
| Teléfono | 27,2% (6.388) | 19,0% (1.767) | 16,6% (5.500) |
| Fecha de nacimiento | 23,3% (11.643) | 15,6% (815) | 12,3% (1.197) |

Según cuántos registros junta hoy la ficha única: vuelve el 18,8% con uno (6.213 clientes), el 21,8% con dos (3.742) y el 27,1% con tres o más (3.700).

## 9. Regla simple: se suma una segunda

**Propuesta.** El segundo escalón era una regla de negocio: «si el primer viaje supera los 10 mil dólares, vuelve».

**Ahora.** Se mantiene, y se suma «si viajó antes como acompañante, vuelve».

**Por qué.**

- La regla de la propuesta separa poco: vuelve el 24,6% de quienes la cumplen (890 clientes) contra el 21,7% del resto.
- La regla nueva separa 36,5% (2.043 clientes) contra 19,3%. Se eligió mirando solo el bloque de entrenamiento.

**Implica.** La escalera tiene dos reglas, y cada modelo tiene que ganarle a la mejor de las dos. Para medir calibración, cada regla predice la tasa de vuelta de su grupo en entrenamiento.

## 10. Simulación de campaña: sobre la prueba, con utilidad en índice

**Propuesta.** «Ordenamos por probabilidad × utilidad esperada y simulamos la campaña sobre la cohorte 2024.»

**Ahora.** La simulación final va sobre el bloque de prueba (enero a agosto de 2025), porque 2024 pasó a ser validación.

La utilidad viene como índice. Multiplicar por una constante no cambia el orden, así que la priorización es la misma. Lo que cambia es la unidad: los resultados salen en índice. Para leerlos en dólares, alguien de la empresa los multiplica por la constante, que queda adentro.

## 11. Cómo se eligen los hiperparámetros

**Propuesta.** La escalera (prevalencia → regla simple → logística → gradient boosting con CatBoost) y la condición de que cada escalón le gane al anterior con intervalo. No decía cómo se eligen los hiperparámetros.

**Ahora.**

- **Todo se elige dentro de entrenamiento (2023),** con validación cruzada estratificada de 5 pliegues.
  - Logística: el C de la regularización, por PR-AUC.
  - CatBoost: la cantidad de árboles, por parada temprana sobre la log-loss; la configuración (profundidad y regularización), por PR-AUC entre 4.
  - Reglas: cada una predice la tasa de vuelta que tuvo su grupo en entrenamiento.
- **La validación (2024) solo se usa para medir y comparar.** Las comparaciones llevan intervalos bootstrap pareados: 2.000 remuestreos de los mismos clientes para todos los modelos.
- **La prueba (2025) no se tocó.**
- **Logística y CatBoost se ajustan en tres brazos para H3:** sin datos de contacto, con los del día 0 y con los de la ficha única.

**Implica.** Los resultados de validación no están optimizados sobre validación, así que las comparaciones entre escalones son limpias. Código: [`modelo/`](../modelo/). Resultados completos: [`modelo/resultados/escalera_validacion.md`](../modelo/resultados/escalera_validacion.md).

## 12. Resultado de la escalera en validación

Brazo día 0, sobre 13.595 clientes de 2024, de los que vuelve el 20,4%. Entre corchetes, intervalo del 95%.

| Escalón | PR-AUC | ROC-AUC | Lift 20% | Lift 10% | Captura 20% |
|---|---|---|---|---|---|
| Prevalencia | 0,204 | 0,500 | 1,00 | 1,00 | 20,0% |
| Regla: primer viaje de 10 mil o más | 0,204 [0,197; 0,211] | 0,498 [0,493; 0,504] | 0,99 [0,95; 1,03] | 0,98 | 19,8% |
| Regla: viajó antes como acompañante | 0,243 [0,233; 0,253] | 0,571 [0,562; 0,579] | 1,54 [1,47; 1,61] | 1,67 | 30,8% |
| **Logística** | **0,340 [0,323; 0,357]** | **0,648 [0,637; 0,660]** | **1,66 [1,58; 1,73]** | **1,90** | **33,2%** |
| CatBoost | 0,339 [0,323; 0,358] | 0,643 [0,631; 0,654] | 1,58 [1,51; 1,66] | 2,00 | 31,7% |

**Lo que se ve.**

- **La regla de la propuesta no le gana a la prevalencia.** La diferencia en PR-AUC es −0,000 [−0,002; 0,001]. En entrenamiento separaba (24,6% contra 21,7%), pero en 2024 no se sostiene.
- **La regla nueva sí le gana a la prevalencia,** en las cuatro métricas y con intervalo. PR-AUC: +0,038 [0,032; 0,045].
- **La logística le gana a la regla nueva** en las cuatro métricas y con intervalo:
  - PR-AUC: +0,097 [0,085; 0,110];
  - ROC-AUC: +0,078 [0,068; 0,088];
  - lift 20%: +0,12 [0,05; 0,19].
- **CatBoost no le gana a la logística.**
  - PR-AUC: −0,001 [−0,008; 0,007].
  - ROC-AUC: −0,006 [−0,012; 0,000].
  - En lift 20% es peor: −0,08 [−0,13; −0,01].
- **El 10% de clientes con mayor probabilidad** según la logística vuelve 1,9 veces más que el promedio: 38,8%, contra 20,4%.

**Implica.**

- Con la regla de la propuesta («cada escalón tiene que ganarle al anterior»), el modelo candidato es la **logística**.
- CatBoost queda como escalón evaluado que no mejoró, lo que también es un resultado.
- La comparación final se hizo una sola vez sobre la prueba (punto 17).

## 13. Calibración: los modelos sobreestiman en 2024

**Lo que se ve.** La logística del día 0 predice en promedio 24,0% y en validación vuelve el 20,4%. En el décimo de clientes con mayor probabilidad predice 48,4% y vuelve el 38,8%. CatBoost tiene el mismo patrón (23,7% de promedio).

**Por qué.** Hay dos causas, y la segunda pesa más.

1. **Bajó la tasa de vuelta:** 21,9% en 2023 contra 20,4% en 2024. Eso explica 1,5 puntos de la sobreestimación: la prevalencia de entrenamiento, aplicada a 2024, predice 21,9%.
2. **Cambió cómo se cargan los datos de contacto.**

| | 2023 (entrenamiento) | 2024 (validación) | Ene–ago 2025 (prueba) *(posterior a la prueba)* |
|---|---|---|---|
| Clientes con mail cargado el día 0 | 42,7% | 59,2% | 94,7% |
| Vuelven, entre los que tienen mail | 30,1% | 25,0% | 21,3% |
| Clientes sin mail ni teléfono el día 0 | 45,9% | 32,7% | 3,3% |
| Vuelven, entre los que no tienen ninguno | 15,6% | 13,4% | 10,4% |

En 2024 se cargó el mail a más clientes, y «tener mail» pasó a separar menos. El modelo aprendió la relación de 2023 y la aplica a 2024. La logística entrenada sin datos de contacto predice 22,1% en promedio y la del día 0, 24,0%: esa diferencia de 1,9 puntos es la parte que agregan los datos de contacto.

En 2025 el mail se cargó al 94,7% de los clientes nuevos y ya casi no distingue a nadie. Esa columna se midió después de correr la prueba, como descriptivo; no se usó para elegir nada.

**Implica.**

- **Recalibrar con validación** antes de usar las probabilidades como probabilidades. La simulación de campaña ordena por probabilidad × utilidad, así que la necesita. Para eso estaba reservada la validación. Hecho: punto 14.
- **El orden (AUC, lift) se ve menos afectado** que las probabilidades.
- **Para la defensa:** parte de la señal de los datos de contacto depende de la práctica de carga de la agencia, y esa práctica cambia con el tiempo. Un modelo en uso necesitaría recalibrarse cada año.

## 14. Recalibración: se corre el intercepto

**Propuesta.** «Brier y curva de calibración, porque las probabilidades tienen que ser probabilidades.» No preveía recalibrar.

**Ahora.** Las probabilidades de la logística del día 0 se recalibran con validación (2024), corriéndolas en la escala logit: p' = sigmoide(logit(p) − 0,2229). Para elegir, se compararon cuatro métodos con validación cruzada de 5 pliegues dentro de validación: cada cliente se recalibra con un ajuste que no lo vio. El criterio se fijó antes de ver los resultados: menor log-loss, salvo que un método más simple no sea peor con intervalo.

| Método | Log-loss | ECE | Prob. media | Pendiente |
|---|---|---|---|---|
| Sin recalibrar | 0,4857 | 0,0375 | 24,0% | 0,89 |
| **Intercepto** | **0,4817** | **0,0142** | **20,4%** | **0,89** |
| Platt (intercepto y pendiente) | 0,4815 | 0,0110 | 20,4% | 1,00 |
| Isotónica | 0,4826 | 0,0065 | 20,4% | 0,91 |

Tasa observada: 20,4%. ECE: distancia promedio entre probabilidad y tasa observada por decil. Pendiente ideal: 1.

**Lo que se ve.**

- **Recalibrar mejora, con intervalo:**
  - log-loss: −0,0039 [−0,0054; −0,0024];
  - Brier: −0,0017 [−0,0022; −0,0011];
  - ECE: baja de 0,0375 a 0,0142.
- **El orden no cambia:** PR-AUC 0,340 y lift 20% de 1,66, antes y después.
- **Platt tiene la menor log-loss, pero no le gana al intercepto con intervalo** (intercepto − Platt: +0,0003 [−0,0002; 0,0008]). Por el criterio queda el intercepto, que es más simple.
- **Queda un residuo en los extremos.** En el décimo de mayor probabilidad predice 43,1% y vuelve 38,7%; en el de menor, predice 7,7% y vuelve 10,1%. Estos décimos se arman con la probabilidad recalibrada fuera de pliegue, así que no coinciden exactamente con los del punto 13 (38,8%). Con pendiente 0,89, las probabilidades siguen algo extremas, y Platt la lleva a 1,00.

**Implica.**

- **Simulación de campaña:** usa las probabilidades recalibradas. Si reporta vueltas *esperadas*, en el décimo superior las sobreestima en unos 4 puntos (medido en validación). Las vueltas *observadas* en la prueba no dependen de esto.
- **Para la defensa:** cambiar a Platt después de ver este residuo sería elegir mirando el resultado. Se mantiene el criterio y se declara el residuo.
- **Supuesto:** el calibrador se ajustó con 2024 y supone que 2025 se le parece. No se cumplió del todo: en la prueba el modelo siguió sobreestimando (punto 17).
- Resultados completos: [`modelo/resultados/calibracion_validacion.md`](../modelo/resultados/calibracion_validacion.md).

## 15. Hipótesis 2: SHAP más una prueba por grupo

**Propuesta.** «Sobre el mejor modelo aplicamos SHAP, leído como asociación y no como causa.»

**Ahora.** SHAP sobre la logística del día 0, que es el mejor modelo (punto 12). Para un modelo lineal, SHAP es exacto: la contribución de cada variable es su coeficiente por la distancia a la media de entrenamiento. Se verificó contra la librería `shap`. Se sumaron dos medidas por grupo de variables, en validación:

- **Sin el grupo.** La logística se reentrena sin las variables del grupo y se compara con el modelo completo, con intervalo bootstrap pareado. Mide lo que el grupo aporta y ningún otro grupo reemplaza.
- **El grupo solo.** Cuánto ordena el grupo por su cuenta.

H2 habla de «destino regional», así que además se probó un modelo que cambia país y región por una sola marca regional sí/no (Argentina, Brasil, Chile, Paraguay).

**Por qué.** SHAP dice cuánto usa el modelo una variable, no si ese uso predice mejor fuera de la muestra. El vendedor y el destino son el caso: el modelo los usa (SHAP medio de 0,148 y 0,092 por grupo), pero sacarlos no empeora la validación.

**Grupos.**

- **H2 · compañía previa:** viajó antes como acompañante, cuántas veces, viaja con cliente previo, viaja con alguien con historial.
- **H2 · destino:** país y región.
- **H2 · vendedor:** código, si es persona, cartera de 12 meses, antigüedad.
- **Datos de contacto del día 0.**
- **Montos:** venta, venta por pasajero, utilidad.
- **Producto:** tipo, aerolínea, régimen, hotel, seguro, servicios, canje de millas, pagador.
- **Viaje:** pasajeros, destinos, noches, anticipación.

**Implica.**

- **Resultado:** H2 se sostiene en parte (ver «Estado de las hipótesis»).
- **Modelo más chico:** un modelo con solo compañía, contacto y viaje podría rendir igual que el completo, porque los otros cuatro grupos no aportan nada propio en validación. Se probó como modelo secundario antes de abrir la prueba (puntos 16 y 17).
- Resultados completos: [`modelo/resultados/interpretacion_validacion.md`](../modelo/resultados/interpretacion_validacion.md).

## 16. Modelo secundario y plan de la prueba escrito antes de abrirla

**Propuesta.** Un solo modelo final, evaluado en la cohorte que el modelo nunca vio.

**Ahora.**

- **Modelo principal:** la logística completa recalibrada, que es la que salió de la escalera.
- **Modelo secundario: logística reducida.** Usa 12 variables: compañía previa, datos de contacto del día 0 y viaje. Son los únicos grupos con aporte propio en validación (punto 15).
  - En validación rinde igual que la completa en orden: PR-AUC 0,342 contra 0,340; la diferencia es +0,002 [−0,004; 0,009].
  - Queda mejor calibrada: pendiente 0,99 contra 0,89, y log-loss −0,0019 [−0,0037; −0,0001].
  - Se recalibra con el mismo criterio que la principal; quedó el intercepto.
- **Plan de la prueba:** antes de abrir 2025 se escribió y versionó [`docs/plan_de_la_prueba.md`](plan_de_la_prueba.md), junto con el script que la corre. Fija qué se evalúa, el criterio que confirma H1 y los análisis secundarios.

**Por qué.**

- Los grupos del modelo reducido se eligieron mirando validación. Por eso su evaluación limpia es la prueba, y por eso es secundario y no reemplaza al principal.
- Fijar el plan en git antes de abrir la prueba deja constancia de que nada se eligió mirando 2025.

**Implica.** En la defensa se puede mostrar el commit del plan con su fecha, anterior al de los resultados. Resultados de validación del reducido: [`modelo/resultados/reducido_validacion.md`](../modelo/resultados/reducido_validacion.md).

## 17. Resultados de la prueba (enero a agosto de 2025)

Corrida una sola vez el 2026-11-19. El plan y el script se versionaron en el commit `69632ac` (16:46) y los resultados, en el `4fb21b8` (16:53). Son 10.148 clientes, de los que vuelve el 20,8%. Antes de abrir el bloque se conocían su tamaño y su tasa de vuelta, que están en el manifiesto de la tabla; ningún modelo se había entrenado ni evaluado con esos clientes. Detalle completo: [`modelo/resultados/prueba.md`](../modelo/resultados/prueba.md).

| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% | Captura 20% |
|---|---|---|---|---|---|
| Prevalencia | 0,208 | 0,500 | 1,00 | 1,00 | 20,0% |
| Regla: primer viaje de 10 mil o más | 0,206 | 0,494 | 0,91 | 0,96 | 19,2% |
| Regla: viajó antes como acompañante | 0,243 | 0,566 | 1,61 | 1,51 | 30,1% |
| **Logística principal (recalibrada)** | **0,319 [0,301; 0,339]** | **0,620 [0,606; 0,633]** | **1,87** | **1,59** | **31,8%** |
| Logística reducida | 0,319 | 0,628 | 1,84 | 1,58 | 31,6% |
| CatBoost | 0,312 | 0,614 | 1,85 | 1,53 | 30,5% |
| Logística entrenada con 2023 + 2024 | 0,332 | 0,638 | 1,90 | 1,60 | 31,9% |

**Lo que se ve.**

- **H1 se confirma con el criterio del plan.** La principal le gana a la prevalencia (PR-AUC +0,111 [0,096; 0,129]; ROC-AUC +0,120 [0,106; 0,133]) y a la regla «viajó antes como acompañante» (PR-AUC +0,077 [0,064; 0,090]; ROC-AUC +0,053 [0,042; 0,065]).
- **El rendimiento baja algo respecto de validación:** PR-AUC de 0,340 a 0,319 y ROC-AUC de 0,648 a 0,620. Dos causas posibles: la escalera se comparó en validación, y la relación entre los datos de contacto y la vuelta siguió cambiando (ver calibración).
- **La regla de la propuesta tampoco le gana a la prevalencia en la prueba:** PR-AUC −0,002 [−0,003; 0,000].
- **CatBoost no le gana a la logística:** PR-AUC −0,007 [−0,016; 0,002]. Repite lo de validación.
- **La logística reducida ordena igual que la principal en PR-AUC y algo mejor en ROC-AUC, y está mejor calibrada.** PR-AUC +0,000 [−0,007; 0,008]; ROC-AUC +0,009 [0,0003; 0,017] (en `prueba.md` el extremo inferior aparece redondeado como 0,000); log-loss −0,0026 [−0,0047; −0,0006]. Adoptarla ahora como modelo final sería una elección hecha después de ver la prueba, y habría que declararla así.
- **Entrenar con 2023 + 2024 mejora el orden:** PR-AUC +0,013 [0,007; 0,019]; ROC-AUC +0,019 [0,011; 0,026]. Sus etiquetas se superponen con el período de prueba (punto 2), así que es un resultado secundario.
- **Calibración: la sobreestimación siguió en 2025.**
  - La principal recalibrada predice 23,9% en promedio y vuelve el 20,8%. Sin recalibrar predecía 27,9%.
  - La recalibración con 2024 corrigió parte (Brier −0,0046 [−0,0052; −0,0039]), pero no todo: la deriva continuó, como advertía el punto 14.
  - La logística sin datos de contacto predice 22,5%, y la principal sin recalibrar, 27,9%. La mayor parte de la sobreestimación de 2025 viene de los datos de contacto: en 2025 el mail se cargó al 94,7% de los clientes nuevos (punto 13, *posterior a la prueba*).
- **Simulación de campaña.** Contactando al 20% de mayor probabilidad (2.030 clientes), quedan contactados 670 de los 2.109 que vuelven (31,8%), contra 422 al azar. Entre los contactados vuelve el 33,0%. Ordenando por probabilidad × utilidad de la primera compra se contacta a menos de los que vuelven (474), pero queda el 67,5% de la utilidad de primera compra de quienes vuelven (38,8% ordenando solo por probabilidad).

**Implica.**

- **Para la agencia:** la propuesta decía que, si el boosting no le ganaba a la logística, alcanzaba con la regla simple. Pasó lo primero, pero la logística sí le gana a la regla con intervalo: la recomendación es la logística, y la versión reducida es más simple de explicar sin perder orden.
- **Para usarlo de verdad:**
  - recalibrar cada año, por la deriva en la carga de datos de contacto;
  - reentrenar con los años más recientes;
  - medir el efecto del contacto con un experimento.

## 18. Uso del modelo: exportado; puntuar fichas nuevas, sin automatizar

**Propuesta.** «Lo llevamos al negocio»: ordenar clientes por probabilidad y simular una campaña. No hablaba de dejar el modelo para usar.

**Ahora.**

- Los dos modelos evaluados en la prueba (principal y reducido) están exportados como JSON en [`modelo/exportado/`](../modelo/exportado/). [`modelo/puntuar.py`](../modelo/puntuar.py) los aplica sin instalar nada. Reproducen el modelo original en validación y corren en una computadora sin librerías.
- **El 2026-11-19 el usuario decidió no armar, por ahora, el script que puntúa fichas nuevas desde la base.** Su indicación: eso «se maneja con el timeline de un cliente».

**Lo medido.** El modelo recibe filas en el formato de la tabla, no fichas. Del timeline del cliente (`gold.mart_jetuy_persona_timeline`) salen 13 de las 29 variables del modelo principal y 5 de las 12 del reducido. Las demás necesitan:

- el historial de los acompañantes;
- el historial del vendedor;
- el registro de contacto de la primera compra;
- quién pagó;
- los servicios de la ficha.

Detalle, variable por variable: [`docs/uso_del_modelo.md`](uso_del_modelo.md).

**Implica.**

- **El score:** es la probabilidad de volver dentro de los 12 meses, solo para clientes en su primera compra. Sirve más para ordenar que como probabilidad exacta, porque en 2025 sobreestimó (23,9% contra 20,8%).
- **Si se usa en la agencia,** conviene reentrenarlo con todas las cohortes etiquetadas y recalibrarlo cada año. Las dos cosas serían análisis posteriores a la prueba.
- **Desde 2025 el mail casi no separa:** se cargó al 94,7% de los clientes nuevos (punto 13).

## 19. Identidad del cliente: no se verificó

**Propuesta.** «El id de cliente es una identidad resuelta hoy: verificamos que no use información posterior» (diapositiva 12, riesgos).

**Ahora.** No se verificó. El id (`master_customer_id`) viene resuelto por la base de la empresa, que junta los registros de una misma persona con datos de hoy. El proyecto no tiene acceso a cómo se hace esa resolución ni a su historia.

**Implica.**

- **Si la base juntó de más** (dos personas como una), la vuelta queda sobreestimada.
- **Si juntó de menos** (una persona como dos), queda subestimada.
- **En los dos casos** puede haber información posterior en la definición de quién es cliente nuevo.

Es un límite declarado.

---

## Estado de las hipótesis

Estado final, con la prueba (enero a agosto de 2025) ya corrida, una sola vez (punto 17).

**H1 · La recompra se puede predecir por encima de la prevalencia y de una regla simple.** **Confirmada en la prueba**, con el criterio fijado antes de abrirla. La logística principal le gana a la prevalencia y a la mejor regla en PR-AUC y ROC-AUC, con intervalo: PR-AUC 0,319, contra 0,243 de la regla y 0,208 de la prevalencia. El 10% de mayor probabilidad vuelve 1,87 veces el promedio. La regla de la propuesta (primer viaje de 10 mil o más) no supera a la prevalencia, ni en validación ni en la prueba.

**H2 · Pesan más el destino regional, viajar con un cliente previo o haber sido acompañante, y el vendedor.** **Se sostiene en parte:** la compañía previa sí pesa, el destino regional y el vendedor no (punto 15). La prueba es consistente: la logística reducida, sin destino, vendedor, montos ni producto, rinde igual que la completa (PR-AUC +0,000 [−0,007; 0,008]). Medido en validación, reentrenando la logística sin cada grupo:

| Grupo | El modelo pierde sin él (PR-AUC) | El grupo solo (PR-AUC) |
|---|---|---|
| H2 · compañía previa | 0,062 [0,050; 0,074] | 0,288 |
| Datos de contacto (día 0) | 0,022 [0,015; 0,030] | 0,262 |
| Viaje (pasajeros, destinos, noches, anticipación) | 0,005 [0,001; 0,008] | 0,229 |
| H2 · vendedor | 0,002 [−0,003; 0,006] | 0,226 |
| Montos | 0,001 [−0,001; 0,003] | 0,225 |
| Producto | −0,001 [−0,004; 0,003] | 0,217 |
| H2 · destino | −0,004 [−0,007; −0,002] | 0,214 |

Modelo completo: 0,340. Prevalencia: 0,204.

**Cómo leer la tabla.**

- **PR-AUC:** mide qué tan bien el modelo pone arriba a los clientes que vuelven. Ordenar al azar da 0,204 (la tasa de vuelta); un orden perfecto da 1.
- **«El modelo pierde sin él»:** cuánto baja el PR-AUC si se saca ese grupo y se vuelve a entrenar. Es lo que el grupo aporta y ningún otro reemplaza. Ejemplo: sin la compañía previa, el modelo baja de 0,340 a 0,278.
- **Los corchetes:** el rango plausible del 95%.
  - Los dos extremos positivos: el grupo ayuda.
  - Incluyen el cero: no se puede afirmar que ayude.
  - Los dos negativos: el modelo está mejor sin el grupo (el caso del destino).
- **«El grupo solo»:** cuánto ordena el grupo por su cuenta, comparado con el 0,204 del azar.

- **Compañía previa: sí.** Es el grupo que más aporta (cuatro variables).
  - Dentro del grupo, lo que pesa es haber viajado antes como acompañante, y más cuantas más veces. Frente a no haberlo hecho, las chances de volver se multiplican por 1,51 con un viaje previo, por 2,15 con dos y por 4,23 con tres o más.
  - Son odds ratios de la logística entrenada con 2023, con el resto de las variables fijas. «Viajó antes como acompañante» y «cuántas veces» están anidadas, así que el efecto contra «nunca» es el producto de las dos: ×1,66 por la primera, y ×0,91, ×1,29 o ×2,54 por la segunda. Están en `interpretacion_validacion.md`, sección 2.
  - Viajar con un cliente previo está anidado en viajar con alguien con historial. Contra viajar sin nadie con historial, multiplica las chances por 1,21; por encima de viajar con alguien con historial, solo por 1,02.
- **Destino regional: no.**
  - Una marca «regional sí/no» no aporta nada frente a no tener destino: PR-AUC −0,000 [−0,000; 0,000].
  - Los cuatro países regionales tienen efectos de ×0,94 (Brasil) a ×1,09 (Paraguay), contra ×0,97 de promedio regional y ×1,01 del resto.
  - El destino en general tampoco ayuda: sin país ni región, el modelo mejora levemente (+0,004 [0,002; 0,007]).
  - Los efectos por país aprendidos en 2023 no se repiten en 2024. Ejemplo: Paraguay, 26,3% de vuelta en 2023 (76 clientes) y 14,1% en 2024 (85).
- **Vendedor: no, como aporte propio.**
  - Sacar el grupo cambia el PR-AUC en 0,002 [−0,003; 0,006]; sacar solo el código, en 0,001 [−0,004; 0,006].
  - El modelo sí distingue vendedores: el código del percentil 10 multiplica las chances por 0,82 y el del 90 por 1,36. Pero esas diferencias, aprendidas en 2023, no mejoran la predicción de 2024.
  - No se listan ni se ordenan vendedores.
- **Fuera de H2 pesan los datos de contacto del día 0.** Sin ellos, el ROC-AUC cae 0,046, la mayor caída de todos los grupos. El mail cargado el día 0 es la variable con mayor contribución individual (SHAP medio 0,374, contra 0,136 de «viajó antes como acompañante»).

**H3 · Parte de la asociación entre «datos de contacto cargados» y volver es fuga, y se reduce al reconstruir desde la primera compra.** **No se sostiene**, ni en validación ni en la prueba. En la prueba, ficha única − día 0 da PR-AUC +0,002 [−0,003; 0,008] y ROC-AUC +0,004 [−0,002; 0,011]. Los datos de contacto del día 0 sí aportan: sin ellos, el PR-AUC baja 0,014 [0,008; 0,020]. En validación:

| Comparación | PR-AUC | ROC-AUC | Brier |
|---|---|---|---|
| Logística: ficha única − día 0 | +0,002 [−0,004; 0,008] | +0,000 [−0,006; 0,007] | −0,0015 [−0,0022; −0,0007] |
| CatBoost: ficha única − día 0 | −0,007 [−0,013; −0,001] | −0,013 [−0,020; −0,006] | +0,0006 [−0,0002; 0,0014] |
| Logística: día 0 − sin datos de contacto | +0,022 [0,015; 0,030] | +0,046 [0,037; 0,055] | −0,0014 [−0,0025; −0,0005] |

- **El orden no cambia.** En la logística, ficha única y día 0 ordenan igual. El Brier algo mejor de la ficha única viene de que sobreestima menos (22,7% de promedio contra 24,0%), no de que ordene mejor.
- **Los datos del día 0 sí agregan.** Comparado con no tenerlos, mejoran el PR-AUC y el ROC-AUC con intervalo.
- **Es consistente con la exploración:** quienes cargaron el dato después vuelven parecido a quienes no lo tienen (punto 8), así que sumar ese dato no agrega señal.
- **Lo que sí apareció es otro problema:** la relación entre datos de contacto y vuelta cambió entre 2023 y 2024, y en 2025 el mail ya se cargaba a casi todos (punto 13).
- **Limitación:** el registro del día 0 se ve como está hoy (punto 8). Esta medición no descarta fuga por edición del mismo registro.

## Riesgos de la propuesta: dónde quedaron

- **2025 sin 12 meses completos.** Resuelto con el corte en agosto de 2025 (punto 1).
- **El id de cliente es una identidad resuelta hoy.** Sigue sin auditar: la resolución de identidad viene de la base y este proyecto no la controla. Es un cambio respecto de lo que prometía la propuesta (punto 19).
- **Propensión a volver no es el efecto de contactar.** Sin cambios: es una limitación declarada.
