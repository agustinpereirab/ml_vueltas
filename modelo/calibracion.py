"""Recalibracion de las probabilidades de un modelo ya entrenado.

Cuatro metodos, de menos a mas flexible:

- `identidad`: no cambia nada.
- `intercepto`: corre todas las probabilidades en la escala logit, lo justo
  para que la probabilidad media iguale la tasa observada.
- `platt`: corrimiento y pendiente en la escala logit,
  sigmoide(a * logit(p) + b). Con a < 1 achica las probabilidades extremas.
- `isotonica`: una funcion escalonada creciente, sin forma fija.

Los tres primeros no cambian el orden de los clientes: AUC y lift quedan
iguales. La isotonica puede crear empates.

Cada metodo guarda sus parametros en un dict serializable a JSON, para
aplicarlo despues a la prueba sin volver a tocar la validacion.
"""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold

EPS = 1e-9


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def sigmoide(z):
    return 1 / (1 + np.exp(-np.clip(np.asarray(z, dtype=float), -35, 35)))


def newton(x, y, desplazamiento=0.0, iteraciones=100):
    """Regresion logistica sin regularizacion, por Newton-Raphson.
    `x` es la matriz de diseno (n x k); devuelve los k coeficientes."""
    y = np.asarray(y, dtype=float)
    beta = np.zeros(x.shape[1])
    for _ in range(iteraciones):
        p = sigmoide(x @ beta + desplazamiento)
        w = p * (1 - p)
        paso = np.linalg.solve(x.T @ (x * w[:, None]), x.T @ (y - p))
        beta = beta + paso
        if np.max(np.abs(paso)) < 1e-12:
            break
    return beta


class Identidad:
    nombre = "identidad"

    def fit(self, p, y):
        return self

    def predict(self, p):
        return np.asarray(p, dtype=float)

    def parametros(self):
        return {"metodo": self.nombre}

    @classmethod
    def desde(cls, d):
        return cls()


class Intercepto:
    nombre = "intercepto"

    def fit(self, p, y):
        z = logit(p)
        self.b = float(newton(np.ones((len(z), 1)), y, desplazamiento=z)[0])
        return self

    def predict(self, p):
        return sigmoide(logit(p) + self.b)

    def parametros(self):
        return {"metodo": self.nombre, "b": self.b}

    @classmethod
    def desde(cls, d):
        c = cls()
        c.b = float(d["b"])
        return c


class Platt:
    nombre = "platt"

    def fit(self, p, y):
        z = logit(p)
        a, b = newton(np.column_stack([z, np.ones(len(z))]), y)
        self.a, self.b = float(a), float(b)
        return self

    def predict(self, p):
        return sigmoide(self.a * logit(p) + self.b)

    def parametros(self):
        return {"metodo": self.nombre, "a": self.a, "b": self.b}

    @classmethod
    def desde(cls, d):
        c = cls()
        c.a, c.b = float(d["a"]), float(d["b"])
        return c


class Isotonica:
    nombre = "isotonica"

    def fit(self, p, y):
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(p, y)
        self.x = [float(v) for v in iso.X_thresholds_]
        self.y = [float(v) for v in iso.y_thresholds_]
        return self

    def predict(self, p):
        return np.interp(np.asarray(p, dtype=float), self.x, self.y)

    def parametros(self):
        return {"metodo": self.nombre, "x": self.x, "y": self.y}

    @classmethod
    def desde(cls, d):
        c = cls()
        c.x, c.y = list(d["x"]), list(d["y"])
        return c


METODOS = {c.nombre: c for c in (Identidad, Intercepto, Platt, Isotonica)}
ORDEN = ["identidad", "intercepto", "platt", "isotonica"]


def desde_parametros(d):
    return METODOS[d["metodo"]].desde(d)


def fuera_de_pliegue(p, y, metodo, pliegues=5, semilla=0):
    """Probabilidades recalibradas en las que cada cliente se calibro con un
    ajuste hecho sobre los OTROS pliegues."""
    p = np.asarray(p, dtype=float)
    y = np.asarray(y)
    salida = np.empty_like(p)
    for ajuste, aplicar in StratifiedKFold(pliegues, shuffle=True, random_state=semilla).split(p, y):
        salida[aplicar] = METODOS[metodo]().fit(p[ajuste], y[ajuste]).predict(p[aplicar])
    return salida


def elegir(puntual, contra_mejor, orden=ORDEN):
    """El metodo de menor perdida, salvo que uno mas simple no sea peor con
    intervalo: entonces el mas simple. `contra_mejor[m]` = (desde, hasta) del
    intervalo de (perdida de m - perdida del mejor)."""
    mejor = min(puntual, key=puntual.get)
    candidatos = [m for m in orden if m == mejor or (m in contra_mejor and contra_mejor[m][0] <= 0)]
    return candidatos[0]
