# La regla del acompañante con el cupo del 20% · *posterior a la prueba*

Generado por `modelo/campania_regla.py` el 2026-11-21. Tabla `77b71c49b21d…`. Descriptivo hecho **después** de correr la prueba, para respaldar cifras del informe. No entrena, no ajusta ni elige nada.

| | Prueba (enero a agosto de 2025) |
|---|---|
| Clientes | 10.148 |
| Vuelven | 2.109 |
| Cupo del 20% | 2029,6 plazas |
| Viajaron antes como acompañantes | 1.748 (vuelven 584) |
| Resto | 8.400 (vuelven 1.525) |
| Regla: vueltas en el cupo (esperadas) | 635,1 (30,1%) |
| Logística principal: vueltas en el cupo | 670 (31,8%) |

**Cómo llena el cupo la regla.** Toma a todos los acompañantes previos y completa las plazas con el resto; como ahí todos empatan, se cuenta lo esperado al desempatar al azar. Coincide con la captura de la regla en `prueba.json`.

**Diferencia de captura, logística − regla:** 1,65 puntos porcentuales [0,13; 3,02]. No es un cálculo nuevo: es la diferencia de lift al 20% declarada en el plan de la prueba (`prueba.json`), multiplicada por 0,20.
