"""Pruebas del armado de la tabla interna, sobre una mini foto INVENTADA.

    py -m unittest discover -s exportacion/pruebas -t .

Cada persona de la mini foto es un caso con resultado conocido. Ningun dato
es real.
"""
import csv
import os
import tempfile
import unittest

import duckdb

from exportacion import armar

TIMELINE = [
    # P1 vuelve comprando. P2 lo acompania en su primera ficha.
    ("P1", 100, "ambos", True, "2023-03-10", "2023-06-01", "2023-06-10", "FACTURADA", True, "AAA", "v1", 2000, 200, 2, "BR", "aereo+hotel", True),
    ("P2", 100, "pasajero", False, "2023-03-10", "2023-06-01", "2023-06-10", "FACTURADA", True, "AAA", "v1", 2000, 200, 2, "BR", "aereo+hotel", True),
    ("P1", 101, "ambos", True, "2023-11-05", "2024-01-15", "2024-01-20", "FACTURADA", True, "AAA", "v1", 900, 90, 1, "AR", "solo_aereo", False),
    # P2 compra por primera vez en 2024, con P1 (cliente previo) de pasajero.
    ("P2", 102, "ambos", True, "2024-02-01", "2024-03-01", "2024-03-08", "FACTURADA", True, "BBB", "v2", 1500, 150, 2, "ES", "solo_aereo", False),
    ("P1", 102, "pasajero", False, "2024-02-01", "2024-03-01", "2024-03-08", "FACTURADA", True, "BBB", "v2", 1500, 150, 2, "ES", "solo_aereo", False),
    # P3: la segunda ficha es el mismo viaje (fecha de viaje a 2 dias).
    ("P3", 103, "ambos", True, "2023-05-01", "2023-07-01", "2023-07-10", "FACTURADA", True, "AAA", "v1", 1000, 100, 1, "US", "solo_aereo", False),
    ("P3", 104, "ambos", True, "2023-05-20", "2023-07-03", "2023-07-10", "FACTURADA", True, "AAA", "v1", 300, 30, 1, "US", "solo_hotel", False),
    # P4: la segunda compra cae un dia despues de los 12 meses.
    ("P4", 105, "ambos", True, "2023-04-01", "2023-05-01", "2023-05-05", "FACTURADA", True, "AAA", "v1", 800, 80, 1, "AR", "solo_aereo", False),
    ("P4", 106, "ambos", True, "2024-04-02", "2024-06-01", "2024-06-05", "FACTURADA", True, "AAA", "v1", 800, 80, 1, "AR", "solo_aereo", False),
    # P4B: la segunda compra cae exactamente a los 12 meses.
    ("P4B", 115, "ambos", True, "2023-04-01", "2023-05-01", "2023-05-05", "FACTURADA", True, "AAA", "v1", 800, 80, 1, "AR", "solo_aereo", False),
    ("P4B", 116, "ambos", True, "2024-04-01", "2024-06-01", "2024-06-05", "FACTURADA", True, "AAA", "v1", 800, 80, 1, "AR", "solo_aereo", False),
    # P5: entra con una compra corporativa.
    ("P5", 107, "ambos", True, "2023-02-01", "2023-02-10", "2023-02-12", "FACTURADA", True, "AAA", "v1", 700, 70, 1, "AR", "solo_aereo", False),
    # P6 compra y despues vuelve solo como pasajero de P7.
    ("P6", 108, "ambos", True, "2023-08-01", "2023-09-01", "2023-09-05", "FACTURADA", True, "BBB", "v2", 600, 60, 1, "BR", "solo_aereo", False),
    ("P7", 109, "cliente", True, "2024-01-10", "2024-02-10", "2024-02-15", "FACTURADA", True, "BBB", "v2", 1200, 120, 1, "BR", "solo_aereo", False),
    ("P6", 109, "pasajero", False, "2024-01-10", "2024-02-10", "2024-02-15", "FACTURADA", True, "BBB", "v2", 1200, 120, 1, "BR", "solo_aereo", False),
    # P8 ya era cliente en 2021: no es nuevo.
    ("P8", 90, "ambos", True, "2021-05-01", "2021-06-01", "2021-06-05", "FACTURADA", True, "AAA", "v1", 500, 50, 1, None, "sin_detalle", False),
    ("P8", 114, "ambos", True, "2023-01-15", "2023-02-01", "2023-02-05", "FACTURADA", True, "AAA", "v1", 500, 50, 1, "AR", "solo_aereo", False),
    # P9: su segunda ficha sigue en proceso, no cuenta.
    ("P9", 110, "ambos", True, "2023-09-01", "2023-10-01", "2023-10-05", "FACTURADA", True, "AAA", "v1", 400, 40, 1, "UY", "otro", False),
    ("P9", 111, "ambos", True, "2023-12-01", "2024-02-01", "2024-02-05", "PROCESO", False, "AAA", "v1", 400, 40, 1, "UY", "otro", False),
    # P10 es menor de edad al comprar.
    ("P10", 117, "ambos", True, "2023-06-01", "2023-07-01", "2023-07-05", "FACTURADA", True, "AAA", "v1", 400, 40, 1, "AR", "solo_aereo", False),
    # P11 compra despues del fin de las cohortes.
    ("P11", 118, "ambos", True, "2025-10-01", "2025-11-01", "2025-11-05", "FACTURADA", True, "AAA", "v1", 400, 40, 1, "AR", "solo_aereo", False),
    # P12: dos fichas el mismo dia 0.
    ("P12", 112, "ambos", True, "2023-06-15", "2023-08-01", "2023-08-10", "FACTURADA", True, "CCC", None, 1000, 100, 3, "MX", "paquete", False),
    ("P12", 113, "ambos", True, "2023-06-15", "2023-08-01", "2023-08-10", "FACTURADA", True, "CCC", None, 500, -20, 2, "MX", "otro", True),
]
COLS_TL = ["master_customer_id", "fic_numero", "rol_en_ficha", "es_titular", "fecha_compra", "fecha_viaje",
           "fecha_regreso", "estado", "es_venta_confirmada", "vendedor_cod", "vendedor_persona_id",
           "monto_venta_usd", "utilidad_usd", "total_pax", "destino_principal_pais", "tipo_producto", "tiene_seguro"]

