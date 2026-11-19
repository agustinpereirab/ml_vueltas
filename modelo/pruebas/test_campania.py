"""Pruebas de la simulacion de campania. Datos inventados."""
import unittest

import numpy as np

from modelo import campania


class Simulacion(unittest.TestCase):
    Y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_orden_perfecto_contacta_a_todos_los_que_vuelven(self):
        r = campania.simular(self.Y, np.arange(10, 0, -1), frac=0.2)
        self.assertEqual(r["contactados"], 2)
        self.assertAlmostEqual(r["vuelven_contactados"], 2)
        self.assertAlmostEqual(r["captura"], 1.0)
        self.assertAlmostEqual(r["lift"], 5.0)
        self.assertAlmostEqual(r["vuelven_contactados_azar"], 0.4)

    def test_puntaje_constante_es_igual_al_azar(self):
        r = campania.simular(self.Y, np.ones(10), frac=0.2)
        self.assertAlmostEqual(r["vuelven_contactados"], r["vuelven_contactados_azar"])
        self.assertAlmostEqual(r["lift"], 1.0)

    def test_el_valor_capturado_suma_el_valor_de_los_que_vuelven_entre_los_contactados(self):
        valor = np.array([100, 300, 50, 50, 50, 50, 50, 50, 50, 50])
        r = campania.simular(self.Y, np.arange(10, 0, -1), frac=0.1, valor=valor)
        # contacta solo al primero: vuelve y vale 100 de los 400 de los que vuelven
        self.assertAlmostEqual(r["valor_capturado"], 0.25)
        self.assertAlmostEqual(r["valor_capturado_azar"], 0.1)

    def test_curva_de_captura(self):
        c = campania.curva(self.Y, np.arange(10, 0, -1), pasos=(0.1, 0.2, 0.5))
        self.assertEqual([round(x["captura"], 6) for x in c], [0.5, 1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
