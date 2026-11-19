"""Pruebas de la carga de la tabla y de los brazos de variables. Datos inventados."""
import csv
import os
import tempfile
import unittest

import numpy as np

from exportacion import reglas
from modelo import datos


def fila(i, bloque):
    f = {c: "0" for c in reglas.COLUMNAS}
    f.update({"cliente": "C-%05d" % i, "cohorte": {"entrenamiento": "2023", "validacion": "2024",
                                                    "prueba": "2025"}[bloque],
              "bloque": bloque, "bloque_60_20_20": bloque, "vuelve_12": str(i % 2),
              "pasajeros": "2", "venta_usd": "1200" if i % 3 else "", "venta_por_pasajero_usd": "600",
              "utilidad_indice": "95", "vendedor": "V-001", "pais_destino": "BR"})
    return f


class Carga(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ruta = os.path.join(cls.tmp.name, "tabla.csv")
        with open(cls.ruta, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=reglas.COLUMNAS)
            w.writeheader()
            for i, b in enumerate(["entrenamiento"] * 6 + ["validacion"] * 4 + ["prueba"] * 3):
                w.writerow(fila(i, b))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_por_defecto_no_carga_el_bloque_de_prueba(self):
        d = datos.cargar(self.ruta)
        self.assertEqual(sorted(d["bloque"].unique()), ["entrenamiento", "validacion"])
        self.assertEqual(len(d), 10)

    def test_pedir_la_prueba_sin_permiso_explicito_falla(self):
        with self.assertRaises(ValueError):
            datos.cargar(self.ruta, bloques=("entrenamiento", "prueba"))

    def test_con_permiso_explicito_carga_la_prueba(self):
        d = datos.cargar(self.ruta, bloques=("prueba",), permitir_prueba=True)
        self.assertEqual(len(d), 3)

    def test_las_numericas_vacias_quedan_como_faltantes(self):
        d = datos.cargar(self.ruta)
        self.assertTrue(np.isnan(d["venta_usd"].iloc[0]))
        self.assertEqual(d["venta_usd"].iloc[1], 1200.0)

    def test_la_etiqueta_es_entera(self):
        d = datos.cargar(self.ruta)
        self.assertEqual(sorted(d[datos.ETIQUETA].unique()), [0, 1])

    def test_separar_devuelve_entrenamiento_y_validacion_con_las_columnas_del_brazo(self):
        d = datos.cargar(self.ruta)
        x_e, y_e, x_v, y_v = datos.separar(d, "dia0")
        self.assertEqual((len(x_e), len(x_v)), (6, 4))
        self.assertEqual(list(x_e.columns), datos.BRAZOS["dia0"])


class Brazos(unittest.TestCase):
    PROHIBIDAS = {"cliente", "cohorte", "bloque", "bloque_60_20_20", "vuelve_12", "vuelve_12_comprando"}

    def test_ningun_brazo_usa_identificadores_bloques_ni_etiquetas(self):
        for nombre, cols in datos.BRAZOS.items():
            self.assertFalse(self.PROHIBIDAS & set(cols), nombre)

    def test_los_brazos_no_mezclan_ficha_unica_y_dia_0(self):
        self.assertFalse(set(datos.BRAZOS["dia0"]) & set(datos.FICHA_UNICA))
        self.assertFalse(set(datos.BRAZOS["ficha_unica"]) & set(datos.DIA0))
        self.assertFalse(set(datos.BRAZOS["sin_contacto"]) & (set(datos.DIA0) | set(datos.FICHA_UNICA)))

    def test_los_brazos_solo_difieren_en_los_datos_de_contacto(self):
        base = set(datos.BRAZOS["sin_contacto"])
        self.assertEqual(set(datos.BRAZOS["dia0"]) - base, set(datos.DIA0))
        self.assertEqual(set(datos.BRAZOS["ficha_unica"]) - base, set(datos.FICHA_UNICA))

    def test_todas_las_columnas_existen_en_el_contrato_y_cada_una_tiene_tipo(self):
        for cols in datos.BRAZOS.values():
            self.assertTrue(set(cols) <= set(reglas.COLUMNAS))
            for c in cols:
                self.assertTrue((c in datos.NUMERICAS) != (c in datos.CATEGORICAS), c)

    def test_la_base_usa_todas_las_variables_del_contrato_que_no_son_contacto(self):
        esperado = set(reglas.COLUMNAS) - self.PROHIBIDAS - set(datos.DIA0) - set(datos.FICHA_UNICA)
        self.assertEqual(set(datos.BRAZOS["sin_contacto"]), esperado)


if __name__ == "__main__":
    unittest.main()
