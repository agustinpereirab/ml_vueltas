"""Pruebas de la recalibracion. Datos inventados."""
import json
import unittest

import numpy as np

from modelo import calibracion as cal
from modelo import metricas as m


def sinteticos(n=20000, a=0.6, b=-0.4, semilla=0):
    """Un modelo que ordena bien pero exagera: la probabilidad real es
    sigmoid(a * logit(p_modelo) + b)."""
    r = np.random.default_rng(semilla)
    p = 1 / (1 + np.exp(-r.normal(-1.2, 1.1, n)))
    real = cal.sigmoide(a * cal.logit(p) + b)
    y = (r.random(n) < real).astype(int)
    return p, y


class Metodos(unittest.TestCase):
    def test_identidad_no_cambia_nada(self):
        p, y = sinteticos(2000)
        np.testing.assert_array_equal(cal.Identidad().fit(p, y).predict(p), p)

    def test_intercepto_iguala_la_probabilidad_media_a_la_tasa_observada(self):
        p, y = sinteticos()
        q = cal.Intercepto().fit(p, y).predict(p)
        self.assertAlmostEqual(q.mean(), y.mean(), places=6)

    def test_platt_recupera_pendiente_y_corrimiento(self):
        p, y = sinteticos(60000)
        c = cal.Platt().fit(p, y)
        self.assertAlmostEqual(c.a, 0.6, delta=0.05)
        self.assertAlmostEqual(c.b, -0.4, delta=0.07)

    def test_isotonica_es_monotona_y_queda_entre_0_y_1(self):
        p, y = sinteticos(5000)
        q = cal.Isotonica().fit(p, y).predict(np.sort(p))
        self.assertTrue(np.all(np.diff(q) >= 0))
        self.assertTrue(np.all((q >= 0) & (q <= 1)))

    def test_intercepto_y_platt_no_cambian_el_orden(self):
        p, y = sinteticos(5000)
        for metodo in (cal.Intercepto, cal.Platt):
            q = metodo().fit(p, y).predict(p)
            self.assertAlmostEqual(m.roc_auc(y, q), m.roc_auc(y, p), places=12)

    def test_los_parametros_se_guardan_en_json_y_reproducen_las_predicciones(self):
        p, y = sinteticos(5000)
        for metodo in cal.METODOS.values():
            c = metodo().fit(p, y)
            copia = cal.desde_parametros(json.loads(json.dumps(c.parametros())))
            np.testing.assert_allclose(copia.predict(p), c.predict(p), rtol=1e-12, atol=1e-12)


class FueraDePliegue(unittest.TestCase):
    def test_cada_cliente_se_calibra_con_un_ajuste_que_no_lo_vio(self):
        p, y = sinteticos(3000)
        oof = cal.fuera_de_pliegue(p, y, "intercepto", pliegues=5, semilla=1)
        dentro = cal.Intercepto().fit(p, y).predict(p)
        self.assertEqual(oof.shape, p.shape)
        self.assertFalse(np.allclose(oof, dentro))

    def test_misma_semilla_mismo_resultado(self):
        p, y = sinteticos(3000)
        np.testing.assert_array_equal(cal.fuera_de_pliegue(p, y, "platt", 5, 3),
                                      cal.fuera_de_pliegue(p, y, "platt", 5, 3))


class Eleccion(unittest.TestCase):
    ORDEN = ["identidad", "intercepto", "platt", "isotonica"]

    def test_gana_la_de_menor_perdida_si_las_mas_simples_son_peores_con_intervalo(self):
        puntual = {"identidad": 0.50, "intercepto": 0.48, "platt": 0.45, "isotonica": 0.46}
        contra_mejor = {"identidad": (0.03, 0.06), "intercepto": (0.01, 0.04), "isotonica": (-0.01, 0.03)}
        self.assertEqual(cal.elegir(puntual, contra_mejor, self.ORDEN), "platt")

    def test_si_una_mas_simple_no_es_peor_con_intervalo_gana_la_mas_simple(self):
        puntual = {"identidad": 0.50, "intercepto": 0.451, "platt": 0.45, "isotonica": 0.46}
        contra_mejor = {"identidad": (0.03, 0.06), "intercepto": (-0.002, 0.004), "isotonica": (-0.01, 0.03)}
        self.assertEqual(cal.elegir(puntual, contra_mejor, self.ORDEN), "intercepto")

    def test_si_no_recalibrar_no_es_peor_no_se_recalibra(self):
        puntual = {"identidad": 0.451, "intercepto": 0.45, "platt": 0.452, "isotonica": 0.46}
        contra_mejor = {"identidad": (-0.001, 0.003), "platt": (-0.001, 0.005), "isotonica": (0.0, 0.02)}
        self.assertEqual(cal.elegir(puntual, contra_mejor, self.ORDEN), "identidad")


class MetricasDeCalibracion(unittest.TestCase):
    def test_log_loss(self):
        self.assertAlmostEqual(m.log_loss(np.array([1, 0]), np.array([0.8, 0.4])),
                               -(np.log(0.8) + np.log(0.6)) / 2)

    def test_ece_es_casi_cero_si_esta_calibrado_y_grande_si_exagera(self):
        p, y = sinteticos(60000, a=1.0, b=0.0)
        self.assertLess(m.ece(y, p), 0.01)
        p, y = sinteticos(60000, a=0.5, b=-0.5)
        self.assertGreater(m.ece(y, p), 0.03)

    def test_pendiente_e_intercepto(self):
        p, y = sinteticos(60000, a=1.0, b=0.0)
        pendiente, intercepto = m.pendiente_e_intercepto(y, p)
        self.assertAlmostEqual(pendiente, 1.0, delta=0.05)
        self.assertAlmostEqual(intercepto, 0.0, delta=0.05)
        p, y = sinteticos(60000, a=0.6, b=-0.4)
        pendiente, intercepto = m.pendiente_e_intercepto(y, p)
        self.assertAlmostEqual(pendiente, 0.6, delta=0.05)


if __name__ == "__main__":
    unittest.main()
