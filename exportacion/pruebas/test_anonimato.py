"""Pruebas de las reglas de anonimato. Todos los datos son inventados."""
import collections
import datetime
import random
import unittest

from exportacion import anonimato as an
from exportacion import reglas

SD = reglas.SIN_DATO


class Bandas(unittest.TestCase):
    LIM, ETQ = [3, 7, 14], ["0-3", "4-7", "8-14", "15+"]

    def test_el_limite_superior_es_inclusivo(self):
        self.assertEqual(an.banda(3, self.LIM, self.ETQ), "0-3")
        self.assertEqual(an.banda(4, self.LIM, self.ETQ), "4-7")
        self.assertEqual(an.banda(14, self.LIM, self.ETQ), "8-14")

    def test_por_encima_del_ultimo_limite_cae_en_la_ultima_banda(self):
        self.assertEqual(an.banda(400, self.LIM, self.ETQ), "15+")

    def test_sin_valor_es_sin_dato(self):
        self.assertEqual(an.banda(None, self.LIM, self.ETQ), SD)

    def test_por_debajo_del_minimo_es_sin_dato(self):
        self.assertEqual(an.banda(-2, self.LIM, self.ETQ, minimo=0), SD)


class Montos(unittest.TestCase):
    def test_sin_valor_o_no_positivo_queda_vacio(self):
        for x in (None, 0, -5):
            self.assertIsNone(an.redondear_monto(x, 30000))

    def test_redondea_con_paso_segun_el_tamanio(self):
        casos = {10: 50, 990: 1000, 1234: 1200, 1250: 1300, 7480: 7500,
                 19800: 20000, 25499: 25000, 25500: 26000}
        for x, esperado in casos.items():
            self.assertEqual(an.redondear_monto(x, 30000), esperado, x)

    def test_por_encima_del_tope_queda_en_el_tope(self):
        self.assertEqual(an.redondear_monto(183666, 30000), 30000)

    def test_redondear_dos_veces_no_cambia_nada(self):
        for x in range(1, 40000, 37):
            r = an.redondear_monto(x, 30000)
            self.assertEqual(an.redondear_monto(r, 30000), r, x)

    def test_indice_redondea_y_conserva_el_signo(self):
        casos = {0: 0, 2: 0, 3: 5, 97: 95, 98: 100, 104: 100, 105: 110, 1234: 1250, -37: -35}
        for x, esperado in casos.items():
            self.assertEqual(an.redondear_indice(x, (-100, 2000)), esperado, x)

    def test_indice_respeta_los_topes(self):
        self.assertEqual(an.redondear_indice(-260, (-100, 2000)), -100)
        self.assertEqual(an.redondear_indice(5000, (-100, 2000)), 2000)

    def test_indice_redondear_dos_veces_no_cambia_nada(self):
        for x in range(-300, 2500, 7):
            r = an.redondear_indice(x, (-100, 2000))
            self.assertEqual(an.redondear_indice(r, (-100, 2000)), r, x)


class Codigos(unittest.TestCase):
    IDS = ["MCU-%04d" % i for i in range(60)]

    def test_son_correlativos_y_no_se_repiten(self):
        m = an.asignar_codigos(self.IDS, "C-", 5, semilla=7)
        self.assertEqual(sorted(m.values()), ["C-%05d" % i for i in range(1, 61)])

    def test_no_siguen_el_orden_de_los_ids_originales(self):
        m = an.asignar_codigos(self.IDS, "C-", 5, semilla=7)
        self.assertNotEqual([m[i] for i in self.IDS], sorted(m.values()))

    def test_misma_semilla_mismo_resultado_sin_importar_el_orden_de_entrada(self):
        a = an.asignar_codigos(self.IDS, "C-", 5, semilla=7)
        b = an.asignar_codigos(list(reversed(self.IDS)), "C-", 5, semilla=7)
        self.assertEqual(a, b)

    def test_otra_semilla_da_otra_correspondencia(self):
        a = an.asignar_codigos(self.IDS, "C-", 5, semilla=7)
        b = an.asignar_codigos(self.IDS, "C-", 5, semilla=8)
        self.assertNotEqual(a, b)

    def test_el_codigo_no_contiene_el_id_original(self):
        m = an.asignar_codigos(self.IDS, "C-", 5, semilla=7)
        for original, codigo in m.items():
            self.assertNotIn(original, codigo)


