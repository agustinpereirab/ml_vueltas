# Escalera de modelos · validación (cohorte 2024)

Generado por `modelo/escalera.py` el 2026-11-19. Tabla `77b71c49b21d…`. Entrenamiento: 13.655 clientes (2023). Validación: 13.595 clientes (2024). El bloque de prueba no se usó.

Entre corchetes, intervalo bootstrap del 95% (2000 remuestreos pareados de los clientes de validación). Brier: más bajo es mejor; el resto, más alto es mejor.

## La escalera (brazo día 0)

| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% | Captura 20% | Brier | Prob. media |
|---|---|---|---|---|---|---|---|
| Prevalencia (a todos la misma probabilidad) | 0,204 [0,198; 0,212] | 0,500 [0,500; 0,500] | 1,00 | 1,00 [1,00; 1,00] | 20,0% | 0,1629 [0,1590; 0,1669] | 21,9% |
| Regla: primer viaje de 10 mil USD o más | 0,204 [0,197; 0,211] | 0,498 [0,493; 0,504] | 0,98 | 0,99 [0,95; 1,03] | 19,8% | 0,1630 [0,1591; 0,1670] | 21,9% |
| Regla: viajó antes como acompañante | 0,243 [0,233; 0,253] | 0,571 [0,562; 0,579] | 1,67 | 1,54 [1,47; 1,61] | 30,8% | 0,1592 [0,1555; 0,1632] | 22,2% |
| Logística · día 0 | 0,340 [0,323; 0,357] | 0,648 [0,637; 0,660] | 1,90 | 1,66 [1,58; 1,73] | 33,2% | 0,1556 [0,1521; 0,1594] | 24,0% |
| CatBoost · día 0 | 0,339 [0,323; 0,358] | 0,643 [0,631; 0,654] | 2,00 | 1,58 [1,51; 1,66] | 31,7% | 0,1558 [0,1522; 0,1596] | 23,7% |

Tasa de vuelta observada en validación: 20,4%. Captura 20%: parte de todas las vueltas que cae en el 20% de clientes con mayor probabilidad (al azar sería 20%).

## ¿Cada escalón le gana al anterior?

Diferencia «modelo − referencia» en validación, con su intervalo. *Sí* = el intervalo no incluye el cero.

| Comparación | PR-AUC | ROC-AUC | Lift 20% | Brier |
|---|---|---|---|---|
| Regla: viajó antes como acompañante − Prevalencia (a todos la misma probabilidad) | 0,038 [0,032; 0,045] · sí | 0,071 [0,062; 0,079] · sí | 0,539 [0,468; 0,608] · sí | -0,0037 [-0,0047; -0,0026] · sí |
| Regla: primer viaje de 10 mil USD o más − Prevalencia (a todos la misma probabilidad) | -0,000 [-0,002; 0,001] · no | -0,002 [-0,007; 0,004] · no | -0,011 [-0,052; 0,026] · no | 0,0001 [0,0000; 0,0002] · peor |
| Logística · día 0 − Regla: viajó antes como acompañante | 0,097 [0,085; 0,110] · sí | 0,078 [0,068; 0,088] · sí | 0,121 [0,053; 0,191] · sí | -0,0036 [-0,0050; -0,0022] · sí |
| CatBoost · día 0 − Logística · día 0 | -0,001 [-0,008; 0,007] · no | -0,006 [-0,012; 0,000] · no | -0,076 [-0,134; -0,007] · peor | 0,0002 [-0,0006; 0,0010] · no |

## Hipótesis 3: los tres brazos

Mismas variables salvo los datos de contacto: sin ellos, como estaban el día 0 (registro de la primera compra) y como están hoy en la ficha única.

| Modelo | PR-AUC | ROC-AUC | Lift 10% | Lift 20% | Captura 20% | Brier | Prob. media |
|---|---|---|---|---|---|---|---|
| Logística · sin datos de contacto | 0,317 [0,301; 0,334] | 0,602 [0,590; 0,615] | 1,88 | 1,52 [1,45; 1,59] | 30,5% | 0,1570 [0,1533; 0,1611] | 22,1% |
| Logística · día 0 | 0,340 [0,323; 0,357] | 0,648 [0,637; 0,660] | 1,90 | 1,66 [1,58; 1,73] | 33,2% | 0,1556 [0,1521; 0,1594] | 24,0% |
| Logística · ficha única | 0,342 [0,325; 0,360] | 0,649 [0,637; 0,660] | 2,01 | 1,61 [1,53; 1,68] | 32,2% | 0,1542 [0,1506; 0,1580] | 22,7% |
| CatBoost · sin datos de contacto | 0,315 [0,298; 0,332] | 0,593 [0,580; 0,605] | 1,88 | 1,56 [1,49; 1,64] | 31,3% | 0,1579 [0,1542; 0,1620] | 22,2% |
| CatBoost · día 0 | 0,339 [0,323; 0,358] | 0,643 [0,631; 0,654] | 2,00 | 1,58 [1,51; 1,66] | 31,7% | 0,1558 [0,1522; 0,1596] | 23,7% |
| CatBoost · ficha única | 0,332 [0,315; 0,351] | 0,630 [0,618; 0,642] | 1,97 | 1,61 [1,54; 1,69] | 32,2% | 0,1564 [0,1528; 0,1604] | 22,7% |

