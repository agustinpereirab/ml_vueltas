"""Armado de la tabla INTERNA: una fila por cliente nuevo, con valores exactos
e ids de la base. No sale de la empresa; `anonimato.py` la convierte en la
tabla que si sale.

Definiciones (las de la presentacion, con las reglas del repo de cohortes):

- Cliente: persona con al menos una ficha facturada como titular.
- Primera compra (dia 0): la fecha de su primera ficha de titular, mirando
  TODO el historial desde 2019. Recien despues se filtra la ventana de
  cohortes: asi no entra como nuevo quien ya compraba antes.
- Compra del dia 0: todas sus fichas de titular compradas ese dia. La ficha
  ancla es la de mas pasajeros (y, a igualdad, la de numero menor).
- Quedan afuera: quien entro con una ficha corporativa el dia 0 y quien era
  menor de 18 ese dia (verificado por fecha de nacimiento).
- Vuelve a 12 meses: tiene otra ficha facturada, como titular o como
  pasajero, comprada despues del dia 0 y hasta 12 meses despues, cuya fecha
  de viaje esta a mas de 7 dias de la del primer viaje.
- Las fichas en PROCESO no cuentan en ningun lado.
"""
import datetime

TABLAS = ("timeline", "ficha", "ficha_persona", "contactos", "persona",
          "pagador", "servicio", "vendedor_codigo")

MESES_VENTANA = 12
DIAS_MISMO_VIAJE = 7

# El regimen viene como texto libre. Se mira en este orden; gana el primero.
REGIMENES = (
    ("todo_incluido", ("ALL INCLUSIVE", "TODO INCLUIDO", "TUDO INCLU")),
    ("pension_completa", ("PENSION COMPLETA", "FULL BOARD")),
    ("media_pension", ("MEDIA PENSION", "HALF BOARD", "MEIA PENS")),
    ("desayuno", ("DESAYUNO", "BREAKFAST", "CAFE DA MANHA")),
    ("solo_alojamiento", ("EUROPEAN PLAN", "SOLO HABITACION", "SOLO ALOJAMIENTO",
                          "ROOM ONLY", "SIN COMIDAS")),
)
ORDEN_REGIMEN = ["todo_incluido", "pension_completa", "media_pension", "desayuno",
                 "solo_alojamiento", "otro"]


