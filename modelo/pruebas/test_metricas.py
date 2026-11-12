"""Pruebas de las metricas, con casos chicos de resultado conocido.

    py -m unittest discover -s modelo/pruebas -t .
"""
import unittest

import numpy as np

from modelo import metricas as M


class TestLift(unittest.TestCase):
    def test_sin_empates(self):
        y = np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 0])
        s = np.arange(10, 0, -1, dtype=float)        # ya ordenado de mayor a menor
        # el 20 % de arriba son 2 clientes: [1, 0] -> 50 % contra 20 % de prevalencia
        self.assertAlmostEqual(M.lift(y, s, 0.2), 2.5)
        self.assertAlmostEqual(M.captura(y, s, 0.2), 0.5)

    def test_todos_empatados_da_lo_mismo_que_el_azar(self):
        y = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0])
        s = np.full(10, 0.3)
        self.assertAlmostEqual(M.lift(y, s, 0.2), 1.0)
        self.assertAlmostEqual(M.captura(y, s, 0.2), 0.2)

    def test_empate_en_el_borde_cuenta_la_parte_que_entra(self):
        # el corte del 50 % (2 clientes) parte al grupo empatado en 0,5:
        # entra uno de sus dos clientes, y en promedio medio positivo.
        y = np.array([1, 1, 0, 0])
        s = np.array([0.9, 0.5, 0.5, 0.1])
        self.assertAlmostEqual(M.positivos_arriba(y, s, 0.5), 1.5)
        self.assertAlmostEqual(M.lift(y, s, 0.5), 1.5)

    def test_corte_no_entero(self):
        # n = 10, 25 % -> 2,5 clientes: los dos primeros y la mitad del tercero
        y = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
        s = np.arange(10, 0, -1, dtype=float)
        self.assertAlmostEqual(M.positivos_arriba(y, s, 0.25), 2.5)

    def test_no_depende_del_orden_de_las_filas(self):
        rng = np.random.default_rng(0)
        y = rng.integers(0, 2, 200)
        s = rng.integers(0, 5, 200).astype(float)    # muchos empates
        p = rng.permutation(200)
        self.assertAlmostEqual(M.lift(y, s, 0.1), M.lift(y[p], s[p], 0.1))


class TestIgualQueSklearn(unittest.TestCase):
    """ROC-AUC y PR-AUC se calculan a mano (mas rapido en el bootstrap): tienen que dar lo mismo."""

    def comparar(self, y, s):
        from sklearn.metrics import average_precision_score, roc_auc_score
        r = M.todas(y, s)
        self.assertAlmostEqual(r["roc_auc"], roc_auc_score(y, s), places=12)
        self.assertAlmostEqual(r["pr_auc"], average_precision_score(y, s), places=12)

    def test_sin_empates(self):
        rng = np.random.default_rng(4)
        y = rng.integers(0, 2, 1000)
        self.comparar(y, y * 0.2 + rng.uniform(0, 1, 1000))

    def test_con_muchos_empates(self):
        rng = np.random.default_rng(5)
        y = (rng.uniform(0, 1, 3000) < 0.2).astype(int)
        self.comparar(y, np.round(y * 0.1 + rng.uniform(0, 1, 3000), 1))

    def test_dos_valores_y_constante(self):
        y = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0])
        self.comparar(y, np.array([0.3, 0.3, 0.1, 0.1, 0.1, 0.3, 0.1, 0.1, 0.1, 0.1]))
        self.comparar(y, np.full(10, 0.2))


class TestProbabilidades(unittest.TestCase):
    def test_brier_de_la_prevalencia(self):
        y = np.array([1, 0, 0, 0, 0])
        self.assertAlmostEqual(M.brier(y, np.full(5, 0.2)), 0.16)

    def test_calibracion_reparte_todos_los_clientes(self):
        rng = np.random.default_rng(1)
        p = rng.uniform(0, 1, 1000)
        y = (rng.uniform(0, 1, 1000) < p).astype(int)
        tramos = M.calibracion(y, p, grupos=10)
        self.assertEqual(len(tramos), 10)
        self.assertEqual(sum(t["n"] for t in tramos), 1000)
        medias = [t["p_media"] for t in tramos]
        self.assertEqual(medias, sorted(medias))

    def test_calibracion_con_pocos_valores_distintos(self):
        y = np.array([1, 0, 0, 1, 0, 0])
        p = np.array([0.2, 0.2, 0.2, 0.4, 0.4, 0.4])
        tramos = M.calibracion(y, p, grupos=10)
        self.assertEqual([(t["n"], round(t["tasa"], 3)) for t in tramos], [(3, 0.333), (3, 0.333)])

    def test_pendiente_de_un_modelo_bien_calibrado(self):
        rng = np.random.default_rng(2)
        p = rng.uniform(0.05, 0.6, 20000)
        y = (rng.uniform(0, 1, 20000) < p).astype(int)
        a, b = M.recta_calibracion(y, p)
        self.assertAlmostEqual(b, 1.0, delta=0.1)
        self.assertAlmostEqual(a, 0.0, delta=0.1)

    def test_pendiente_de_un_puntaje_constante_no_existe(self):
        a, b = M.recta_calibracion(np.array([0, 1, 0, 0]), np.full(4, 0.25))
        self.assertTrue(np.isnan(b))


class TestBootstrap(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(3)
        self.y = rng.integers(0, 2, 500)
        self.bueno = self.y * 0.3 + rng.uniform(0, 1, 500)
        self.malo = rng.uniform(0, 1, 500)

    def test_un_modelo_contra_si_mismo_no_tiene_diferencia(self):
        r = M.bootstrap(self.y, {"a": self.bueno, "b": self.bueno.copy()},
                        pares=[("b", "a")], repeticiones=200, semilla=7)
        for metrica, d in r["diferencias"]["b - a"].items():
            self.assertEqual((d["desde"], d["hasta"]), (0.0, 0.0), metrica)

    def test_misma_semilla_mismo_resultado(self):
        args = dict(pares=[("bueno", "malo")], repeticiones=100, semilla=11)
        r1 = M.bootstrap(self.y, {"malo": self.malo, "bueno": self.bueno}, **args)
        r2 = M.bootstrap(self.y, {"malo": self.malo, "bueno": self.bueno}, **args)
        self.assertEqual(r1, r2)

    def test_el_intervalo_rodea_al_valor_y_detecta_al_mejor(self):
        r = M.bootstrap(self.y, {"malo": self.malo, "bueno": self.bueno},
                        pares=[("bueno", "malo")], repeticiones=300, semilla=5)
        auc = r["modelos"]["bueno"]["roc_auc"]
        self.assertLessEqual(auc["desde"], auc["valor"])
        self.assertLessEqual(auc["valor"], auc["hasta"])
        self.assertGreater(r["diferencias"]["bueno - malo"]["roc_auc"]["desde"], 0)


if __name__ == "__main__":
    unittest.main()