| Comparación | PR-AUC | ROC-AUC | Lift 20% | Brier |
|---|---|---|---|---|
| Logística · ficha única − Logística · día 0 | 0,002 [-0,004; 0,008] | 0,000 [-0,006; 0,007] | -0,049 [-0,100; 0,009] | -0,0015 [-0,0022; -0,0007] |
| CatBoost · ficha única − CatBoost · día 0 | -0,007 [-0,013; -0,001] | -0,013 [-0,020; -0,006] | 0,023 [-0,033; 0,084] | 0,0006 [-0,0002; 0,0014] |
| Logística · día 0 − Logística · sin datos de contacto | 0,022 [0,015; 0,030] | 0,046 [0,037; 0,055] | 0,137 [0,073; 0,198] | -0,0014 [-0,0025; -0,0005] |
| CatBoost · día 0 − CatBoost · sin datos de contacto | 0,025 [0,018; 0,032] | 0,050 [0,041; 0,059] | 0,020 [-0,037; 0,083] | -0,0021 [-0,0031; -0,0012] |

## Calibración (brazo día 0)

Clientes de validación ordenados por probabilidad y partidos en diez grupos iguales.

| Grupo | Logística: prob. media | Logística: vuelven | CatBoost: prob. media | CatBoost: vuelven |
|---|---|---|---|---|
| 1 | 9,4% | 10,2% | 9,5% | 8,5% |
| 2 | 13,0% | 9,8% | 12,5% | 12,9% |
| 3 | 15,5% | 12,9% | 14,9% | 14,2% |
| 4 | 18,2% | 15,3% | 17,7% | 15,9% |
| 5 | 21,0% | 19,7% | 20,5% | 18,9% |
| 6 | 23,7% | 21,8% | 23,2% | 19,9% |
| 7 | 26,6% | 21,8% | 25,7% | 22,9% |
| 8 | 29,8% | 25,2% | 28,8% | 26,4% |
| 9 | 34,8% | 29,1% | 33,7% | 24,0% |
| 10 | 48,4% | 38,8% | 50,0% | 40,8% |

## Cómo se eligió cada cosa (solo con entrenamiento)

- **Regla: primer viaje de 10 mil USD o más:** 890 clientes de entrenamiento la cumplen; vuelven 24,6% contra 21,7% del resto; PR-AUC en entrenamiento 0,221.
- **Regla: viajó antes como acompañante:** 2.043 clientes de entrenamiento la cumplen; vuelven 36,5% contra 19,3% del resto; PR-AUC en entrenamiento 0,255.
- **Mejor regla** (la que se compara con la logística): Regla: viajó antes como acompañante.
- **Logística · dia0:** C = 0.1, elegido por PR-AUC en validación cruzada de 5 pliegues (C=0.003: 0,352, C=0.01: 0,361, C=0.03: 0,365, C=0.1: 0,366, C=0.3: 0,365, C=1.0: 0,363).
- **Logística · ficha_unica:** C = 0.03, elegido por PR-AUC en validación cruzada de 5 pliegues (C=0.003: 0,336, C=0.01: 0,345, C=0.03: 0,349, C=0.1: 0,348, C=0.3: 0,346, C=1.0: 0,343).
- **Logística · sin_contacto:** C = 0.1, elegido por PR-AUC en validación cruzada de 5 pliegues (C=0.003: 0,316, C=0.01: 0,326, C=0.03: 0,329, C=0.1: 0,329, C=0.3: 0,327, C=1.0: 0,325).
- **CatBoost · dia0:** profundidad 4, l2 3, tasa 0.05, 1025 árboles (parada temprana por log-loss en validación cruzada de 5 pliegues; configuración elegida por PR-AUC entre 4).
- **CatBoost · ficha_unica:** profundidad 6, l2 10, tasa 0.05, 1167 árboles (parada temprana por log-loss en validación cruzada de 5 pliegues; configuración elegida por PR-AUC entre 4).
- **CatBoost · sin_contacto:** profundidad 4, l2 3, tasa 0.05, 1115 árboles (parada temprana por log-loss en validación cruzada de 5 pliegues; configuración elegida por PR-AUC entre 4).

Versiones: python 3.14.7, scikit-learn 1.9.1, catboost 1.2.10, numpy 2.5.5. Semilla 2026.
