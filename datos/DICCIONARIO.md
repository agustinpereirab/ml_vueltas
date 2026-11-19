# Diccionario de `tabla_modelo.csv`

Una fila por cliente nuevo de Jetmar, con lo que se sabía el día de su primera
compra y si volvió a viajar con la agencia dentro de los 12 meses siguientes.

- **37.398 clientes, 40 columnas.** Primera compra entre el 2023-01-01 y el 2025-08-31.
- **Sin datos personales.** No hay nombres, documentos, mails, teléfonos, fechas ni ids de la base. Todas las columnas tienen una lista cerrada de valores; no hay texto libre.
- **Fuente:** foto de la base tomada el 2026-11-11, con compras hasta el 2026-11-09.

## Cómo se define cada cosa

- **Cliente nuevo:** persona cuya primera ficha facturada como titular, mirando todo el historial desde 2019, cae en el período. Quien ya compraba antes de 2023 no entra.
- **Día 0:** la fecha de esa primera compra. Si ese día compró más de una ficha, se suman la venta y la utilidad, y el viaje se describe con la ficha de más pasajeros.
- **Quedan afuera:** quien entró con una compra corporativa y quien era menor de 18 años ese día.
- **`vuelve_12` = 1:** tiene otra ficha facturada, como titular o como pasajero, comprada después del día 0 y hasta 12 meses después, con fecha de viaje a más de 7 días de la del primer viaje. Una ficha con fecha de viaje a 7 días o menos se considera parte del mismo viaje.
- **Fichas en proceso:** no cuentan, ni como primera compra ni como vuelta.

Las cohortes 2021 y 2022 no están: Jetmar no tiene detalle de servicios (destino, producto, duración) antes de enero de 2023.

## Partición

| Columna | Entrenamiento | Validación | Prueba |
|---|---|---|---|
| `bloque` | cohorte 2023 · 13.655 | cohorte 2024 · 13.595 | enero a agosto de 2025 · 10.148 |
| `bloque_60_20_20` | hasta agosto de 2024 · 23.017 | septiembre de 2024 a febrero de 2025 · 6.551 | marzo a agosto de 2025 · 7.830 |

Con `bloque`, la etiqueta del último cliente de entrenamiento se cierra antes de que compre el primero de prueba. Con `bloque_60_20_20` eso no se cumple: las etiquetas de entrenamiento se cierran durante el período de prueba.

## Columnas

### Identificación y etiqueta

| Columna | Qué es | Valores |
|---|---|---|
| `cliente` | Código al azar, sin relación con el id de la base | `C-00001` … |
| `cohorte` | Año de la primera compra | 2023, 2024, 2025 |
| `bloque`, `bloque_60_20_20` | Partición (ver arriba) | entrenamiento, validacion, prueba |
| `vuelve_12` | **Etiqueta.** Vuelve a viajar dentro de los 12 meses | 0, 1 |
| `vuelve_12_comprando` | Etiqueta alternativa: vuelve como titular (paga) | 0, 1 |

### La compañía

| Columna | Qué es | Valores |
|---|---|---|
| `fue_acompaniante_antes` | Viajó con Jetmar como pasajero antes de su primera compra | 0, 1 |
| `viajes_previos_acompaniante` | Cuántas fichas tuvo así | 0, 1, 2, 3+ |
| `viaja_con_cliente_previo` | Alguno de sus acompañantes ya había comprado antes | 0, 1 |
| `viaja_con_alguien_con_historial` | Alguno de sus acompañantes ya había viajado o comprado antes | 0, 1 |
| `pasajeros` | Tamaño del grupo. En la interpretación del modelo (hipótesis 2) va en el grupo «viaje», no en «compañía previa» | 1, 2, 3, 4, 5-9, 10+, sin_dato |

### La compra

