# Instrucciones para sesiones de Claude en este repo

Arranque en frío: qué es el proyecto, qué leer y en qué orden, en qué estado está y qué reglas no se rompen. No repite contenido; dice dónde está.

## Qué es

Proyecto final de Aprendizaje Automático I: «¿Vuelve a viajar?». Busca predecir, el día de su primera compra, si un cliente nuevo de Jetmar (agencia de 5M Travel Group, Uruguay) vuelve a comprar con la agencia (para él o como pasajero en la compra de otro cliente) dentro de los 12 meses siguientes. El equipo son cuatro estudiantes. El que trabaja en la empresa y tiene acceso a la base es Agustín, el usuario de este repo.

## Qué leer, en este orden

1. [`HALLAZGOS.md`](HALLAZGOS.md): el resumen de todo, con índice de archivos y glosario.
2. [`docs/cambios_respecto_de_la_propuesta.md`](docs/cambios_respecto_de_la_propuesta.md): **la fuente de verdad** de decisiones, resultados y estado de las hipótesis. Si algo de la propuesta o de otro archivo lo contradice, manda este registro.
3. [`datos/DICCIONARIO.md`](datos/DICCIONARIO.md): las 40 columnas de la tabla y cómo se definió cada cosa.
4. [`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md) y [`modelo/resultados/prueba.md`](modelo/resultados/prueba.md): la evaluación final.
5. [`docs/uso_del_modelo.md`](docs/uso_del_modelo.md): qué da el modelo, qué necesita y qué está decidido sobre usarlo con clientes nuevos.

## Estado (2026-11-20)

**Hecho:**

- la tabla anonimizada y la exploración;
- la escalera de modelos, la recalibración y la interpretación para H2, todo en validación;
- **la prueba, corrida una sola vez:**
  - H1 confirmada;
  - H2 en parte;
  - H3: señal adicional incierta (registro de cambios, punto 21);
- los modelos exportados para usarlos en otra computadora;
- **el informe** (`informe/informe.pdf`, 6 páginas, el máximo de la consigna; se entrega el 23 de noviembre). Está escrito como evaluación retrospectiva entre cohortes (registro de cambios, punto 21). Se arma con `py informe/armar_informe.py`, que dibuja las figuras desde `modelo/resultados/` y necesita Playwright;
- **la presentación de la defensa** (`presentacion/`, 25 de noviembre): 20 minutos con cuatro oradores, estilo «postal» (viaje en ómnibus de Montevideo a Florianópolis; elegido entre tres bocetos en `presentacion/bocetos/`), más `GUION.md` y `GUIA.md` con preguntas probables. El PDF de respaldo se arma con `py presentacion/exportar_pdf.py`. El caso C-00412 es un cliente inventado, puntuado con el modelo exportado.

**No se versionan** (`.gitignore`, decisiones del usuario del 2026-11-20 y 2026-11-22): `informe/`, `presentacion/`, `consigna.pdf` y la página escrita de la propuesta (`PropuestaProyectoML_Grupo6.pdf`). Viven solo en la máquina del equipo; no se agregan a ningún commit.

**Decidido no hacer:** el script para puntuar fichas nuevas desde la base (decisión del usuario, 2026-11-19; ver `docs/uso_del_modelo.md`).

**Pendiente:** ensayar la defensa. Si cambia una cifra, se cambia el script o el resultado de origen y se vuelven a armar el informe y la presentación (ver `presentacion/GUIA.md`, «Si algo cambia»).

## Reglas que no se rompen

1. **El bloque de prueba ya se usó.** Son los clientes con primera compra entre enero y agosto de 2025, evaluados el 2026-11-19 con el plan versionado en el commit `69632ac`.
   - No se vuelve a elegir, ajustar ni comparar modelos nuevos con ese bloque como si fuera limpio.
   - Todo análisis nuevo que lo toque se anota como **posterior a la prueba**.
   - `modelo/prueba.py` se niega a correr de nuevo. No forzarlo: no borrar `modelo/resultados/prueba.json`.
   - [`docs/plan_de_la_prueba.md`](docs/plan_de_la_prueba.md) **no se edita**: es el registro de lo que se fijó antes de abrir la prueba. Si algo de su notación confunde, se aclara en otro documento.
   - Antes de abrir la prueba ya se conocían el tamaño del bloque y su tasa de vuelta (están en el manifiesto de la tabla). Decir «no se había entrenado ni evaluado ningún modelo con esos clientes», no «no se miró nada de 2025».
2. **Vocabulario.**
   - «Prueba» o «bloque de prueba» es ese conjunto de clientes de 2025. Las carpetas `exportacion/pruebas/` y `modelo/pruebas/` son **pruebas automáticas** del código (tests unitarios). No confundirlos.
   - «Ficha» es una compra en la base. «Ficha única» y «ficha del día 0» son los datos de contacto de una persona, hoy o en el registro de su primera compra.
   - «Vuelve a 12 meses»: la **compra** de vuelta cae dentro de los 12 meses, no necesariamente el viaje.
   - Detalle en el glosario de `HALLAZGOS.md`.
3. **Los datos no viajan.**
   - `datos/tabla_modelo.csv` no está en el repo ni en el zip de hallazgos, y no se versiona. Está anonimizada pero no es pública.
   - La foto de la base, la tabla de correspondencia de códigos y la constante de la utilidad viven solo en la máquina del usuario, fuera de OneDrive, y nunca entran al repo.
   - Al explorar datos de clientes, imprimir conteos y formatos, nunca valores personales.
4. **Los números de [`presentacion_propuesta.html`](presentacion_propuesta.html) están superados.**
   - La prevalencia es 21,9%, no «10 a 20».
   - Las cohortes son 2023 a agosto de 2025, no 2021 a 2025.
   - La regla de «10 mil USD» no le gana al azar.

   - El «≈1% de margen neto» de la diapositiva 2 no tiene fuente dentro del proyecto. No citarlo sin confirmarlo con el usuario.

   La propuesta sirve para comparar; las cifras vigentes están en el registro de cambios y en `modelo/resultados/`.
5. **Toda decisión o cambio respecto de la propuesta se anota en el registro de cambios,** con su medición, en el mismo paso en que se toma. El usuario lo pidió porque se usa en la defensa.
6. **Cómo se cita una cifra.** Va con su base de comparación y sin adjetivos que la valoren («el hallazgo más fuerte»). Lo preliminar o exploratorio se marca como tal. Cada cifra sale de un archivo de resultados (`modelo/resultados/*.json` o `.md`) o del registro; no se recalcula con otra definición.
7. **Vendedores:** no se listan ni se ordenan resultados por vendedor.
8. **Anonimato de la tabla:** cualquier cambio pasa por [`exportacion/reglas.py`](exportacion/reglas.py) y tiene que dejar `exportacion/03_verificar.py` en PASA.
9. **Los informes generados no se editan a mano.** Los `.md`, `.json` y `.png` de `modelo/resultados/` y `analisis/exploracion.html` salen de sus scripts. Para cambiarlos, se cambia el script y se vuelve a correr.

## Qué corre y qué no

**Sin la tabla** (por ejemplo, desde el zip de hallazgos):

- Todas las pruebas automáticas, que usan datos inventados:
  ```
  python -m unittest discover -s exportacion/pruebas -t .
  python -m unittest discover -s modelo/pruebas -t .
  ```
- `python modelo/puntuar.py <modelo.json> <entrada.csv> <salida.csv>`, con filas propias en el formato de la tabla.
- Leer todos los resultados.

**Con la tabla** copiada a `datos/` y verificada con `python exportacion/03_verificar.py`:

| Script | Tiempo |
|---|---|
| `modelo/escalera.py` | ~70 min |
| `modelo/recalibrar.py` | ~1 min |
| `modelo/interpretar.py` | ~6 min |
| `modelo/reducido.py` | ~1 min |
| `modelo/exportar.py` | segundos |
| `modelo/carga_contacto.py` (descriptivo posterior a la prueba; no elige nada) | segundos |
| `modelo/variables_solas.py` (cada variable sola en validación; exploratorio, no elige nada ni usa la prueba; no necesita CatBoost) | ~3 min |
| `modelo/campania_regla.py` (cómo llena la regla el cupo del 20% en la prueba; descriptivo posterior a la prueba) | segundos |

Cada script se niega a correr si la tabla no coincide con la huella de `datos/manifiesto.json`.

**Solo dentro de la empresa** (base de datos y VPN): `exportacion/01_tomar_foto.py` y `exportacion/02_armar_tabla.py`.

## Entorno

- **Python:** 3.14, con las versiones de [`requirements.txt`](requirements.txt).
- **Entorno virtual:** fuera del proyecto y fuera de OneDrive: adentro pesa unos 840 MB y el editor lo indexa.
- **En la máquina del usuario:**
  - el entorno del proyecto está en `C:\Users\apere\entornos\ml_vueltas`, con las versiones de `requirements.txt`; los scripts del modelo y las pruebas automáticas se corren con su `Scripts\python.exe`;
  - la terminal de VS Code activa ese entorno, así que `py` lo usa; tiene también Playwright, que necesitan `informe/armar_informe.py` y `presentacion/exportar_pdf.py` (Playwright no está en `requirements.txt` porque solo sirve para esos dos, que no se versionan);
  - `python` no responde.
- **Git:** no tiene identidad global configurada. Los commits van con `-c user.name=... -c user.email=...`. Los datos nunca se versionan.
- **Desde el zip de hallazgos** (no trae `.git`): el historial está en `HISTORIAL_GIT.txt` y en `repo.bundle`, que se recupera con `git clone repo.bundle ml_vueltas`. Ahí se ven las fechas del plan de la prueba (`69632ac`) y de sus resultados (`4fb21b8`).
