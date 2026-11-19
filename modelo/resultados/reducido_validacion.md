# Modelo secundario: logística reducida · validación (cohorte 2024)

Generado por `modelo/reducido.py` el 2026-11-19. Tabla `77b71c49b21d…`. El bloque de prueba no se usó.

**Variables (12):** los grupos «H2 · compañía previa», «Datos de contacto (día 0)», «Viaje».

**Advertencia.** Los grupos se eligieron mirando validación (`interpretar.py`): los números de esta página son optimistas para el modelo reducido. La comparación que cuenta es la de la prueba.

C = 1,000, elegido por PR-AUC en validación cruzada de 5 pliegues dentro de entrenamiento (C=0.003: 0,349, C=0.01: 0,356, C=0.03: 0,359, C=0.1: 0,359, C=0.3: 0,359, C=1.0: 0,359).

| Modelo | PR-AUC | ROC-AUC | Lift 20% | Brier | Log-loss |
|---|---|---|---|---|---|
| Logística completa (principal) | 0,340 [0,323; 0,357] | 0,648 [0,637; 0,660] | 1,66 [1,58; 1,73] | 0,1556 [0,1521; 0,1594] | 0,4857 [0,4775; 0,4948] |
| Logística reducida | 0,342 [0,326; 0,361] | 0,651 [0,640; 0,662] | 1,67 [1,60; 1,74] | 0,1547 [0,1512; 0,1584] | 0,4837 [0,4756; 0,4924] |
| Reducida − completa | 0,002 [-0,004; 0,009] | 0,002 [-0,003; 0,008] | 0,014 [-0,048; 0,073] | -0,0009 [-0,0016; -0,0002] | -0,0019 [-0,0037; -0,0001] |

## Recalibración

Mismo criterio que el modelo principal: menor log-loss fuera de pliegue; el más simple si no es peor con intervalo.

| Método | Log-loss | ECE | Prob. media | Pendiente |
|---|---|---|---|---|
| Sin recalibrar | 0,4837 | 0,0349 | 23,9% | 0,99 |
| Intercepto | 0,4801 | 0,0075 | 20,4% | 0,99 |
| Platt | 0,4801 | 0,0067 | 20,4% | 1,00 |
| Isotónica | 0,4828 | 0,0088 | 20,4% | 0,91 |

Elegido: **Intercepto** (menor log-loss: Intercepto). Parámetros: `{"metodo": "intercepto", "b": -0.2152349150052863}`.