| Columna | Qué es | Valores |
|---|---|---|
| `venta_usd` | Venta del día 0, en dólares. Redondeada de a 50 hasta 1.000, de a 100 hasta 5.000, de a 500 hasta 20.000 y de a 1.000 después. Tope: 30.000 | entero o vacío |
| `venta_por_pasajero_usd` | Venta dividida por pasajeros, con el mismo redondeo. Tope: 10.000. En grupos de 5 a 9 se divide por 6; en grupos de 10 o más queda vacío | entero o vacío |
| `utilidad_indice` | Utilidad del día 0 dividida por una constante que no se publica. Sirve para comparar y ordenar, no para leer dólares. Entre −100 y 2.000 | entero |
| `canje_millas` | Pagó, en todo o en parte, con canje de millas | 0, 1 |
| `pagador` | Quién figura pagando | cliente, tercero, solo_millas, sin_dato |
| `tipo_producto` | Tipo de ficha | solo_aereo, aereo_hotel, paquete, solo_hotel, maritimo, otro, sin_dato |
| `tiene_seguro`, `lleva_hotel` | La compra incluye seguro / hotel | 0, 1 |
| `regimen_hotel` | Régimen del hotel | desayuno, solo_alojamiento, todo_incluido, pension, otro, sin_hotel, sin_dato |
| `aerolinea` | Aerolínea con más servicios en la compra | 11 aerolíneas, otra, sin_aereo, sin_dato |
| `servicios` | Cantidad de servicios, sin contar devoluciones | 1, 2, 3-4, 5-7, 8+ |

`maritimo` es sobre todo cruce por barco a Buenos Aires o Colonia, no cruceros.

### El viaje

| Columna | Qué es | Valores |
|---|---|---|
| `region_destino` | Región del destino principal | brasil, sudamerica, europa, caribe, norteamerica, asia_oceania_africa, uruguay, otro, sin_dato |
| `pais_destino` | País del destino principal | 14 países, otro, sin_dato |
| `destinos` | Cantidad de destinos | 1, 2, 3+, sin_dato |
| `noches` | Días entre la salida y el regreso | 0-3, 4-7, 8-14, 15+, sin_dato |
| `anticipacion` | Días entre la compra y el viaje | 0-7, 8-14, 15-30, 31-60, 61-90, 91-180, 181+, sin_dato |

`sudamerica` no incluye Brasil ni Uruguay. `caribe` incluye México y Centroamérica. `GE` es, en la base, sobre todo Alemania: Fráncfort, Múnich, Düsseldorf y Hamburgo, más unos pocos destinos de Georgia (Tiflis, Batumi). Berlín figura aparte como `DE` y en la tabla cae en «otro». Medido con ciudades de destino en la copia de septiembre de 2026: 641 fichas con `GE` y 260 con `DE`.

### El vendedor

| Columna | Qué es | Valores |
|---|---|---|
| `vendedor` | Código al azar. Los vendedores con menos de 50 clientes en la tabla van juntos en `V-otros` | `V-001` … `V-144`, `V-otros` |
| `vendedor_es_persona` | El código corresponde a una persona y no a un canal | 0, 1 |
| `vendedor_fichas_12m` | Fichas del vendedor en los 12 meses anteriores a la venta | 0-49, 50-149, 150-299, 300-499, 500+ |
| `vendedor_antiguedad` | Años desde su primera ficha. La base empieza en 2019: `4+` quiere decir «desde antes de 2020» | menos_de_1, 1-3, 4+, sin_dato |

**No ordenar ni publicar resultados por vendedor.** El código sirve como variable del modelo, no para comparar personas.

### Ficha única y ficha del día 0 (hipótesis 3)

| Columna | Qué es | Valores |
|---|---|---|
| `fu_tiene_mail`, `fu_tiene_telefono`, `fu_tiene_documento`, `fu_tiene_nacimiento` | El dato está cargado **hoy** en la ficha única de la persona o en cualquiera de sus registros | 0, 1 |
| `fu_registros` | Cuántos registros de la persona junta hoy la ficha única, en todas las marcas del grupo | 1, 2, 3+ |
| `d0_tiene_mail`, `d0_tiene_telefono`, `d0_tiene_documento`, `d0_tiene_nacimiento` | El dato está cargado en el registro que se usó en la primera compra | 0, 1 |

