# Uso del modelo

Qué da el modelo, qué necesita para dar un score a un cliente nuevo y qué está decidido al respecto. Estado al 2026-11-19.

## Qué hay

[`modelo/exportado/`](../modelo/exportado/) tiene, en JSON, el modelo principal y el reducido. Son dos de los siete que se evaluaron en la prueba:

| Archivo | Modelo | Variables |
|---|---|---|
| `principal.json` | Regresión logística principal, la que confirmó H1 | 29 |
| `reducido.json` | Regresión logística reducida: compañía previa, datos de contacto del día 0 y viaje | 12 |

Los dos están entrenados con la cohorte 2023 y recalibrados con la 2024, tal como se evaluaron. [`modelo/puntuar.py`](../modelo/puntuar.py) los aplica con Python estándar, sin instalar nada:

```
python modelo/puntuar.py modelo/exportado/principal.json entrada.csv salida.csv
```

Se verificó que reproducen las probabilidades del modelo original en los 13.595 clientes de validación (diferencia máxima de 3e-16), y que corren en una computadora sin numpy ni scikit-learn.

## Qué es el score

`prob_vuelve_12` es la probabilidad de que un cliente **nuevo** (en su primera compra) vuelva a comprar con Jetmar (para él o como pasajero en la compra de otro cliente) dentro de los 12 meses siguientes, para un viaje distinto del primero.

- **Solo para clientes en su primera compra.** No aplica a quien ya compró antes.
- **Sobreestima.** En la prueba (enero a agosto de 2025) predijo 23,9% en promedio y volvió el 20,8%. Sirve más para **ordenar** a quién contactar primero que como probabilidad exacta.
- **Mide propensión, no efecto.** Un score alto dice que el cliente tiende a volver, no que contactarlo lo haga volver.
- **El mail ya casi no separa.** `d0_tiene_mail` es la variable con mayor contribución en el modelo principal (SHAP) y también está en el reducido. Pero en 2025 se cargó al 94,7% de los clientes nuevos, contra el 42,7% en 2023, el año con que se entrenaron. A partir de 2025 el modelo le suma esa ventaja a casi todos, y por eso sobreestima. Para usarlo con clientes de hoy conviene reentrenarlo con datos recientes. Es un descriptivo posterior a la prueba: ver el registro de cambios, punto 13.

## Qué necesita la entrada

`puntuar.py` recibe filas en el formato de [`datos/tabla_modelo.csv`](../datos/DICCIONARIO.md): mismas columnas, bandas y categorías. **No recibe una ficha tal como sale del sistema de gestión.** Para puntuar un cliente nuevo hay que calcular antes sus variables del día 0 y pasarlas a ese formato. Las reglas de bandas y categorías están en [`exportacion/reglas.py`](../exportacion/reglas.py) y la conversión, en `fila_publica` de [`exportacion/anonimato.py`](../exportacion/anonimato.py).

**Ninguna variable sale de la ficha sola: todas necesitan la base.** La tabla dice de dónde sale cada una. «Timeline» es `gold.mart_jetuy_persona_timeline`: una fila por persona y ficha, con todo el historial del cliente desde 2019.

| Variable | De dónde sale | ¿Alcanza el timeline del cliente? |
|---|---|---|
| `fue_acompaniante_antes`, `viajes_previos_acompaniante` | fichas del cliente como pasajero, anteriores a su primera compra | sí |
| `pasajeros` | `total_pax` de la ficha (la mayor, si compró varias el mismo día) | sí |
| `venta_usd`, `venta_por_pasajero_usd` | `monto_venta_usd` de las fichas del día 0 | sí |
| `utilidad_indice` | `utilidad_usd` dividida por una constante interna (`secretos.json`, fuera del repo) | sí, con la constante |
| `tipo_producto`, `tiene_seguro` | columnas de la ficha | sí |
| `pais_destino`, `region_destino` | `destino_principal_pais`; la región, con la tabla de `reglas.py` | sí |
| `noches` | `fecha_regreso` − `fecha_viaje` | sí |
| `anticipacion` | `fecha_viaje` − `fecha_compra` | sí |
| `vendedor` | `vendedor_persona_id` (o `vendedor_cod`), pasado al código `V-xxx` con la correspondencia interna | sí, con la correspondencia |
| `viaja_con_cliente_previo`, `viaja_con_alguien_con_historial` | historial de **los acompañantes** de la ficha | **no**: el timeline del cliente trae los nombres de los acompañantes, no sus ids; hace falta el timeline de cada uno |
| `vendedor_fichas_12m`, `vendedor_antiguedad` | todas las fichas del vendedor | **no**: hace falta el timeline completo de Jetmar |
| `vendedor_es_persona` | `gold.dim_vendedor_codigo` | **no** |
| `d0_tiene_mail`, `d0_tiene_telefono`, `d0_tiene_documento`, `d0_tiene_nacimiento` | el registro de cliente usado en la primera compra: `gold.fact_ficha_persona` → `gold.mart_jetuy_persona_contactos` | **no** |
| `canje_millas`, `pagador` | `gold.fact_ficha_pagador` | **no** |
| `aerolinea`, `regimen_hotel`, `servicios` | `gold.mart_jetuy_ficha_servicio` | **no** en columnas propias. El timeline trae un campo `servicios` (jsonb) cuyo contenido actual no se verificó |
| `lleva_hotel`, `destinos` | `gold.fact_ficha` (`n_hoteles`, `n_destinos`) | **no** |

Además, para saber si el cliente entra en el universo del modelo:

- **Primera compra:** que no tenga una ficha anterior como titular. Esto sí sale del timeline.
- **Compra corporativa:** se mira en `fact_ficha.es_corporativa`, que no está en el timeline.
- **Edad:** que no sea menor de 18, según la fecha de nacimiento de `dim_persona`, que tampoco está en el timeline.

**En resumen:** del timeline del cliente salen 13 de las 29 variables del modelo principal y 5 de las 12 del reducido. El resto necesita las otras tablas de la tabla de arriba. Cómo se calcula todo para la tabla histórica está en [`exportacion/armar.py`](../exportacion/armar.py), que trabaja en lote sobre una foto de la base.

## Qué está decidido

- **2026-11-19 · no se arma, por ahora, el script para puntuar fichas nuevas desde la base.** Lo decidió el usuario. La indicación fue que la puntuación «se maneja con el timeline de un cliente». La tabla de arriba dice qué parte del modelo cubre eso.
- **Si se usa en la agencia:**
  - conviene reentrenarlo con todas las cohortes etiquetadas (2023 a agosto de 2025);
  - conviene recalibrarlo cada año, porque cambió la carga de datos de contacto (ver el registro de cambios, puntos 13 y 17).

  Las dos cosas serían análisis posteriores a la prueba y tienen que anotarse como tales. En la prueba, el modelo entrenado con 2023 + 2024 ordenó mejor que el entrenado solo con 2023: PR-AUC +0,013 [0,007; 0,019].