class GruposChicos(unittest.TestCase):
    def filas(self):
        return ([{"a": "1", "b": "x"} for _ in range(5)] + [{"a": "1", "b": "y"} for _ in range(2)]
                + [{"a": "1", "b": "z"}] + [{"a": "2", "b": "x"} for _ in range(2)])

    def test_encuentra_las_filas_en_grupos_de_menos_de_k(self):
        self.assertEqual(an.filas_en_grupos_chicos(self.filas(), ["a", "b"], 3), [5, 6, 7, 8, 9])

    def test_generalizar_aplica_los_pasos_en_orden_solo_a_los_grupos_chicos(self):
        filas = self.filas()
        pasos = [("b", lambda f: f.update(b="*")), ("a", lambda f: f.update(a="*"))]
        informe, restantes = an.generalizar(filas, ["a", "b"], 3, pasos)
        self.assertEqual(informe, [("b", 5), ("a", 2)])
        # los cinco del grupo grande no se tocan
        self.assertEqual(filas[:5], [{"a": "1", "b": "x"}] * 5)
        # y, z se juntan en un grupo de 3 que ya alcanza
        self.assertEqual(filas[5:8], [{"a": "1", "b": "*"}] * 3)
        # los dos de a=2 no llegan a 3 ni suprimiendo todo: quedan informados
        self.assertEqual(restantes, [8, 9])

    def test_si_no_hay_grupos_chicos_no_toca_nada(self):
        filas = [{"a": "1"} for _ in range(4)]
        informe, restantes = an.generalizar(filas, ["a"], 3, [("a", lambda f: f.update(a="*"))])
        self.assertEqual((informe, restantes), ([], []))
        self.assertEqual(filas, [{"a": "1"}] * 4)


class DetalleDentroDelGrupo(unittest.TestCase):
    """Segunda capa: dentro de cada grupo base, ningun subgrupo por `detalle`
    puede tener menos de k filas. Se suprime lo minimo."""
    PASOS = [("d", lambda f: f.update(d=SD))]

    @staticmethod
    def grupo(base, **cuantos):
        return [{"g": base, "d": d} for d, n in cuantos.items() for _ in range(n)]

    def cuenta(self, filas, base):
        return dict(collections.Counter(f["d"] for f in filas if f["g"] == base))

    def test_subgrupos_suficientes_no_se_tocan(self):
        filas = self.grupo("A", x=3, y=3)
        informe, restantes = an.asegurar_detalle(filas, ["g"], ["d"], 3, self.PASOS)
        self.assertEqual((informe, restantes), ([], []))
        self.assertEqual(self.cuenta(filas, "A"), {"x": 3, "y": 3})

    def test_si_los_suprimidos_no_llegan_a_k_se_completa_con_filas_del_subgrupo_mas_grande(self):
        filas = self.grupo("A", x=7, y=1, z=1)
        informe, restantes = an.asegurar_detalle(filas, ["g"], ["d"], 3, self.PASOS)
        self.assertEqual(self.cuenta(filas, "A"), {"x": 6, SD: 3})
        self.assertEqual(informe, [("d", 2), ("prestadas", 1)])
        self.assertEqual(restantes, [])

    def test_si_nadie_puede_prestar_se_suprime_el_detalle_de_todo_el_grupo(self):
        filas = self.grupo("A", x=3, y=2)
        informe, restantes = an.asegurar_detalle(filas, ["g"], ["d"], 3, self.PASOS)
        self.assertEqual(self.cuenta(filas, "A"), {SD: 5})
        self.assertEqual(informe, [("d", 2), ("grupo_completo", 3)])
        self.assertEqual(restantes, [])

    def test_cada_grupo_base_se_resuelve_por_separado(self):
        filas = self.grupo("A", x=7, y=1, z=1) + self.grupo("B", x=4, y=4)
        an.asegurar_detalle(filas, ["g"], ["d"], 3, self.PASOS)
        self.assertEqual(self.cuenta(filas, "B"), {"x": 4, "y": 4})
        self.assertEqual(an.filas_en_grupos_chicos(filas, ["g", "d"], 3), [])


CONTRATO = [
    ("id", {"tipo": "codigo", "patron": r"C-\d{2}"}),
    ("color", {"tipo": "categoria", "valores": ["rojo", "azul", SD]}),
    ("monto", {"tipo": "monto", "tope": 30000, "vacio": True}),
    ("idx", {"tipo": "indice", "topes": (-100, 2000)}),
]


def fila_ok(i, color="rojo"):
    return {"id": "C-%02d" % i, "color": color, "monto": "1200", "idx": "95"}