Las columnas `fu_` usan información posterior al día 0: son el brazo «con fuga». Las `d0_` son el brazo reconstruido. Si un dato está en `d0_`, está también en `fu_`.

Límite de la reconstrucción: el registro del día 0 se ve como está hoy. Si alguien completó un dato después sobre ese mismo registro, aparece como cargado el día 0.

## Qué se hizo para que no se pueda identificar a nadie

1. **Se armó una tabla nueva, no se copió la base.** Los nombres, documentos y demás datos de contacto nunca entraron al archivo; solo entró si estaban cargados o no.
2. **Códigos al azar.** No son un hash del id: sin la tabla de correspondencia, que queda dentro de la empresa, no hay forma de volver al id.
3. **Sin fechas.** Solo el año de la primera compra y bandas de anticipación y de noches.
4. **Montos redondeados y con tope.** La utilidad sale como índice.
5. **Grupos de al menos 5.** Cada combinación de cohorte, región, país, pasajeros, noches, tipo de producto y hotel aparece en 5 clientes o más. Es lo que alguien de afuera puede saber del viaje de un conocido. Se midió además con el año de viaje, que no se publica.
6. **Grupos de al menos 3 con más detalle.** Lo mismo sumando aerolínea, régimen del hotel y cantidad de destinos.
7. **Ninguna categoría con menos de 20 clientes.**
8. **Filas en orden de código**, que es al azar.

Para llegar a los puntos 5 y 6 se suprimieron valores en los clientes que quedaban en grupos chicos. **Un `sin_dato` puede querer decir «la base no lo trae» o «se suprimió»: conviene tratarlo como una categoría más.** Sobre las 37.398 filas:

| Columna | Sin dato | De eso, por supresión |
|---|---|---|
| `aerolinea` | 29,0% | todo |
| `destinos` | 22,9% | 16,0% |
| `regimen_hotel` | 19,7% | todo |
| `noches` | 12,2% | todo |
| `pais_destino` | 7,3% (y otro 7,6% pasó a `otro`) | 0,5% |
| `pasajeros` | 3,8% | 3,7% |
| `tipo_producto` | 0,7% | todo |

Además se retiraron 31 clientes que no llegaban a un grupo de 5 ni suprimiendo todo.

**Los conteos de supresión de `manifiesto.json`** no son por columna: cuentan las filas tocadas en cada paso del algoritmo, y una fila puede pasar por más de un paso.

- `prestadas`: filas de un grupo grande a las que se les suprimió el detalle para completar un grupo de al menos 3.
- `grupo_completo`: filas a las que se les suprimió el detalle porque ningún grupo podía prestar.

Los porcentajes por columna son los de la tabla de arriba.

### Límites

- La protección vale contra quien conoce un viaje desde afuera. **Quien tenga acceso a la base de Jetmar puede volver a cruzar la tabla**: mirando todas las columnas juntas, el 93,6% de las filas es única.
- Alguien que conozca del viaje más que lo listado en los puntos 5 y 6 (por ejemplo, el monto) puede achicar el grupo.
- Por eso la tabla no es pública: es para el equipo y los docentes.

## Lo que la presentación prometía y la tabla no trae

- **Mes de compra y de viaje, ciudad de destino:** son lo que más reidentifica.
- **Edad, género y nacionalidad:** multiplican los grupos chicos.
- **Categoría del hotel:** en la base es la categoría de la habitación y viene cargada en una parte menor de los hoteles.

## Cómo se regenera (solo dentro de la empresa)

```
python exportacion/01_tomar_foto.py     # foto mínima de la base, fuera de OneDrive
python exportacion/02_armar_tabla.py    # arma datos/tabla_modelo.csv
python exportacion/03_verificar.py      # la revisa; lo puede correr quien reciba la tabla
python analisis/graficas.py             # analisis/exploracion.html
python -m unittest discover -s exportacion/pruebas -t .   # pruebas automáticas (tests)
```

Las reglas de la tabla están en `exportacion/reglas.py`. Volver a correr el paso 2 sobre la misma foto da la misma tabla y los mismos códigos.
