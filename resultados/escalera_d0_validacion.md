# Escalera de modelos · validación · cohorte 2024

2026-11-12 · tabla `77b71c49b21d…` · brazo `d0` (sin las columnas de ficha única)

Entrenados con la cohorte 2023: 13.655 clientes, vuelve el 21,9 %. Medidos sobre validación · cohorte 2024: 13.595 clientes, vuelve el 20,4 %. Entre paréntesis, intervalo bootstrap del 95 % (2.000 repeticiones, pareadas: en cada una, todos los modelos se miden sobre la misma muestra de clientes).

Los hiperparámetros de la logística y del boosting se eligieron mirando este mismo bloque, así que sus números acá salen algo optimistas. La medida final es la de prueba.

## Métricas

| Escalón | PR-AUC | ROC-AUC | Lift 10 % | Lift 20 % | Captura 20 % | Brier | Exactitud (0,5) |
|---|---|---|---|---|---|---|---|
| 1. **prevalencia** — A todos la tasa de vuelta de entrenamiento | 0,204 (0,198–0,211) | 0,500 (0,500–0,500) | 1,00 (1,00–1,00) | 1,00 (1,00–1,00) | 20,0 % (20,0–20,0) | 0,163 (0,159–0,167) | 79,6 % (78,9–80,2) |
| 2. **regla** — Venta del día 0 por encima de 10.000 USD ⇒ vuelve | 0,204 (0,197–0,211) | 0,499 (0,493–0,504) | 0,98 (0,90–1,06) | 0,99 (0,96–1,03) | 19,8 % (19,1–20,6) | 0,163 (0,159–0,167) | 79,6 % (78,9–80,2) |
| 3. **logistica** — Regresión logística L2, categóricas en one-hot | 0,342 (0,325–0,360) | 0,652 (0,640–0,664) | 1,97 (1,85–2,09) | 1,66 (1,58–1,73) | 33,1 % (31,6–34,6) | 0,155 (0,151–0,158) | 80,0 % (79,4–80,7) |
| 4. **boosting** — LightGBM, categóricas nativas | 0,346 (0,328–0,364) | 0,649 (0,638–0,661) | 2,08 (1,96–2,20) | 1,69 (1,62–1,77) | 33,8 % (32,3–35,4) | 0,155 (0,152–0,158) | 80,0 % (79,4–80,7) |

- **PR-AUC** arranca en la prevalencia (0,204) y **ROC-AUC** en 0,5: es lo que da ordenar al azar.
- **Lift 20 %**: cuántas veces más vuelve el 20 % de mayor puntaje que el promedio. **Captura 20 %**: qué parte de los que vuelven cae en ese 20 % (al azar, 20 %).
- **Brier**: error cuadrático de la probabilidad; más chico es mejor.
- **Exactitud (0,5)** está para mostrar por qué no sirve: predecir que nadie vuelve ya acierta el 79,6 %.
- Los empates de puntaje (la regla tiene solo dos) se reparten como un sorteo.

## ¿Cada escalón le gana al anterior?

Diferencia entre un escalón y el anterior, con su intervalo. ✔: el intervalo entero queda del lado bueno (en Brier, por debajo de 0). El escalón **gana** si gana en PR-AUC, la métrica principal.

| Comparación | PR-AUC | ROC-AUC | Lift 20 % | Brier | ¿Gana? |
|---|---|---|---|---|---|
| regla − prevalencia | −0,000 (−0,002 a 0,001) | −0,001 (−0,007 a 0,004) | −0,009 (−0,045 a 0,029) | 0,000 (−0,000 a 0,000) | no |
| logistica − regla | 0,138 (0,123 a 0,155) ✔ | 0,153 (0,141 a 0,166) ✔ | 0,665 (0,582 a 0,745) ✔ | −0,008 (−0,010 a −0,007) ✔ | **sí** |
| boosting − logistica | 0,003 (−0,004 a 0,011) | −0,003 (−0,009 a 0,003) | 0,034 (−0,024 a 0,101) | 0,000 (−0,000 a 0,001) | no |

## Calibración

Recta de calibración: logística de la etiqueta sobre el logit de la probabilidad. Bien calibrado es ordenada 0 y pendiente 1; pendiente menor que 1 quiere decir probabilidades demasiado extremas.

| Escalón | Predicho medio | Observado | Ordenada | Pendiente |
|---|---|---|---|---|
| prevalencia | 21,9 % | 20,4 % | — | — |
| regla | 21,9 % | 20,4 % | −1,75 | −0,31 |
| logistica | 23,6 % | 20,4 % | −0,21 | 0,99 |
| boosting | 24,2 % | 20,4 % | −0,19 | 1,04 |

Por décimos de probabilidad predicha (predicho → observado, en %):