class Verificaciones(unittest.TestCase):
    def test_columnas_iguales_al_contrato_pasan(self):
        self.assertEqual(an.revisar_columnas(["id", "color", "monto", "idx"], CONTRATO), [])

    def test_columna_que_no_esta_en_el_contrato_se_rechaza(self):
        p = an.revisar_columnas(["id", "color", "monto", "idx", "nombre"], CONTRATO)
        self.assertTrue(any("nombre" in x for x in p), p)

    def test_columna_faltante_se_rechaza(self):
        p = an.revisar_columnas(["id", "color", "monto"], CONTRATO)
        self.assertTrue(any("idx" in x for x in p), p)

    def test_columnas_en_otro_orden_se_rechazan(self):
        self.assertTrue(an.revisar_columnas(["color", "id", "monto", "idx"], CONTRATO))

    def test_valores_dentro_del_contrato_pasan(self):
        self.assertEqual(an.revisar_dominios([fila_ok(1), dict(fila_ok(2), monto="")], CONTRATO), [])

    def test_categoria_fuera_de_la_lista_se_rechaza(self):
        p = an.revisar_dominios([dict(fila_ok(1), color="verde")], CONTRATO)
        self.assertTrue(any("color" in x for x in p), p)

    def test_monto_fuera_de_la_grilla_del_tope_o_no_numerico_se_rechaza(self):
        for malo in ("1234", "40000", "abc", "-50", "12.5"):
            p = an.revisar_dominios([dict(fila_ok(1), monto=malo)], CONTRATO)
            self.assertTrue(any("monto" in x for x in p), malo)

    def test_indice_vacio_o_fuera_de_grilla_se_rechaza(self):
        for malo in ("", "97", "2500"):
            p = an.revisar_dominios([dict(fila_ok(1), idx=malo)], CONTRATO)
            self.assertTrue(any("idx" in x for x in p), malo)

    def test_codigo_con_otro_formato_se_rechaza(self):
        for malo in ("C-1", "MCU-20260601-0000123", "C-123"):
            p = an.revisar_dominios([dict(fila_ok(1), id=malo)], CONTRATO)
            self.assertTrue(any("id" in x for x in p), malo)

    def test_valores_con_forma_de_dato_personal_se_rechazan(self):
        for malo in ("ana@correo.com", "099123456", "+59899123456", "PEREZ GONZALEZ, MARIA DE LOS ANGELES"):
            p = an.revisar_patrones([dict(fila_ok(1), color=malo)])
            self.assertTrue(p, malo)

    def test_valores_normales_no_disparan_los_patrones(self):
        self.assertEqual(an.revisar_patrones([fila_ok(1), {"x": "aerolineas_argentinas", "y": "30000"}]), [])

    def test_codigo_de_cliente_repetido_se_rechaza(self):
        self.assertEqual(an.revisar_codigos([fila_ok(1), fila_ok(2)], "id"), [])
        self.assertTrue(an.revisar_codigos([fila_ok(1), fila_ok(1)], "id"))

    def test_grupo_de_menos_de_k_se_rechaza(self):
        filas = [fila_ok(i) for i in range(5)] + [fila_ok(9, color="azul")]
        self.assertEqual(an.revisar_k(filas[:5], ["color"], 5, "prueba"), [])
        p = an.revisar_k(filas, ["color"], 5, "prueba")
        self.assertTrue(any("1" in x for x in p), p)

    def test_categoria_con_pocos_clientes_se_rechaza_salvo_sin_dato(self):
        filas = [fila_ok(i) for i in range(30)] + [fila_ok(40, color="azul"), fila_ok(41, color=SD)]
        p = an.revisar_categorias(filas, CONTRATO, 20)
        self.assertTrue(any("azul" in x for x in p), p)
        self.assertFalse(any(SD in x for x in p), p)

    def test_archivo_ordenado_por_cohorte_se_rechaza(self):
        ordenado = [{"cohorte": str(2023 + i // 100)} for i in range(300)]
        self.assertTrue(an.revisar_orden(ordenado, "cohorte"))
        mezclado = list(ordenado)
        random.Random(3).shuffle(mezclado)
        self.assertEqual(an.revisar_orden(mezclado, "cohorte"), [])

    def test_gasto_por_pasajero_no_delata_el_tamanio_del_grupo(self):
        def f(pas, venta, pp):
            return {"pasajeros": pas, "venta_usd": venta, "venta_por_pasajero_usd": pp}
        self.assertEqual(an.revisar_por_pasajero([f("2", "3000", "1500"), f("5-9", "6000", "1000"),
                                                  f("10+", "30000", ""), f(SD, "500", "")]), [])
        self.assertTrue(an.revisar_por_pasajero([f("10+", "30000", "1000")]))
        self.assertTrue(an.revisar_por_pasajero([f("5-9", "6000", "1200")]))
        self.assertTrue(an.revisar_por_pasajero([f(SD, "500", "250")]))


class SupresionCoherente(unittest.TestCase):
    def test_si_se_suprime_el_producto_no_quedan_la_aerolinea_ni_el_regimen(self):
        def f(producto, aerolinea, regimen):
            return {"tipo_producto": producto, "aerolinea": aerolinea, "regimen_hotel": regimen}
        self.assertEqual(an.revisar_supresion([f("paquete", "latam", "desayuno"), f(SD, SD, SD)]), [])
        self.assertTrue(an.revisar_supresion([f(SD, "latam", SD)]))
        self.assertTrue(an.revisar_supresion([f(SD, SD, "desayuno")]))


def interna(**cambios):
    f = {"cid": "MCU-1", "f1": datetime.date(2023, 3, 10), "v1": datetime.date(2023, 6, 1), "cohorte": 2023,
         "vuelve_12": True, "vuelve_12_comprando": False, "n_prev_pasajero": 4,
         "n_comp": 1, "n_comp_historial": 1, "n_comp_cliente_previo": 0,
         "pax": 2, "venta": 3140.0, "utilidad": 310.0, "anticipacion_dias": 83, "noches": 9,
         "pais": "BR", "tipo_producto": "aereo+hotel", "tiene_seguro": True, "lleva_hotel": True,
         "n_destinos": 2, "n_servicios": 4, "aerolinea_iata": "LA", "regimen": "desayuno",
         "canje_millas": False, "pagador": "cliente",
         "vend_clave": "v1", "vend_es_persona": True, "vend_fichas_12m": 210, "vend_antiguedad_dias": 678,
         "fu_tiene_mail": True, "fu_tiene_telefono": True, "fu_tiene_documento": True,
         "fu_tiene_nacimiento": True, "fu_registros": 2,
         "d0_tiene_mail": False, "d0_tiene_telefono": True, "d0_tiene_documento": True,
         "d0_tiene_nacimiento": False}
    f.update(cambios)
    return f


CORTES = (datetime.date(2024, 8, 1), datetime.date(2025, 3, 1))


def publica(**cambios):
    return an.fila_publica(interna(**cambios), "C-00001", "V-001", CORTES, k_utilidad=250.0)


class FilaPublica(unittest.TestCase):
    def test_trae_exactamente_las_columnas_del_contrato(self):
        f = publica()
        self.assertEqual([c for c in f if not c.startswith("_")], reglas.COLUMNAS)

    def test_no_lleva_el_id_ni_las_fechas(self):
        valores = [str(v) for v in publica().values()]
        self.assertNotIn("MCU-1", valores)
        self.assertFalse(any("2023-03-10" in v or "2023-06-01" in v for v in valores))

    def test_particiones(self):
        self.assertEqual(publica()["bloque"], "entrenamiento")
        self.assertEqual(publica()["bloque_60_20_20"], "entrenamiento")
        f = publica(cohorte=2024, f1=datetime.date(2024, 9, 1))
        self.assertEqual((f["bloque"], f["bloque_60_20_20"]), ("validacion", "validacion"))
        f = publica(cohorte=2025, f1=datetime.date(2025, 3, 1))
        self.assertEqual((f["bloque"], f["bloque_60_20_20"]), ("prueba", "prueba"))

    def test_etiqueta_y_compania(self):
        f = publica()
        self.assertEqual((f["vuelve_12"], f["vuelve_12_comprando"]), ("1", "0"))
        self.assertEqual((f["fue_acompaniante_antes"], f["viajes_previos_acompaniante"]), ("1", "3+"))
        self.assertEqual((f["viaja_con_cliente_previo"], f["viaja_con_alguien_con_historial"]), ("0", "1"))

    def test_montos_redondeados_y_utilidad_como_indice(self):
        f = publica()
        self.assertEqual(f["venta_usd"], "3100")
        self.assertEqual(f["venta_por_pasajero_usd"], "1600")     # 3140 / 2 = 1570
        self.assertEqual(f["utilidad_indice"], "120")             # 310 / 250 * 100 = 124

    def test_grupo_de_5_a_9_usa_el_tamanio_representativo(self):
        f = publica(pax=8, venta=8000.0)
        self.assertEqual(f["pasajeros"], "5-9")
        self.assertEqual(f["venta_por_pasajero_usd"], "1300")     # 8000 / 6 = 1333

    def test_grupo_de_10_o_mas_no_publica_gasto_por_pasajero(self):
        f = publica(pax=30, venta=30000.0)
        self.assertEqual((f["pasajeros"], f["venta_por_pasajero_usd"]), ("10+", ""))

    def test_venta_no_positiva_queda_vacia(self):
        f = publica(venta=-20.0)
        self.assertEqual((f["venta_usd"], f["venta_por_pasajero_usd"]), ("", ""))

    def test_destino(self):
        f = publica()
        self.assertEqual((f["region_destino"], f["pais_destino"]), ("brasil", "BR"))
        f = publica(pais="JP")
        self.assertEqual((f["region_destino"], f["pais_destino"]), ("asia_oceania_africa", "otro"))
        f = publica(pais=None, n_destinos=0)
        self.assertEqual((f["region_destino"], f["pais_destino"], f["destinos"]), (SD, SD, SD))

    def test_producto_aerolinea_y_regimen(self):
        f = publica()
        self.assertEqual((f["tipo_producto"], f["aerolinea"], f["regimen_hotel"]),
                         ("aereo_hotel", "latam", "desayuno"))
        f = publica(tipo_producto="crucero", aerolinea_iata=None, regimen=None, lleva_hotel=False)
        self.assertEqual((f["tipo_producto"], f["aerolinea"], f["regimen_hotel"]),
                         ("maritimo", "sin_aereo", "sin_hotel"))
        f = publica(aerolinea_iata="TK", regimen="media_pension")
        self.assertEqual((f["aerolinea"], f["regimen_hotel"]), ("otra", "pension"))

    def test_bandas_del_viaje_y_del_vendedor(self):
        f = publica()
        self.assertEqual((f["noches"], f["anticipacion"], f["destinos"], f["servicios"]),
                         ("8-14", "61-90", "2", "3-4"))
        self.assertEqual((f["vendedor"], f["vendedor_fichas_12m"], f["vendedor_antiguedad"]),
                         ("V-001", "150-299", "1-3"))
        self.assertEqual(publica(anticipacion_dias=-4)["anticipacion"], SD)

    def test_fichas(self):
        f = publica()
        self.assertEqual((f["fu_tiene_mail"], f["d0_tiene_mail"], f["fu_registros"]), ("1", "0", "2"))
        self.assertEqual(publica(d0_tiene_mail=None)["d0_tiene_mail"], "0")

    def test_guarda_el_anio_de_viaje_solo_como_campo_oculto(self):
        self.assertEqual(publica()["_anio_viaje"], "2023")


class Cortes(unittest.TestCase):
    def test_los_cortes_caen_en_inicio_de_mes_cerca_del_60_y_el_80(self):
        fechas = [datetime.date(2023, 1, 1) + datetime.timedelta(days=i) for i in range(1000)]
        c1, c2 = an.cortes_60_20_20(fechas)
        self.assertEqual((c1.day, c2.day), (1, 1))
        antes_1 = sum(f < c1 for f in fechas) / len(fechas)
        antes_2 = sum(f < c2 for f in fechas) / len(fechas)
        self.assertAlmostEqual(antes_1, 0.60, delta=0.02)
        self.assertAlmostEqual(antes_2, 0.80, delta=0.02)


def internas_inventadas(n=4000, semilla=1):
    r = random.Random(semilla)
    filas = []
    for i in range(n):
        f1 = datetime.date(2023, 1, 1) + datetime.timedelta(days=r.randrange(0, 973))
        ant = r.choice([3, 10, 20, 45, 75, 120, 200])
        pax = r.choice([1, 1, 2, 2, 2, 3, 4, 6, 12])
        pais = r.choice(["BR", "BR", "AR", "AR", "ES", "US", "MX", "JP", "PY", None])
        hotel = r.random() < 0.4
        filas.append(interna(
            cid="MCU-%06d" % i, f1=f1, v1=f1 + datetime.timedelta(days=ant), cohorte=f1.year,
            vuelve_12=r.random() < 0.2, vuelve_12_comprando=r.random() < 0.15,
            n_prev_pasajero=r.choice([0, 0, 0, 1, 2, 5]), n_comp_historial=r.choice([0, 0, 1]),
            n_comp_cliente_previo=r.choice([0, 0, 1]), pax=pax,
            venta=r.choice([-10.0, 300.0, 1250.0, 4800.0, 9000.0, 52000.0]),
            utilidad=r.choice([-900.0, 0.0, 40.0, 250.0, 900.0, 9000.0]),
            anticipacion_dias=ant, noches=r.choice([2, 5, 10, 20]),
            pais=pais, n_destinos=0 if pais is None else r.choice([1, 1, 2, 3]),
            tipo_producto=r.choice(["solo_aereo", "aereo+hotel", "paquete", "solo_hotel", "otro", "crucero"]),
            tiene_seguro=r.random() < 0.2, lleva_hotel=hotel,
            regimen=r.choice(["desayuno", "todo_incluido", "solo_alojamiento", "otro"]) if hotel else None,
            aerolinea_iata=r.choice(["LA", "CM", "G3", "IB", "TK", None]),
            n_servicios=r.choice([1, 2, 3, 6, 9]), canje_millas=r.random() < 0.3,
            pagador=r.choice(["cliente", "cliente", "tercero", "solo_millas"]),
            vend_clave="v%d" % r.choice([1, 1, 1, 2, 2, 3, 4, 5, 6, 7]) if r.random() < 0.99 else "raro%d" % i,
            vend_es_persona=r.random() < 0.95, vend_fichas_12m=r.choice([10, 100, 250, 400, 900]),
            vend_antiguedad_dias=r.choice([100, 700, 2000]),
            fu_tiene_mail=r.random() < 0.7, fu_tiene_telefono=r.random() < 0.5,
            fu_tiene_documento=r.random() < 0.9, fu_tiene_nacimiento=r.random() < 0.9,
            fu_registros=r.choice([1, 1, 2, 3]),
            d0_tiene_mail=r.random() < 0.6, d0_tiene_telefono=r.random() < 0.5,
            d0_tiene_documento=r.random() < 0.9, d0_tiene_nacimiento=r.random() < 0.8))
    return filas


class TablaCompleta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.internas = internas_inventadas()
        cls.filas, cls.informe, cls.mapas = an.armar_publica(cls.internas, semilla=11, k_utilidad=250.0)

    def test_la_tabla_armada_pasa_todas_las_verificaciones(self):
        self.assertEqual(an.revisar_todo(self.filas, reglas), [])

    def test_no_quedan_campos_ocultos(self):
        self.assertEqual(list(self.filas[0]), reglas.COLUMNAS)

    def test_ningun_grupo_queda_por_debajo_de_k_ni_contando_el_anio_de_viaje(self):
        self.assertEqual(self.informe["grupos_chicos_al_final"], {"cuasi_1": 0, "cuasi_2": 0})

    def test_informa_cuantas_filas_toco_y_cuantas_saco(self):
        self.assertEqual(self.informe["filas_entrada"], len(self.internas))
        self.assertEqual(self.informe["filas_salida"], len(self.filas))
        self.assertEqual(self.informe["filas_salida"] + self.informe["filas_retiradas"], len(self.internas))

    def test_ningun_id_original_aparece_en_la_tabla(self):
        originales = {f["cid"] for f in self.internas} | {f["vend_clave"] for f in self.internas}
        for f in self.filas:
            self.assertFalse(originales & set(f.values()))

    def test_la_correspondencia_queda_aparte_y_cubre_a_todos_los_clientes_publicados(self):
        codigos = set(self.mapas["clientes"].values())
        self.assertTrue({f["cliente"] for f in self.filas} <= codigos)

    def test_vendedores_con_pocos_clientes_van_a_otros(self):
        self.assertIn(reglas.VENDEDOR_OTROS, {f["vendedor"] for f in self.filas})
        self.assertTrue(all(c == reglas.VENDEDOR_OTROS for v, c in self.mapas["vendedores"].items()
                            if v.startswith("raro")))

    def test_misma_semilla_misma_tabla(self):
        otra, _, _ = an.armar_publica(internas_inventadas(), semilla=11, k_utilidad=250.0)
        self.assertEqual(otra, self.filas)

    def test_una_tabla_alterada_no_pasa(self):
        mala = [dict(f) for f in self.filas]
        mala[0]["pais_destino"] = "ZZ"
        self.assertTrue(an.revisar_todo(mala, reglas))
        mala = [dict(f, nombre="x") for f in self.filas]
        self.assertTrue(an.revisar_todo(mala, reglas))
        mala = [dict(f) for f in self.filas] + [dict(self.filas[0])]
        self.assertTrue(an.revisar_todo(mala, reglas))


if __name__ == "__main__":
    unittest.main()
