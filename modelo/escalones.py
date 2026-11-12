"""Los cuatro escalones de la escalera, de menos a mas complejo.

Cada uno se ajusta con entrenamiento y, si tiene hiperparametros, los elige
mirando validacion. Todos devuelven una probabilidad, asi Brier y la
calibracion se pueden comparar entre escalones:

1. prevalencia: a todos la tasa de entrenamiento ("predecir que nadie vuelve"
   con la exactitud de corte 0,5; el piso de cualquier metrica de orden).
2. regla: venta del dia 0 por encima de 10.000 USD => vuelve. A cada lado
   del umbral, la tasa de entrenamiento de ese lado.
3. logistica: regresion logistica L2 con one-hot; se elige C en validacion.
4. boosting: LightGBM con categoricas nativas; se eligen la forma de los
   arboles en validacion y la cantidad con parada temprana (log-loss) en
   validacion.

Con cualquier hiperparametro elegido en validacion, la metrica de validacion
de ese modelo sale algo optimista. Por eso la medida final es la de prueba.
"""
import lightgbm as lgb
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from modelo import metricas as M
from modelo.datos import NUMERICAS

SEMILLA = 2023
CRITERIO = "pr_auc"            # con que se eligen los hiperparametros


def signo_log1p(x):
    return np.sign(x) * np.log1p(np.abs(x))


class Prevalencia:
    nombre = "prevalencia"
    descripcion = "A todos la tasa de vuelta de entrenamiento"

    def ajustar(self, X, y, X_val=None, y_val=None):
        self.tasa = float(np.mean(y))
        self.elegido = {"tasa": self.tasa}
        return self

    def probabilidad(self, X):
        return np.full(len(X), self.tasa)


class ReglaVenta:
    nombre = "regla"
    umbral = 10000
    descripcion = "Venta del día 0 por encima de 10.000 USD ⇒ vuelve"

    def _arriba(self, X):
        return (X["venta_usd"] > self.umbral).to_numpy()   # NaN cuenta como abajo

    def ajustar(self, X, y, X_val=None, y_val=None):
        arriba = self._arriba(X)
        self.tasa_arriba = float(np.mean(y[arriba]))
        self.tasa_abajo = float(np.mean(y[~arriba]))
        self.elegido = {"umbral_usd": self.umbral, "parte_arriba": float(arriba.mean()),
                        "tasa_arriba": self.tasa_arriba, "tasa_abajo": self.tasa_abajo}
        return self

    def probabilidad(self, X):
        return np.where(self._arriba(X), self.tasa_arriba, self.tasa_abajo)


class Logistica:
    nombre = "logistica"
    descripcion = "Regresión logística L2, categóricas en one-hot"
    GRILLA_C = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0]

    def _armar(self, C, columnas):
        numericas = Pipeline([
            ("log", FunctionTransformer(signo_log1p, feature_names_out="one-to-one")),
            ("imputa", SimpleImputer(strategy="median", add_indicator=True)),
            ("escala", StandardScaler()),
        ])
        previo = ColumnTransformer([
            ("num", numericas, [c for c in columnas if c in NUMERICAS]),
            ("cat", OneHotEncoder(handle_unknown="ignore"),
             [c for c in columnas if c not in NUMERICAS]),
        ])
        return Pipeline([("previo", previo), ("lr", LogisticRegression(C=C, max_iter=5000))])

    def ajustar(self, X, y, X_val, y_val):
        self.grilla = []
        mejor = None
        for C in self.GRILLA_C:
            m = self._armar(C, list(X.columns)).fit(X, y)
            r = M.todas(y_val, m.predict_proba(X_val)[:, 1])
            self.grilla.append({"C": C, **r})
            if mejor is None or r[CRITERIO] > mejor[0]:
                mejor = (r[CRITERIO], C, m)
        _, self.C, self.modelo = mejor
        self.elegido = {"C": self.C}
        return self

    def probabilidad(self, X):
        return self.modelo.predict_proba(X)[:, 1]


class Boosting:
    nombre = "boosting"
    descripcion = "LightGBM, categóricas nativas"
    # La parada temprana mira el log-loss de validacion: con el PR-AUC, que es
    # escalonado y ruidoso, cortaba a los 8-36 arboles con el modelo a medio
    # ajustar (probabilidades comprimidas, peor Brier).
    BASE = dict(objective="binary", metric="binary_logloss", learning_rate=0.03,
                n_estimators=3000, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                max_cat_to_onehot=8, random_state=SEMILLA, deterministic=True,
                force_row_wise=True, n_jobs=4, verbose=-1)
    # Cuanto se suavizan las categoricas de muchos valores (vendedor, pais,
    # aerolinea) antes de cortar por ellas.
    CATEGORIAS = {"suave": dict(cat_smooth=20, min_data_per_group=50, cat_l2=10),
                  "fuerte": dict(cat_smooth=50, min_data_per_group=200, cat_l2=20)}
    GRILLA = [{"num_leaves": h, "min_child_samples": m, "reg_lambda": l, "categorias": c}
              for h in (7, 15, 31) for m in (50, 200) for l in (0.0, 10.0)
              for c in ("suave", "fuerte")]
    PACIENCIA = 100

    def _parametros(self, g):
        g = dict(g)
        return {**self.BASE, **self.CATEGORIAS[g.pop("categorias")], **g}

    def ajustar(self, X, y, X_val, y_val):
        self.grilla = []
        mejor = None
        for g in self.GRILLA:
            m = lgb.LGBMClassifier(**self._parametros(g))
            m.fit(X, y, eval_X=(X_val,), eval_y=(y_val,),
                  callbacks=[lgb.early_stopping(self.PACIENCIA, first_metric_only=True,
                                                verbose=False)])
            r = M.todas(y_val, m.predict_proba(X_val)[:, 1])
            self.grilla.append({**g, "arboles": int(m.best_iteration_), **r})
            if mejor is None or r[CRITERIO] > mejor[0]:
                mejor = (r[CRITERIO], g, m)
        _, g, self.modelo = mejor
        self.elegido = {**g, "arboles": int(self.modelo.best_iteration_),
                        "learning_rate": self.BASE["learning_rate"]}
        return self

    def probabilidad(self, X):
        return self.modelo.predict_proba(X)[:, 1]


ESCALERA = [Prevalencia, ReglaVenta, Logistica, Boosting]
