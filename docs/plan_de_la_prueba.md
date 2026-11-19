# Plan de la prueba

Este plan se escribió y se versionó en git **antes** de abrir el bloque de prueba: los clientes con primera compra entre enero y agosto de 2025, 10.148 en total. Todo lo que se evalúa, y el criterio que confirma la hipótesis 1, quedó fijado con entrenamiento (2023) y validación (2024).

La prueba se corre **una sola vez** con [`modelo/prueba.py`](../modelo/prueba.py). El script se niega a correr si este archivo tiene cambios sin versionar o si ya hay resultados de la prueba. Los resultados se reportan todos, salgan como salgan. Con la prueba no se elige ni se ajusta nada.

## Modelo principal

Regresión logística con las variables del día 0, entrenada con 2023 (C = 0,1, elegido por validación cruzada dentro de entrenamiento). Las probabilidades se recalibran con el corrimiento de intercepto ajustado en validación: p' = sigmoide(logit(p) − 0,2229).

**Criterio de H1.** H1 se confirma si, en la prueba, el modelo principal le gana a la prevalencia y a la mejor regla simple («viajó antes como acompañante»), en PR-AUC y en ROC-AUC. Para ganar, el intervalo bootstrap pareado del 95% de la diferencia tiene que quedar entero por encima de cero. Si falla alguna de las cuatro comparaciones, H1 no se confirma.

## Análisis secundarios

Se reportan todos, sin cambiar el criterio de H1.

1. **Logística reducida.** Usa 12 variables: compañía previa, datos de contacto del día 0 y viaje. C = 1, recalibrada con intercepto (b = −0,2152). Se compara con la principal. Sus grupos se eligieron mirando validación, así que sus números de validación son optimistas; la prueba es su evaluación limpia.
2. **CatBoost del día 0.** Se usan los hiperparámetros de la escalera (profundidad 4, l2 3, tasa 0,05, 1.025 árboles) y no se recalibra. Se compara con la principal en orden: PR-AUC, ROC-AUC y lift.
3. **Hipótesis 3.** La logística con la ficha única (C = 0,03) y la logística sin datos de contacto (C = 0,1) se comparan con la principal en orden. Recalibrar no cambia el orden de la principal, así que la comparación es justa.
4. **Regla «primer viaje de 10 mil o más»**, contra la prevalencia.
5. **Logística reentrenada con 2023 + 2024** (mismo C, sin recalibrar). Solo se miden métricas de orden. Sus etiquetas se superponen con el período de prueba (ver el registro de cambios, punto 2).
6. **Calibración en la prueba** de la principal y la reducida: probabilidad media contra tasa observada, ECE, pendiente y tabla por decil.

## Simulación de campaña

Se hace con el modelo principal.

- **Escenario:** contactar al 20% de clientes con mayor probabilidad. Se cuentan las vueltas que caen entre los contactados y se comparan con contactar a la misma cantidad al azar. Se agrega la curva de captura del 5% al 100%.
- **Variante:** ordenar por probabilidad × utilidad de la primera compra (índice, con los negativos en cero). Se reporta qué parte de la utilidad de primera compra de los que vuelven queda en el grupo contactado.
- **Límite 1.** La tabla no trae la utilidad del viaje de vuelta. La variante mide el valor del cliente por su primera compra, no lo que deja al volver.
- **Límite 2.** La simulación mide propensión, no el efecto de contactar: cuenta a quienes iban a volver. Cuánto agrega el contacto solo se puede saber con un experimento.

## Métricas e intervalos

- **Métricas:** PR-AUC, ROC-AUC, lift en el 10% y el 20% superior, captura en el 20%, Brier, log-loss y ECE.
- **Intervalos:** bootstrap pareado del 95%, con 2.000 remuestreos de los clientes de prueba y semilla 2026.
