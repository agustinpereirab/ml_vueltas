"""Pruebas de los escalones de la escalera. Datos inventados."""
import unittest

import numpy as np
import pandas as pd

from modelo import modelos


class Reglas(unittest.TestCase):
    def test_la_regla_predice_la_tasa_de_su_grupo_en_entrenamiento(self):
        g_ent = np.array([True, True, False, False, False])
        y_ent = np.array([1, 0, 1, 0, 0])
        p = modelos.regla(g_ent, y_ent, np.array([True, False]))
        np.testing.assert_allclose(p, [0.5, 1 / 3])

    def test_la_prevalencia_predice_la_tasa_de_entrenamiento_a_todos(self):
        p = modelos.prevalencia(np.array([1, 0, 0, 0]), 3)
        np.testing.assert_allclose(p, [0.25, 0.25, 0.25])


def sinteticos(n=600, semilla=0):
    r = np.random.default_rng(semilla)
    a = r.choice(["x", "y", "z", "sin_dato"], n)
    b = r.choice(["1", "0"], n)
    v = np.where(r.random(n) < 0.1, np.nan, r.gamma(2, 600, n))
    logit = -1.4 + 1.2 * (a == "x") + 0.8 * (b == "1") + 0.0004 * np.nan_to_num(v)
    y = (r.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame({"a": a, "b": b, "venta_usd": v}), y


class Logistica(unittest.TestCase):
    def test_aprende_y_tolera_categorias_nuevas_y_faltantes(self):
        x, y = sinteticos()
        ajuste = modelos.ajustar_logistica(x, y, ["a", "b"], ["venta_usd"], cs=(0.1, 1.0), semilla=1)
        nuevo = pd.DataFrame({"a": ["w", "x"], "b": ["1", "0"], "venta_usd": [np.nan, 900.0]})
        p = ajuste["modelo"].predict_proba(nuevo)[:, 1]
        self.assertEqual(p.shape, (2,))
        self.assertTrue(np.all((p > 0) & (p < 1)))
        self.assertIn(ajuste["C"], (0.1, 1.0))
        self.assertEqual(set(ajuste["cv"]), {0.1, 1.0})

    def test_ordena_mejor_que_el_azar_dentro_de_la_muestra(self):
        from sklearn.metrics import roc_auc_score
        x, y = sinteticos()
        ajuste = modelos.ajustar_logistica(x, y, ["a", "b"], ["venta_usd"], cs=(1.0,), semilla=1)
        self.assertGreater(roc_auc_score(y, ajuste["modelo"].predict_proba(x)[:, 1]), 0.65)


class CatBoost(unittest.TestCase):
    def test_elige_una_configuracion_y_predice_probabilidades(self):
        x, y = sinteticos()
        configs = [{"depth": 3, "l2_leaf_reg": 3}, {"depth": 4, "l2_leaf_reg": 10}]
        ajuste = modelos.ajustar_catboost(x, y, ["a", "b"], configs, semilla=1,
                                          iteraciones=150, tasa=0.1, pliegues=3)
        p = ajuste["modelo"].predict_proba(x.head(5))[:, 1]
        self.assertTrue(np.all((p > 0) & (p < 1)))
        self.assertIn(ajuste["params"]["depth"], (3, 4))
        self.assertGreaterEqual(ajuste["iteraciones"], 1)
        self.assertEqual(len(ajuste["cv"]), 2)


if __name__ == "__main__":
    unittest.main()
