"""Los escalones de la escalera: prevalencia, regla simple, logistica y CatBoost.

Los hiperparametros se eligen con validacion cruzada DENTRO del bloque de
entrenamiento. Asi la validacion (2024) queda limpia para comparar escalones,
y la prueba (2025) para el final.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


def prevalencia(y_ent, n):
    """Escalon 0: a todos la tasa de vuelta de entrenamiento."""
    return np.full(n, float(np.mean(y_ent)))


def regla(grupo_ent, y_ent, grupo_val):
    """Escalon 1: una regla de si/no. Cada cliente recibe la tasa de vuelta que
    tuvo su grupo en entrenamiento, para poder medir tambien la calibracion."""
    grupo_ent = np.asarray(grupo_ent, dtype=bool)
    y_ent = np.asarray(y_ent, dtype=float)
    tasa_si = y_ent[grupo_ent].mean()
    tasa_no = y_ent[~grupo_ent].mean()
    return np.where(np.asarray(grupo_val, dtype=bool), tasa_si, tasa_no)


def _logistica(cats, nums, C):
    numericas = Pipeline([
        ("asinh", FunctionTransformer(np.arcsinh, feature_names_out="one-to-one")),
        ("imputar", SimpleImputer(strategy="median", add_indicator=True)),
        ("escalar", StandardScaler()),
    ])
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cats),
        ("num", numericas, nums),
    ])
    return Pipeline([("pre", pre), ("modelo", LogisticRegression(C=C, max_iter=5000))])


def ajustar_logistica(x, y, cats, nums, cs, semilla, pliegues=5):
    """Escalon 2: regresion logistica con L2. Las categoricas van en one-hot y
    las numericas pasan por asinh (los montos tienen cola larga), imputacion por
    mediana con indicador de faltante y estandarizacion. C se elige por PR-AUC
    en validacion cruzada estratificada dentro de entrenamiento."""
    folds = StratifiedKFold(pliegues, shuffle=True, random_state=semilla)
    cv = {C: float(cross_val_score(_logistica(cats, nums, C), x, y, cv=folds,
                                   scoring="average_precision").mean())
          for C in cs}
    mejor = max(cv, key=cv.get)
    return {"modelo": _logistica(cats, nums, mejor).fit(x, y), "C": mejor, "cv": cv}


class _CatBoost:
    """Envuelve el modelo para que reciba la tabla tal como sale de `datos`."""

    def __init__(self, modelo, cats):
        self.modelo = modelo
        self.cats = cats

    def _preparar(self, x):
        x = x.copy()
        for c in self.cats:
            x[c] = x[c].astype(str).astype(object)
        return x

    def predict_proba(self, x):
        return self.modelo.predict_proba(self._preparar(x))


def ajustar_catboost(x, y, cats, configs, semilla, iteraciones=2000, tasa=0.05, pliegues=5):
    """Escalon 3: gradient boosting con CatBoost, que maneja las categoricas
    sin one-hot. Para cada configuracion, la cantidad de arboles sale de la
    parada temprana sobre la log-loss en validacion cruzada; entre
    configuraciones gana la de mayor PR-AUC en esa misma validacion cruzada."""
    # CatBoost se importa aca: los scripts que solo usan la logistica corren sin el
    from catboost import CatBoostClassifier, Pool, cv as catboost_cv
    preparar = _CatBoost(None, cats)._preparar
    pool = Pool(preparar(x), y, cat_features=cats)
    resultados = []
    for cfg in configs:
        params = {"loss_function": "Logloss", "custom_metric": ["PRAUC", "AUC"],
                  "iterations": iteraciones, "learning_rate": tasa, "random_seed": semilla,
                  "allow_writing_files": False, "logging_level": "Silent", **cfg}
        r = catboost_cv(pool, params, fold_count=pliegues, stratified=True, shuffle=True,
                        seed=semilla, early_stopping_rounds=100, plot=False)
        col_pr = next(c for c in r.columns if c.startswith("test-PRAUC") and c.endswith("-mean"))
        mejor = int(r["test-Logloss-mean"].idxmin())
        resultados.append({"config": cfg, "iteraciones": int(r.loc[mejor, "iterations"]) + 1,
                           "pr_auc_cv": float(r.loc[mejor, col_pr]),
                           "logloss_cv": float(r.loc[mejor, "test-Logloss-mean"])})
    elegido = max(resultados, key=lambda r: r["pr_auc_cv"])
    params = {"loss_function": "Logloss", "learning_rate": tasa, "random_seed": semilla,
              "allow_writing_files": False, "logging_level": "Silent", **elegido["config"]}
    modelo = CatBoostClassifier(iterations=elegido["iteraciones"], **params)
    modelo.fit(preparar(x), y, cat_features=cats)
    return {"modelo": _CatBoost(modelo, cats), "params": {**elegido["config"], "learning_rate": tasa},
            "iteraciones": elegido["iteraciones"], "cv": resultados}
