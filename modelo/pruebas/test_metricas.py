"""Pruebas de las metricas. Datos inventados."""
import unittest

import numpy as np

from modelo import metricas as m


class TopK(unittest.TestCase):
    Y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_orden_perfecto_captura_todo_en_el_20_por_ciento(self):
        score = np.arange(10, 0, -1)
        self.assertAlmostEqual(m.tasa_en(self.Y, score, 0.2), 1.0)
        self.assertAlmostEqual(m.captura_en(self.Y, score, 0.2), 1.0)
        self.assertAlmostEqual(m.lift_en(self.Y, score, 0.2), 5.0)

    def test_puntaje_constante_es_como_elegir_al_azar(self):
        score = np.full(10, 0.3)
        self.assertAlmostEqual(m.tasa_en(self.Y, score, 0.2), 0.2)
        self.assertAlmostEqual(m.captura_en(self.Y, score, 0.2), 0.2)
        self.assertAlmostEqual(m.lift_en(self.Y, score, 0.2), 1.0)

    def test_los_empates_en_el_borde_se_reparten_en_proporcion(self):
        # el grupo de arriba tiene 4 clientes y 2 vuelven; el 10% es 1 cliente
        score = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
        self.assertAlmostEqual(m.tasa_en(self.Y, score, 0.1), 0.5)
        self.assertAlmostEqual(m.captura_en(self.Y, score, 0.1), 0.25)
        self.assertAlmostEqual(m.lift_en(self.Y, score, 0.1), 2.5)

    def test_el_orden_de_entrada_no_importa(self):
        r = np.random.default_rng(1)
        y = r.integers(0, 2, 200)
        s = r.random(200)
        i = r.permutation(200)
        self.assertAlmostEqual(m.lift_en(y, s, 0.2), m.lift_en(y[i], s[i], 0.2))


class Otras(unittest.TestCase):
    def test_brier(self):
        self.assertAlmostEqual(m.brier(np.array([1, 0]), np.array([0.8, 0.4])), (0.04 + 0.16) / 2)

    def test_calibracion_reparte_a_todos_en_grupos(self):
        r = np.random.default_rng(2)
        p = r.random(1000)
        y = (r.random(1000) < p).astype(int)
        tabla = m.calibracion(y, p, grupos=10)
        self.assertEqual(len(tabla), 10)
        self.assertEqual(sum(g["n"] for g in tabla), 1000)
        for g in tabla:
            self.assertLess(abs(g["p_media"] - g["observada"]), 0.15)

    def test_evaluar_trae_todas_las_metricas(self):
        r = np.random.default_rng(3)
        p = r.random(500)
        y = (r.random(500) < p).astype(int)
        e = m.evaluar(y, p)
        for clave in ("roc_auc", "pr_auc", "lift_10", "lift_20", "captura_10", "captura_20",
                      "brier", "p_media", "tasa_observada"):
            self.assertIn(clave, e)
        self.assertGreater(e["roc_auc"], 0.6)


class Bootstrap(unittest.TestCase):
    def setUp(self):
        r = np.random.default_rng(4)
        self.p = r.random(800)
        self.y = (r.random(800) < self.p).astype(int)
        self.ruido = r.random(800)

    def correr(self, semilla=7):
        return m.bootstrap(self.y, {"a": self.p, "b": self.p, "azar": self.ruido},
                           {"roc_auc": m.roc_auc, "lift_20": lambda y, s: m.lift_en(y, s, 0.2)},
                           pares=[("b", "a"), ("a", "azar")], repeticiones=300, semilla=semilla)

    def test_mismo_modelo_dos_veces_da_diferencia_cero(self):
        d = self.correr()["diferencias"]["b - a"]["roc_auc"]
        self.assertEqual((d["punto"], d["desde"], d["hasta"]), (0.0, 0.0, 0.0))

    def test_el_intervalo_contiene_al_valor_puntual(self):
        r = self.correr()
        for modelo, mets in r["modelos"].items():
            for nombre, v in mets.items():
                self.assertLessEqual(v["desde"], v["punto"], (modelo, nombre))
                self.assertGreaterEqual(v["hasta"], v["punto"], (modelo, nombre))

    def test_un_modelo_mejor_que_el_azar_tiene_diferencia_positiva_con_intervalo(self):
        d = self.correr()["diferencias"]["a - azar"]["roc_auc"]
        self.assertGreater(d["desde"], 0)

    def test_misma_semilla_mismo_resultado(self):
        self.assertEqual(self.correr(7), self.correr(7))


if __name__ == "__main__":
    unittest.main()