def cargar_foto(con, carpeta):
    """Lee los CSV de la foto y deja tablas tipadas, solo con lo que se usa."""
    carpeta = carpeta.replace("\\", "/")
    for t in TABLAS:
        con.execute("CREATE OR REPLACE TABLE crudo_%s AS SELECT * FROM read_csv("
                    "'%s/%s.csv', header=true, all_varchar=true)" % (t, carpeta, t))
    con.execute("""
        CREATE OR REPLACE TABLE tl_todo AS
        SELECT master_customer_id AS cid, CAST(fic_numero AS BIGINT) AS fic,
               CAST(es_titular AS BOOLEAN) AS es_tit,
               CAST(fecha_compra AS DATE) AS fc, CAST(fecha_viaje AS DATE) AS fv,
               CAST(fecha_regreso AS DATE) AS fr,
               CAST(es_venta_confirmada AS BOOLEAN) AS confirmada,
               vendedor_cod AS vend_cod, vendedor_persona_id AS vend_pid,
               CAST(monto_venta_usd AS DOUBLE) AS venta, CAST(utilidad_usd AS DOUBLE) AS util,
               CAST(total_pax AS INTEGER) AS pax,
               destino_principal_pais AS pais, tipo_producto,
               CAST(tiene_seguro AS BOOLEAN) AS seguro
        FROM crudo_timeline
        WHERE fecha_compra IS NOT NULL""")
    con.execute("CREATE OR REPLACE TABLE tl AS SELECT * FROM tl_todo WHERE confirmada")
    con.execute("""
        CREATE OR REPLACE TABLE fi AS
        SELECT CAST(fic_numero AS BIGINT) AS fic, CAST(es_corporativa AS BOOLEAN) AS es_corp,
               CAST(n_hoteles AS INTEGER) AS n_hoteles, CAST(n_destinos AS INTEGER) AS n_destinos
        FROM crudo_ficha""")
    con.execute("""
        CREATE OR REPLACE TABLE fp AS
        SELECT DISTINCT master_customer_id AS cid, tit_cod, CAST(fic_numero AS BIGINT) AS fic
        FROM crudo_ficha_persona""")
    con.execute("""
        CREATE OR REPLACE TABLE ct AS
        SELECT tit_cod, master_customer_id AS cid,
               CAST(tiene_mail AS BOOLEAN) AS mail, CAST(tiene_telefono AS BOOLEAN) AS tel,
               CAST(tiene_documento AS BOOLEAN) AS doc, CAST(tiene_nacimiento AS BOOLEAN) AS nac
        FROM crudo_contactos""")
    con.execute("""
        CREATE OR REPLACE TABLE pe AS
        SELECT master_customer_id AS cid, genero, CAST(nacimiento_mes AS DATE) AS nac_mes,
               pais_nacionalidad AS nacionalidad, CAST(n_registros_atlas AS INTEGER) AS n_reg,
               CAST(tiene_mail AS BOOLEAN) AS mail, CAST(tiene_telefono AS BOOLEAN) AS tel,
               CAST(tiene_documento AS BOOLEAN) AS doc
        FROM crudo_persona""")
    con.execute("""
        CREATE OR REPLACE TABLE pg AS
        SELECT CAST(fic_numero AS BIGINT) AS fic, pagador_categoria AS cat,
               CAST(es_millas AS BOOLEAN) AS millas, master_customer_id AS pcid
        FROM crudo_pagador""")
    casos = " ".join(
        "WHEN %s THEN '%s'" % (" OR ".join("contains(r, '%s')" % p for p in patrones), nombre)
        for nombre, patrones in REGIMENES)
    con.execute("""
        CREATE OR REPLACE TABLE sv AS
        SELECT fic, tipo, iata,
               CASE WHEN r IS NULL THEN NULL %s ELSE 'otro' END AS regimen
        FROM (SELECT CAST(fic_numero AS BIGINT) AS fic, srv_tipo_nom AS tipo,
                     aerolinea_iata AS iata,
                     strip_accents(upper(hotel_regimen)) AS r
              FROM crudo_servicio
              WHERE NOT coalesce(CAST(es_nota_devolucion AS BOOLEAN), false))""" % casos)
    con.execute("""
        CREATE OR REPLACE TABLE vc AS
        SELECT ven_cod, any_value(vendedor_persona_id) AS pid, bool_and(CAST(es_persona AS BOOLEAN)) AS es_persona
        FROM crudo_vendedor_codigo GROUP BY ven_cod""")
    for t in TABLAS:
        con.execute("DROP TABLE crudo_%s" % t)


def _fecha(texto):
    return datetime.date.fromisoformat(str(texto)).isoformat()