FICHAS = sorted({f[1] for f in TIMELINE})
CORPORATIVAS = {107}
N_HOTELES = {100: 1, 104: 1}
N_DESTINOS = {100: 2}

FICHA_PERSONA = [
    ("P1", "R1", 100, "cliente"), ("P1", "R1", 100, "pasajero"), ("P1", "R2", 101, "cliente"),
    ("P2", "R3", 100, "pasajero"), ("P2", "R3", 102, "cliente"),
    ("P3", "R4", 103, "cliente"), ("P12", "R5", 112, "cliente"),
]
CONTACTOS = [
    # tit_cod, persona, mail, telefono, documento, nacimiento
    ("R1", "P1", False, True, True, False),
    ("R2", "P1", True, True, True, True),
    ("R3", "P2", True, True, True, True),
    ("R4", "P3", False, False, False, False),
    ("R5", "P12", True, True, True, True),
]
PERSONA = [
    # persona, genero, nacimiento_mes, nacionalidad, registros, mail, telefono, documento
    ("P1", "F", "1980-05-01", "UY", 2, True, True, True),
    ("P2", "M", "1975-01-01", "AR", 1, True, False, True),
    ("P3", "O", None, None, 1, False, False, False),
    ("P4", "F", "1990-01-01", "UY", 1, False, False, True),
    ("P4B", "F", "1990-01-01", "UY", 1, False, False, True),
    ("P5", "M", "1970-01-01", "UY", 1, True, True, True),
    ("P6", "M", "1985-01-01", "UY", 1, False, True, True),
    ("P7", "F", "1960-01-01", "UY", 3, True, True, True),
    ("P8", "F", "1950-01-01", "UY", 1, True, True, True),
    ("P9", None, "2000-01-01", "UY", 1, False, False, True),
    ("P10", "M", "2010-01-01", "UY", 1, False, False, True),
    ("P11", "M", "1980-01-01", "UY", 1, False, False, True),
    ("P12", "F", "1995-08-01", "UY", 1, True, True, True),
]
PAGADOR = [
    # ficha, categoria, tipo doc, millas, persona que paga
    (100, "persona_fisica", "CI", False, "P1"),
    (102, "medio_de_pago", "RUT", True, None),
    (103, "persona_fisica", "CI", False, "PX"),
    (112, "persona_fisica", "CI", False, "P12"), (112, "medio_de_pago", "RUT", True, None),
    (107, "empresa", "RUT", False, None),
]
SERVICIO = [
    # ficha, tipo, regimen, noches hotel, iata, devolucion
    (100, "CIAS. AEREAS", None, None, "LA", False), (100, "CIAS. AEREAS", None, None, "LA", False),
    (100, "CIAS. AEREAS", None, None, "G3", False),
    (100, "HOTELES", "Alojamiento y Desayuno", 9, None, False),
    (100, "DEVOLUCIONES GENERALES", None, None, None, True),
    (104, "HOTELES", "ALL INCLUSIVE", 7, None, False),
    (112, "PAQUETES", None, None, None, False),
]
VENDEDOR_CODIGO = [("AAA", "v1", True), ("BBB", "v2", True), ("CCC", None, False)]


