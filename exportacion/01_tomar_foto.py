"""Paso 1 · Toma una foto MINIMA de la base, para armar la tabla del modelo.

    py exportacion/01_tomar_foto.py

Solo corre adentro de la empresa, con la VPN levantada. Lee el DSN de
`~/.claude.json` en el momento (no lo imprime ni lo guarda) y abre la
conexion en solo lectura.

Que trae y que no
-----------------
Trae unicamente las columnas que hacen falta para calcular las variables del
dia 0 y la etiqueta. NO trae nombres, apellidos, documentos, mails, telefonos,
descripciones de ficha ni listas de acompaniantes: de los datos de contacto
solo viaja si estan cargados o no (`IS NOT NULL`), y de la fecha de nacimiento
solo el mes y el anio.

La foto queda FUERA de OneDrive y fuera del repo, en
`~/datos/ml_vueltas/foto_<fecha>/`, con un `manifiesto.json`. Sigue siendo dato
interno: lleva los ids de la base. Lo unico que sale de la empresa es la tabla
que arma el paso 2 y aprueba el paso 3.
"""
import datetime
import json
import os
import sys

import duckdb
import psycopg

RAIZ = os.path.join(os.path.expanduser("~"), "datos", "ml_vueltas")

CONSULTAS = {
    # persona x ficha: el hecho. Todo el historial (desde 2019), porque la
    # primera compra se calcula sobre el historial completo.
    "timeline": """
        SELECT master_customer_id, fic_numero, rol_en_ficha, es_titular,
               fecha_compra, fecha_viaje, fecha_regreso,
               estado, es_venta_confirmada,
               vendedor_cod, vendedor_persona_id,
               (vendedor_cod_2 IS NOT NULL) AS tiene_vendedor_2,
               monto_venta_usd, monto_cuotaparte_usd, utilidad_usd,
               total_pax, n_participantes,
               destino_principal_pais, tipo_producto, tiene_seguro
        FROM gold.mart_jetuy_persona_timeline""",
    "ficha": """
        SELECT fic_numero, fic_estado, fic_apertura, fic_viaje, fic_facturacion,
               fic_venta_usd, fic_utilidad_usd, total_pax, pax_ficha,
               es_corporativa, tipo_ficha,
               n_vuelos, n_hoteles, n_seguros, n_paquetes, n_maritimo, n_traslados,
               n_noches_alojamiento, fecha_inicio, fecha_fin, duracion_dias,
               destino_principal_pais, n_destinos, destino_regla
        FROM gold.fact_ficha
        WHERE empresa_key = 'JETUY'""",
    # que registro (tit_cod) uso cada persona en cada ficha: es el puente
    # para reconstruir la ficha del dia 0.
    "ficha_persona": """
        SELECT master_customer_id, tit_cod, fic_numero, rol
        FROM gold.fact_ficha_persona
        WHERE empresa_key = 'JETUY'""",
    # un registro por tit_cod. De los datos de contacto, solo si estan.
    "contactos": """
        SELECT tit_cod, master_customer_id,
               (email IS NOT NULL AND email <> '')                 AS tiene_mail,
               (telefono_e164 IS NOT NULL AND telefono_e164 <> '') AS tiene_telefono,
               (doc_numero IS NOT NULL AND doc_numero <> '')       AS tiene_documento,
               (anio_nacimiento IS NOT NULL)                       AS tiene_nacimiento,
               fecha_alta_atlas, evidencia
        FROM gold.mart_jetuy_persona_contactos""",
    # la ficha unica (dim_persona): el estado de hoy de cada persona.
    "persona": """
        SELECT d.master_customer_id, d.genero,
               date_trunc('month', d.fecha_nacimiento)::date       AS nacimiento_mes,
               d.pais_nacionalidad, d.n_registros_atlas,
               (d.email_canonico IS NOT NULL AND d.email_canonico <> '') AS tiene_mail,
               (d.cel_canonico IS NOT NULL AND d.cel_canonico <> '')     AS tiene_telefono,
               (d.doc_canonico IS NOT NULL AND d.doc_canonico <> '')     AS tiene_documento
        FROM gold.dim_persona d
        WHERE d.master_customer_id IN (
            SELECT master_customer_id FROM gold.mart_jetuy_persona_timeline)""",
    # quien pago. El codigo 106176 es el canje de millas (Itau Volar).
    "pagador": """
        SELECT fic_numero, pagador_categoria, pagador_doc_tipo,
               (pagador_cod = '106176') AS es_millas,
               master_customer_id, pct_aporte_ficha
        FROM gold.fact_ficha_pagador
        WHERE empresa_key = 'JETUY'""",
    # detalle de servicios: aerolinea, regimen y categoria del hotel.
    "servicio": """
        SELECT fic_numero, orden_servicio, srv_tipo_nom, familia_template,
               hotel_categoria, hotel_regimen, hotel_noches,
               aerolinea_iata, aerolinea_nom, n_tramos, destino_pais_cod,
               fecha_desde, fecha_hasta, srv_venta_usd, pax_cantidad,
               estado_servicio, es_nota_devolucion, es_venta_confirmada,
               fecha_devolucion
        FROM gold.mart_jetuy_ficha_servicio""",
    "vendedor_codigo": """
        SELECT ven_cod, vendedor_persona_id, es_persona
        FROM gold.dim_vendedor_codigo
        WHERE empresa_key = 'JETUY'""",
}