def construir_interna(con, cohorte_desde, cohorte_hasta):
    """Crea la tabla `interna`: una fila por cliente del universo."""
    desde, hasta = _fecha(cohorte_desde), _fecha(cohorte_hasta)

    # una fila por ficha facturada
    con.execute("""
        CREATE OR REPLACE TABLE fch AS
        SELECT t.fic, any_value(t.fc) AS fc, any_value(t.fv) AS fv, any_value(t.fr) AS fr,
               any_value(t.venta) AS venta, any_value(t.util) AS util, any_value(t.pax) AS pax,
               any_value(t.pais) AS pais, any_value(t.tipo_producto) AS tipo_producto,
               bool_or(t.seguro) AS seguro,
               coalesce(any_value(t.vend_pid), 'cod:' || any_value(t.vend_cod)) AS vend_clave,
               coalesce(any_value(vc.es_persona), any_value(t.vend_pid) IS NOT NULL) AS vend_es_persona
        FROM tl t LEFT JOIN vc ON vc.ven_cod = t.vend_cod
        GROUP BY t.fic""")

    # primera compra como titular, sobre TODO el historial
    con.execute("""
        CREATE OR REPLACE TABLE primera AS
        SELECT DISTINCT ON (cid) cid, fic AS fic1, fc AS f1, fv AS v1, fr AS r1
        FROM tl WHERE es_tit
        ORDER BY cid, fc, pax DESC NULLS LAST, fic""")
    con.execute("""
        CREATE OR REPLACE TABLE dia0 AS
        SELECT DISTINCT p.cid, t.fic
        FROM primera p JOIN tl t ON t.cid = p.cid AND t.es_tit AND t.fc = p.f1""")

    con.execute("""
        CREATE OR REPLACE TABLE universo AS
        SELECT p.*,
               CASE WHEN pe.nac_mes IS NULL THEN NULL
                    ELSE year(p.f1) - year(pe.nac_mes)
                         - CASE WHEN month(p.f1) < month(pe.nac_mes) THEN 1 ELSE 0 END
               END AS edad
        FROM primera p LEFT JOIN pe USING (cid)
        WHERE p.f1 BETWEEN DATE '%s' AND DATE '%s'
          AND p.cid NOT IN (SELECT d.cid FROM dia0 d JOIN fi USING (fic) WHERE fi.es_corp)
        """ % (desde, hasta))
    con.execute("DELETE FROM universo WHERE edad IS NOT NULL AND edad < 18")

    def vuelta(tabla):
        return ("%s.fc > u.f1 AND %s.fc <= u.f1 + INTERVAL %d MONTH "
                "AND (%s.fv IS NULL OR u.v1 IS NULL OR abs(date_diff('day', u.v1, %s.fv)) > %d)"
                % (tabla, tabla, MESES_VENTANA, tabla, tabla, DIAS_MISMO_VIAJE))

    con.execute("""
        CREATE OR REPLACE TABLE etiqueta AS
        SELECT u.cid,
               coalesce(bool_or(t.confirmada AND %(v)s), false) AS vuelve_12,
               coalesce(bool_or(t.confirmada AND t.es_tit AND %(v)s), false) AS vuelve_12_comprando,
               coalesce(bool_or(%(v)s), false) AS vuelve_12_con_proceso,
               count(DISTINCT t.fic) FILTER (WHERE t.confirmada AND t.fc < u.f1) AS n_prev_pasajero
        FROM universo u JOIN tl_todo t USING (cid)
        GROUP BY u.cid""" % {"v": vuelta("t")})

    # la compania: las otras personas de las fichas del dia 0
    con.execute("""
        CREATE OR REPLACE TABLE compania AS
        WITH c AS (SELECT DISTINCT d.cid, o.cid AS oid
                   FROM dia0 d JOIN universo u ON u.cid = d.cid
                   JOIN tl o ON o.fic = d.fic AND o.cid <> d.cid),
        h AS (SELECT c.cid, c.oid,
                     bool_or(t.fc < u.f1) AS con_historial,
                     bool_or(t.fc < u.f1 AND t.es_tit) AS cliente_previo
              FROM c JOIN universo u ON u.cid = c.cid JOIN tl t ON t.cid = c.oid
              GROUP BY c.cid, c.oid)
        SELECT cid, count(*) AS n_comp,
               count(*) FILTER (WHERE con_historial) AS n_comp_historial,
               count(*) FILTER (WHERE cliente_previo) AS n_comp_cliente_previo
        FROM h GROUP BY cid""")

    con.execute("""
        CREATE OR REPLACE TABLE compra AS
        SELECT d.cid, sum(f.venta) AS venta, sum(f.util) AS utilidad, max(f.pax) AS pax,
               bool_or(f.seguro) AS tiene_seguro,
               bool_or(coalesce(fi.n_hoteles, 0) > 0) AS lleva_hotel
        FROM dia0 d JOIN universo u ON u.cid = d.cid JOIN fch f USING (fic) LEFT JOIN fi USING (fic)
        GROUP BY d.cid""")

    con.execute("""
        CREATE OR REPLACE TABLE servicios AS
        WITH s AS (SELECT d.cid, sv.* FROM dia0 d JOIN universo u ON u.cid = d.cid JOIN sv USING (fic)),
        aero AS (SELECT DISTINCT ON (cid) cid, iata
                 FROM (SELECT cid, iata, count(*) AS k FROM s WHERE iata IS NOT NULL GROUP BY cid, iata)
                 ORDER BY cid, k DESC, iata),
        reg AS (SELECT DISTINCT ON (cid) cid, regimen
                FROM s WHERE regimen IS NOT NULL
                ORDER BY cid, list_position(%s, regimen))
        SELECT n.cid, n.n_servicios, aero.iata AS aerolinea_iata, reg.regimen
        FROM (SELECT cid, count(*) AS n_servicios FROM s GROUP BY cid) n
        LEFT JOIN aero USING (cid) LEFT JOIN reg USING (cid)""" % ORDEN_REGIMEN)

    con.execute("""
        CREATE OR REPLACE TABLE pago AS
        SELECT d.cid,
               bool_or(pg.millas) AS canje_millas,
               CASE WHEN bool_or(pg.cat = 'persona_fisica' AND pg.pcid = d.cid) THEN 'cliente'
                    WHEN bool_or(pg.cat IN ('persona_fisica', 'empresa')) THEN 'tercero'
                    WHEN bool_or(pg.millas) THEN 'solo_millas'
                    ELSE 'sin_dato' END AS pagador
        FROM dia0 d JOIN universo u ON u.cid = d.cid JOIN pg USING (fic)
        GROUP BY d.cid""")

    con.execute("""
        CREATE OR REPLACE TABLE vend AS
        WITH inicio AS (SELECT vend_clave, min(fc) AS v0 FROM fch GROUP BY vend_clave)
        SELECT u.cid, a.vend_clave, a.vend_es_persona,
               date_diff('day', i.v0, u.f1) AS vend_antiguedad_dias,
               (SELECT count(*) FROM fch o
                 WHERE o.vend_clave = a.vend_clave
                   AND o.fc >= u.f1 - INTERVAL 12 MONTH AND o.fc < u.f1) AS vend_fichas_12m
        FROM universo u JOIN fch a ON a.fic = u.fic1
        LEFT JOIN inicio i ON i.vend_clave = a.vend_clave""")

    con.execute("""
        CREATE OR REPLACE TABLE dia0_ficha AS
        SELECT d.cid, bool_or(ct.mail) AS mail, bool_or(ct.tel) AS tel,
               bool_or(ct.doc) AS doc, bool_or(ct.nac) AS nac
        FROM dia0 d JOIN universo u ON u.cid = d.cid
        JOIN fp ON fp.cid = d.cid AND fp.fic = d.fic
        JOIN ct ON ct.tit_cod = fp.tit_cod
        GROUP BY d.cid""")

    # ficha unica: lo que hoy se sabe de la persona, en su ficha canonica o
    # en cualquiera de sus registros. Asi nunca sabe menos que la del dia 0.
    con.execute("""
        CREATE OR REPLACE TABLE registros AS
        SELECT cid, bool_or(mail) AS mail, bool_or(tel) AS tel,
               bool_or(doc) AS doc, bool_or(nac) AS nac
        FROM ct GROUP BY cid""")

    con.execute("""
        CREATE OR REPLACE TABLE interna AS
        SELECT u.cid, u.f1, u.v1, year(u.f1) AS cohorte,
               e.vuelve_12, e.vuelve_12_comprando, e.vuelve_12_con_proceso,
               e.n_prev_pasajero,
               coalesce(c.n_comp, 0) AS n_comp,
               coalesce(c.n_comp_historial, 0) AS n_comp_historial,
               coalesce(c.n_comp_cliente_previo, 0) AS n_comp_cliente_previo,
               k.pax, k.venta, k.utilidad,
               date_diff('day', u.f1, u.v1) AS anticipacion_dias,
               date_diff('day', u.v1, u.r1) AS noches,
               a.pais, a.tipo_producto, k.tiene_seguro, k.lleva_hotel,
               fi.n_destinos, coalesce(s.n_servicios, 0) AS n_servicios,
               s.aerolinea_iata, s.regimen,
               coalesce(p.canje_millas, false) AS canje_millas,
               coalesce(p.pagador, 'sin_dato') AS pagador,
               v.vend_clave, v.vend_es_persona, v.vend_fichas_12m, v.vend_antiguedad_dias,
               coalesce(pe.mail, false) OR coalesce(rg.mail, false) AS fu_tiene_mail,
               coalesce(pe.tel, false) OR coalesce(rg.tel, false) AS fu_tiene_telefono,
               coalesce(pe.doc, false) OR coalesce(rg.doc, false) AS fu_tiene_documento,
               pe.nac_mes IS NOT NULL OR coalesce(rg.nac, false) AS fu_tiene_nacimiento,
               pe.n_reg AS fu_registros,
               u.edad,
               CASE WHEN pe.genero IN ('F', 'M') THEN pe.genero END AS genero,
               pe.nacionalidad,
               d.mail AS d0_tiene_mail, d.tel AS d0_tiene_telefono,
               d.doc AS d0_tiene_documento, d.nac AS d0_tiene_nacimiento
        FROM universo u
        JOIN etiqueta e USING (cid)
        JOIN compra k USING (cid)
        JOIN fch a ON a.fic = u.fic1
        LEFT JOIN fi ON fi.fic = u.fic1
        LEFT JOIN compania c USING (cid)
        LEFT JOIN servicios s USING (cid)
        LEFT JOIN pago p USING (cid)
        LEFT JOIN vend v USING (cid)
        LEFT JOIN pe USING (cid)
        LEFT JOIN registros rg USING (cid)
        LEFT JOIN dia0_ficha d USING (cid)""")