def _csv(carpeta, nombre, columnas, filas):
    with open(os.path.join(carpeta, nombre + ".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        for f in filas:
            w.writerow(["" if v is None else ("t" if v is True else "f" if v is False else v) for v in f])


def escribir_mini_foto(carpeta):
    _csv(carpeta, "timeline", COLS_TL, TIMELINE)
    _csv(carpeta, "ficha", ["fic_numero", "es_corporativa", "n_hoteles", "n_destinos"],
         [(f, f in CORPORATIVAS, N_HOTELES.get(f, 0), N_DESTINOS.get(f, 1)) for f in FICHAS])
    _csv(carpeta, "ficha_persona", ["master_customer_id", "tit_cod", "fic_numero", "rol"], FICHA_PERSONA)
    _csv(carpeta, "contactos", ["tit_cod", "master_customer_id", "tiene_mail", "tiene_telefono",
                                "tiene_documento", "tiene_nacimiento"], CONTACTOS)
    _csv(carpeta, "persona", ["master_customer_id", "genero", "nacimiento_mes", "pais_nacionalidad",
                              "n_registros_atlas", "tiene_mail", "tiene_telefono", "tiene_documento"], PERSONA)
    _csv(carpeta, "pagador", ["fic_numero", "pagador_categoria", "pagador_doc_tipo", "es_millas",
                              "master_customer_id"], PAGADOR)
    _csv(carpeta, "servicio", ["fic_numero", "srv_tipo_nom", "hotel_regimen", "hotel_noches",
                               "aerolinea_iata", "es_nota_devolucion"], SERVICIO)
    _csv(carpeta, "vendedor_codigo", ["ven_cod", "vendedor_persona_id", "es_persona"], VENDEDOR_CODIGO)


class ArmadoInterno(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        escribir_mini_foto(cls.tmp.name)
        con = duckdb.connect()
        armar.cargar_foto(con, cls.tmp.name)
        armar.construir_interna(con, cohorte_desde="2023-01-01", cohorte_hasta="2025-08-31")
        cur = con.execute("SELECT * FROM interna")
        cols = [d[0] for d in cur.description]
        cls.filas = {f[0]: dict(zip(cols, f)) for f in cur.fetchall()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ---- universo -------------------------------------------------------
    def test_universo_son_los_clientes_nuevos_no_corporativos_adultos(self):
        self.assertEqual(sorted(self.filas),
                         sorted(["P1", "P2", "P3", "P4", "P4B", "P6", "P7", "P9", "P12"]))

    def test_quien_entro_con_compra_corporativa_queda_afuera(self):
        self.assertNotIn("P5", self.filas)

    def test_quien_ya_era_cliente_antes_de_2023_queda_afuera(self):
        self.assertNotIn("P8", self.filas)

    def test_menor_de_edad_al_comprar_queda_afuera(self):
        self.assertNotIn("P10", self.filas)

    def test_compra_posterior_al_fin_de_cohortes_queda_afuera(self):
        self.assertNotIn("P11", self.filas)

    def test_la_cohorte_es_el_anio_de_la_primera_compra_como_titular(self):
        self.assertEqual(self.filas["P1"]["cohorte"], 2023)
        self.assertEqual(self.filas["P2"]["cohorte"], 2024)

    # ---- etiqueta -------------------------------------------------------
    def test_vuelve_si_compra_otro_viaje_dentro_de_los_12_meses(self):
        self.assertTrue(self.filas["P1"]["vuelve_12"])
        self.assertTrue(self.filas["P1"]["vuelve_12_comprando"])

    def test_otra_ficha_del_mismo_viaje_no_es_vuelta(self):
        self.assertFalse(self.filas["P3"]["vuelve_12"])

    def test_compra_un_dia_despues_de_los_12_meses_no_es_vuelta(self):
        self.assertFalse(self.filas["P4"]["vuelve_12"])

    def test_compra_exactamente_a_los_12_meses_es_vuelta(self):
        self.assertTrue(self.filas["P4B"]["vuelve_12"])

    def test_volver_como_pasajero_cuenta_como_vuelta_pero_no_como_compra(self):
        self.assertTrue(self.filas["P6"]["vuelve_12"])
        self.assertFalse(self.filas["P6"]["vuelve_12_comprando"])

    def test_ficha_en_proceso_no_cuenta_como_vuelta(self):
        self.assertFalse(self.filas["P9"]["vuelve_12"])

    def test_otra_ficha_del_mismo_dia_0_no_es_vuelta(self):
        self.assertFalse(self.filas["P12"]["vuelve_12"])

    # ---- la compania ----------------------------------------------------
    def test_viajo_antes_como_acompaniante(self):
        self.assertEqual(self.filas["P2"]["n_prev_pasajero"], 1)
        self.assertEqual(self.filas["P1"]["n_prev_pasajero"], 0)

    def test_viaja_con_un_cliente_previo(self):
        self.assertEqual(self.filas["P2"]["n_comp_cliente_previo"], 1)
        self.assertEqual(self.filas["P7"]["n_comp_cliente_previo"], 1)
        # P2 acompania a P1 pero todavia no tenia historial ese dia
        self.assertEqual(self.filas["P1"]["n_comp_cliente_previo"], 0)
        self.assertEqual(self.filas["P1"]["n_comp_historial"], 0)

    # ---- la compra del dia 0 --------------------------------------------
    def test_dos_fichas_el_dia_0_suman_venta_y_utilidad_y_toman_el_grupo_mayor(self):
        f = self.filas["P12"]
        self.assertEqual(f["venta"], 1500)
        self.assertEqual(f["utilidad"], 80)
        self.assertEqual(f["pax"], 3)
        self.assertTrue(f["tiene_seguro"])

    def test_anticipacion_y_noches_salen_de_la_ficha_ancla(self):
        self.assertEqual(self.filas["P1"]["anticipacion_dias"], 83)
        self.assertEqual(self.filas["P1"]["noches"], 9)

    def test_destino_producto_hotel_y_destinos(self):
        f = self.filas["P1"]
        self.assertEqual(f["pais"], "BR")
        self.assertEqual(f["tipo_producto"], "aereo+hotel")
        self.assertTrue(f["lleva_hotel"])
        self.assertEqual(f["n_destinos"], 2)

    def test_servicios_no_cuentan_las_devoluciones(self):
        self.assertEqual(self.filas["P1"]["n_servicios"], 4)

    def test_aerolinea_principal_es_la_de_mas_servicios(self):
        self.assertEqual(self.filas["P1"]["aerolinea_iata"], "LA")
        self.assertIsNone(self.filas["P12"]["aerolinea_iata"])

    def test_regimen_del_hotel_se_normaliza(self):
        self.assertEqual(self.filas["P1"]["regimen"], "desayuno")
        self.assertIsNone(self.filas["P2"]["regimen"])

    # ---- quien pago -----------------------------------------------------
    def test_pagador(self):
        self.assertEqual(self.filas["P1"]["pagador"], "cliente")
        self.assertEqual(self.filas["P2"]["pagador"], "solo_millas")
        self.assertEqual(self.filas["P3"]["pagador"], "tercero")
        self.assertEqual(self.filas["P4"]["pagador"], "sin_dato")
        self.assertEqual(self.filas["P12"]["pagador"], "cliente")

    def test_canje_de_millas(self):
        self.assertTrue(self.filas["P2"]["canje_millas"])
        self.assertTrue(self.filas["P12"]["canje_millas"])
        self.assertFalse(self.filas["P1"]["canje_millas"])

    # ---- el vendedor ----------------------------------------------------
    def test_fichas_del_vendedor_en_los_12_meses_previos(self):
        # v1 antes del 2023-03-10: las fichas 114 (2023-01-15) y 107 (2023-02-01,
        # corporativa: tambien es trabajo del vendedor); la 90 es de 2021
        self.assertEqual(self.filas["P1"]["vend_fichas_12m"], 2)

    def test_antiguedad_del_vendedor_desde_su_primera_ficha(self):
        # la primera ficha de v1 es la 90, del 2021-05-01
        self.assertEqual(self.filas["P1"]["vend_antiguedad_dias"], 678)

    def test_vendedor_sin_persona_se_identifica_por_codigo_y_no_es_persona(self):
        self.assertEqual(self.filas["P12"]["vend_clave"], "cod:CCC")
        self.assertFalse(self.filas["P12"]["vend_es_persona"])
        self.assertEqual(self.filas["P1"]["vend_clave"], "v1")

    # ---- ficha unica y ficha del dia 0 ----------------------------------
    def test_ficha_unica_trae_el_estado_de_hoy(self):
        f = self.filas["P1"]
        self.assertTrue(f["fu_tiene_mail"])
        self.assertTrue(f["fu_tiene_nacimiento"])
        self.assertEqual(f["fu_registros"], 2)
        self.assertEqual(f["edad"], 42)
        self.assertEqual(f["genero"], "F")

    def test_ficha_del_dia_0_solo_mira_los_registros_de_la_primera_ficha(self):
        f = self.filas["P1"]          # R1 no tiene mail ni nacimiento; R2 llega despues
        self.assertFalse(f["d0_tiene_mail"])
        self.assertTrue(f["d0_tiene_telefono"])
        self.assertFalse(f["d0_tiene_nacimiento"])

    def test_la_ficha_unica_incluye_lo_que_tenga_cualquier_registro_de_la_persona(self):
        # la ficha canonica de P2 no tiene telefono, pero su registro R3 si:
        # la ficha unica nunca puede saber menos que la del dia 0
        self.assertTrue(self.filas["P2"]["fu_tiene_telefono"])
        self.assertTrue(self.filas["P2"]["d0_tiene_telefono"])
        # P3: ni la ficha canonica ni su registro tienen nada
        self.assertFalse(self.filas["P3"]["fu_tiene_mail"])
        self.assertFalse(self.filas["P3"]["fu_tiene_nacimiento"])

    def test_sin_registro_en_la_primera_ficha_el_dia_0_queda_sin_dato(self):
        self.assertIsNone(self.filas["P4"]["d0_tiene_mail"])

    def test_genero_no_informado_queda_nulo(self):
        self.assertIsNone(self.filas["P3"]["genero"])
        self.assertIsNone(self.filas["P9"]["genero"])


if __name__ == "__main__":
    unittest.main()
