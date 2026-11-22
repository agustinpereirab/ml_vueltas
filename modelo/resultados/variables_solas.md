# Cada variable sola · validación (cohorte 2024) · exploratorio

Generado por `modelo/variables_solas.py` el 2026-11-22. Tabla `77b71c49b21d…`. Descriptivo: no elige, no ajusta nada y no usa el bloque de prueba.

**Cómo se midió.** Para cada variable, la tasa de vuelta de cada valor se aprende con entrenamiento (2023) y se usa como puntaje en validación (2024); las numéricas, en quintiles de entrenamiento. Validación: 13.595 clientes, vuelve el 20,4%. ROC-AUC con intervalo bootstrap del 95% (2000 remuestreos). Azar: ROC-AUC 0,5; PR-AUC igual a la tasa de vuelta.

**Sobre r y r².** r es la correlación entre el puntaje y la vuelta (0 o 1). Con una etiqueta de sí o no, r² queda bajo aunque la variable ordene bien: no se lee como «porcentaje explicado». La medida que corresponde a la pregunta (ordenar a quién llamar) es la de orden.

| Variable | Grupo | ROC-AUC | PR-AUC | r | r² |
|---|---|---|---|---|---|
| Logística principal (29 variables) | modelo | 0,648 [0,637; 0,660] | 0,340 | 0,232 | 0,054 |
| Teléfono cargado el día 0 | Datos de contacto (día 0) | 0,590 [0,580; 0,600] | 0,242 | 0,145 | 0,021 |
| Mail cargado el día 0 | Datos de contacto (día 0) | 0,582 [0,573; 0,591] | 0,237 | 0,135 | 0,018 |
| Viajes previos como acompañante | H2 · compañía previa | 0,575 [0,566; 0,584] | 0,271 | 0,195 | 0,038 |
| Viajó antes como acompañante | H2 · compañía previa | 0,571 [0,562; 0,579] | 0,243 | 0,153 | 0,023 |
| Vendedor (código) | H2 · vendedor | 0,535 [0,522; 0,548] | 0,227 | 0,044 | 0,002 |
| Viaja con alguien con historial | H2 · compañía previa | 0,532 [0,522; 0,541] | 0,217 | 0,057 | 0,003 |
| Utilidad (índice) | Montos | 0,530 [0,519; 0,542] | 0,218 | 0,043 | 0,002 |
| Nacimiento cargado el día 0 | Datos de contacto (día 0) | 0,525 [0,518; 0,532] | 0,213 | 0,056 | 0,003 |
| Viaja con un cliente previo | H2 · compañía previa | 0,525 [0,516; 0,534] | 0,214 | 0,049 | 0,002 |
| Cantidad de destinos | Viaje | 0,525 [0,514; 0,537] | 0,214 | 0,037 | 0,001 |
| Antigüedad del vendedor | H2 · vendedor | 0,523 [0,512; 0,534] | 0,214 | 0,037 | 0,001 |
| Venta | Montos | 0,523 [0,511; 0,536] | 0,215 | 0,027 | 0,001 |
| Anticipación | Viaje | 0,522 [0,509; 0,534] | 0,216 | 0,025 | 0,001 |
| Aerolínea | Producto | 0,522 [0,510; 0,534] | 0,214 | 0,026 | 0,001 |
| Servicios | Producto | 0,520 [0,508; 0,532] | 0,212 | 0,029 | 0,001 |
| Régimen del hotel | Producto | 0,518 [0,507; 0,529] | 0,211 | 0,019 | 0,000 |
| Noches | Viaje | 0,518 [0,506; 0,529] | 0,213 | 0,028 | 0,001 |
| Pasajeros | Viaje | 0,517 [0,506; 0,528] | 0,212 | 0,027 | 0,001 |
| Tipo de producto | Producto | 0,516 [0,505; 0,527] | 0,213 | 0,022 | 0,000 |
| País de destino | H2 · destino | 0,514 [0,503; 0,526] | 0,211 | 0,020 | 0,000 |
| Venta por pasajero | Montos | 0,512 [0,500; 0,524] | 0,213 | 0,031 | 0,001 |
| Cartera del vendedor | H2 · vendedor | 0,511 [0,499; 0,522] | 0,209 | 0,020 | 0,000 |
| Lleva hotel | Producto | 0,511 [0,501; 0,521] | 0,208 | 0,018 | 0,000 |
| Seguro | Producto | 0,508 [0,499; 0,517] | 0,207 | 0,015 | 0,000 |
| Región de destino | H2 · destino | 0,507 [0,494; 0,519] | 0,211 | 0,001 | 0,000 |
| Canje de millas | Producto | 0,501 [0,491; 0,511] | 0,205 | 0,002 | 0,000 |
| Vendedor es persona | H2 · vendedor | 0,501 [0,500; 0,502] | 0,205 | 0,019 | 0,000 |
| Documento cargado el día 0 | Datos de contacto (día 0) | 0,500 [0,498; 0,502] | 0,205 | 0,001 | 0,000 |
| Quién pagó | Producto | 0,500 [0,496; 0,504] | 0,204 | 0,007 | 0,000 |