| Décimo | logistica | boosting |
|---|---|---|
| 1 | 10,1 → 10,2 | 11,0 → 9,3 |
| 2 | 13,3 → 9,7 | 13,7 → 11,5 |
| 3 | 15,6 → 13,2 | 16,1 → 13,8 |
| 4 | 18,2 → 16,0 | 19,1 → 15,4 |
| 5 | 21,0 → 17,9 | 22,0 → 19,6 |
| 6 | 23,6 → 19,9 | 24,4 → 20,5 |
| 7 | 26,1 → 24,1 | 26,9 → 20,7 |
| 8 | 28,9 → 25,7 | 29,7 → 24,5 |
| 9 | 33,2 → 27,4 | 33,8 → 26,6 |
| 10 | 45,8 → 40,3 | 45,0 → 42,6 |

## Hiperparámetros

Elegidos con el PR-AUC de validación. Con cualquier otro criterio esto se tiene que volver a correr antes de abrir prueba.

- **prevalencia**: tasa = 0,219
- **regla**: umbral_usd = 10000, parte_arriba = 0,061, tasa_arriba = 0,238, tasa_abajo = 0,217
- **logistica**: C = 0,030
- **boosting**: num_leaves = 31, min_child_samples = 50, reg_lambda = 0,000, categorias = fuerte, arboles = 92, learning_rate = 0,030

Grilla de **logistica** (validación):

| C | PR-AUC | ROC-AUC | Lift 20 % | Brier |
|---|---|---|---|---|
| 0.001 | 0,327 | 0,656 | 1,67 | 0,1561 |
| 0.003 | 0,336 | 0,656 | 1,69 | 0,1550 |
| 0.01 | 0,342 | 0,654 | 1,65 | 0,1545 |
| 0.03 | 0,342 | 0,652 | 1,66 | 0,1547 |
| 0.1 | 0,340 | 0,648 | 1,65 | 0,1557 |
| 0.3 | 0,336 | 0,644 | 1,65 | 0,1570 |
| 1.0 | 0,331 | 0,640 | 1,63 | 0,1585 |
| 3.0 | 0,329 | 0,638 | 1,64 | 0,1593 |

Grilla de **boosting** (validación):

| num_leaves | min_child_samples | reg_lambda | categorias | arboles | PR-AUC | ROC-AUC | Lift 20 % | Brier |
|---|---|---|---|---|---|---|---|---|
| 7 | 50 | 0.0 | suave | 69 | 0,338 | 0,642 | 1,65 | 0,1560 |
| 7 | 50 | 0.0 | fuerte | 146 | 0,342 | 0,645 | 1,65 | 0,1554 |
| 7 | 50 | 10.0 | suave | 136 | 0,338 | 0,641 | 1,67 | 0,1563 |
| 7 | 50 | 10.0 | fuerte | 147 | 0,341 | 0,646 | 1,65 | 0,1555 |
| 7 | 200 | 0.0 | suave | 82 | 0,340 | 0,642 | 1,66 | 0,1562 |
| 7 | 200 | 0.0 | fuerte | 146 | 0,341 | 0,645 | 1,67 | 0,1556 |
| 7 | 200 | 10.0 | suave | 136 | 0,336 | 0,640 | 1,65 | 0,1565 |
| 7 | 200 | 10.0 | fuerte | 149 | 0,341 | 0,646 | 1,67 | 0,1556 |
| 15 | 50 | 0.0 | suave | 69 | 0,340 | 0,643 | 1,66 | 0,1560 |
| 15 | 50 | 0.0 | fuerte | 69 | 0,346 | 0,648 | 1,71 | 0,1551 |
| 15 | 50 | 10.0 | suave | 65 | 0,339 | 0,642 | 1,68 | 0,1563 |
| 15 | 50 | 10.0 | fuerte | 94 | 0,344 | 0,646 | 1,66 | 0,1554 |
| 15 | 200 | 0.0 | suave | 69 | 0,341 | 0,643 | 1,66 | 0,1560 |
| 15 | 200 | 0.0 | fuerte | 80 | 0,344 | 0,648 | 1,66 | 0,1553 |
| 15 | 200 | 10.0 | suave | 69 | 0,338 | 0,643 | 1,69 | 0,1562 |
| 15 | 200 | 10.0 | fuerte | 99 | 0,344 | 0,649 | 1,68 | 0,1552 |
| 31 | 50 | 0.0 | suave | 65 | 0,341 | 0,643 | 1,67 | 0,1559 |
| 31 | 50 | 0.0 | fuerte | 92 | 0,346 | 0,649 | 1,69 | 0,1550 |
| 31 | 50 | 10.0 | suave | 72 | 0,340 | 0,645 | 1,68 | 0,1559 |
| 31 | 50 | 10.0 | fuerte | 102 | 0,344 | 0,649 | 1,68 | 0,1552 |
| 31 | 200 | 0.0 | suave | 69 | 0,340 | 0,641 | 1,67 | 0,1563 |
| 31 | 200 | 0.0 | fuerte | 88 | 0,344 | 0,649 | 1,70 | 0,1552 |
| 31 | 200 | 10.0 | suave | 69 | 0,338 | 0,642 | 1,66 | 0,1562 |
| 31 | 200 | 10.0 | fuerte | 86 | 0,344 | 0,650 | 1,69 | 0,1552 |

---

Generado por `modelo/escalera.py` (semilla 2023). Se regenera con `.venv/Scripts/python -m modelo.escalera`.