def dsn_de_config():
    """Busca la primera clave DSN en ~/.claude.json. Nunca se imprime."""
    ruta = os.path.join(os.path.expanduser("~"), ".claude.json")
    with open(ruta, encoding="utf-8") as fh:
        cfg = json.load(fh)

    def buscar(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "DSN" and isinstance(v, str) and v.strip():
                    return v
                hit = buscar(v)
                if hit:
                    return hit
        elif isinstance(o, list):
            for v in o:
                hit = buscar(v)
                if hit:
                    return hit
        return None

    dsn = buscar(cfg)
    if not dsn:
        raise SystemExit("no hay ninguna clave DSN en ~/.claude.json")
    return dsn


def main():
    hoy = datetime.date.today().isoformat()
    destino = os.path.join(RAIZ, "foto_" + hoy)
    if "OneDrive" in destino:
        raise SystemExit("la foto no puede quedar dentro de OneDrive: " + destino)
    os.makedirs(destino, exist_ok=True)

    manifiesto = {"tomado": datetime.datetime.now().isoformat(timespec="seconds"),
                  "base": "serving", "schema": "gold", "tablas": []}
    duck = duckdb.connect()
    with psycopg.connect(dsn_de_config(), connect_timeout=20) as con:
        con.read_only = True
        for nombre, sql in CONSULTAS.items():
            ruta = os.path.join(destino, nombre + ".csv")
            with con.cursor() as cur, open(ruta, "wb") as fh:
                with cur.copy("COPY (%s) TO STDOUT WITH (FORMAT csv, HEADER true)" % sql) as copia:
                    for bloque in copia:
                        fh.write(bloque)
                filas_copy = cur.rowcount
            filas_csv = duck.execute(
                "SELECT count(*) FROM read_csv('%s', header=true, all_varchar=true)"
                % ruta.replace("\\", "/")).fetchone()[0]
            columnas = [r[0] for r in duck.execute(
                "DESCRIBE SELECT * FROM read_csv('%s', header=true, all_varchar=true)"
                % ruta.replace("\\", "/")).fetchall()]
            ok = filas_copy == filas_csv
            manifiesto["tablas"].append({
                "tabla": nombre, "archivo": nombre + ".csv", "filas_copy": filas_copy,
                "filas_csv": filas_csv, "columnas": columnas, "verificado": ok,
                "mb": round(os.path.getsize(ruta) / 1e6, 1)})
            print("%-16s %9d filas · %6.1f MB · %s" % (
                nombre, filas_csv, os.path.getsize(ruta) / 1e6,
                "ok" if ok else "DIFIERE de COPY (%d)" % filas_copy), flush=True)
        manifiesto["ultima_compra"] = str(con.execute(
            "SELECT max(fecha_compra) FROM gold.mart_jetuy_persona_timeline").fetchone()[0])

    with open(os.path.join(destino, "manifiesto.json"), "w", encoding="utf-8") as fh:
        json.dump(manifiesto, fh, indent=2, ensure_ascii=False)
    print("foto en %s · ultima compra %s" % (destino, manifiesto["ultima_compra"]))
    return 0 if all(t["verificado"] for t in manifiesto["tablas"]) else 1


if __name__ == "__main__":
    sys.exit(main())
