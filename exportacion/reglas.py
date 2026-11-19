"""El contrato de la tabla que sale de la empresa.

Todo lo que puede aparecer en `datos/tabla_modelo.csv` esta enumerado aca:
que columnas, en que orden y que valores admite cada una. No hay ninguna
columna de texto libre. El paso 2 arma la tabla con estas reglas y el paso 3
la rechaza si encuentra algo fuera de ellas.
"""

SIN_DATO = "sin_dato"
BINARIA = ["0", "1"]

# ---------------------------------------------------------------- cohortes
COHORTE_DESDE = "2023-01-01"     # Jetmar no tiene detalle de servicios antes
COHORTE_HASTA = "2025-08-31"     # deja 12 meses de ventana + margen de facturacion
BLOQUE_POR_COHORTE = {2023: "entrenamiento", 2024: "validacion", 2025: "prueba"}
BLOQUES = ["entrenamiento", "validacion", "prueba"]

# ----------------------------------------------------------------- destino
PAISES = ["BR", "AR", "ES", "US", "MX", "CL", "DO", "UY", "IT", "CO", "GE", "PE", "GB", "PY"]
OTRO = "otro"
REGIONES = ["brasil", "sudamerica", "europa", "caribe", "norteamerica",
            "asia_oceania_africa", "uruguay", OTRO]
_REGION = {
    "brasil": ["BR"],
    "uruguay": ["UY"],
    "sudamerica": ["AR", "BO", "CL", "CO", "EC", "GY", "PE", "PY", "SR", "VE"],
    "norteamerica": ["CA", "US"],
    "caribe": ["AN", "AW", "BB", "BS", "BZ", "CR", "CU", "DO", "GT", "HN", "JM", "KY",
               "MX", "NI", "PA", "PR", "SV", "TT"],
    "europa": ["AT", "BE", "CH", "CY", "CZ", "DE", "DK", "ES", "FI", "FR", "GB", "GE",
               "GR", "HR", "HU", "IE", "IS", "IT", "LU", "MT", "NL", "NO", "PL", "PT",
               "RO", "RU", "SE", "TR"],
    "asia_oceania_africa": ["AE", "AU", "CN", "EG", "ET", "ID", "IL", "IN", "IR", "JP",
                            "KE", "KR", "KZ", "MA", "MY", "NZ", "PG", "PH", "QA", "SA",
                            "SG", "TH", "TZ", "VN", "ZA"],
}
REGION_DE_PAIS = {p: r for r, ps in _REGION.items() for p in ps}

# ---------------------------------------------------------------- producto
TIPOS_PRODUCTO = {"solo_aereo": "solo_aereo", "aereo+hotel": "aereo_hotel",
                  "paquete": "paquete", "solo_hotel": "solo_hotel",
                  "crucero": "maritimo",      # en la base "crucero" es Buquebus
                  "otro": OTRO}
AEROLINEAS = {"LA": "latam", "CM": "copa", "G3": "gol", "IB": "iberia",
              "UX": "air_europa", "AR": "aerolineas_argentinas", "H2": "sky",
              "AV": "avianca", "JA": "jetsmart", "WJ": "jetsmart", "AD": "azul",
              "AA": "american"}
SIN_AEREO = "sin_aereo"
OTRA = "otra"
REGIMENES = {"desayuno": "desayuno", "solo_alojamiento": "solo_alojamiento",
             "todo_incluido": "todo_incluido", "media_pension": "pension",
             "pension_completa": "pension", "otro": OTRO}
SIN_HOTEL = "sin_hotel"

# ------------------------------------------------------------------ bandas
# (limites superiores inclusivos, etiquetas, minimo valido)
BANDAS = {
    "pasajeros": ([1, 2, 3, 4, 9], ["1", "2", "3", "4", "5-9", "10+"], 1),
    "viajes_previos_acompaniante": ([0, 1, 2], ["0", "1", "2", "3+"], 0),
    "servicios": ([1, 2, 4, 7], ["1", "2", "3-4", "5-7", "8+"], 1),
    "destinos": ([1, 2], ["1", "2", "3+"], 1),
    "noches": ([3, 7, 14], ["0-3", "4-7", "8-14", "15+"], 0),
    "anticipacion": ([7, 14, 30, 60, 90, 180],
                     ["0-7", "8-14", "15-30", "31-60", "61-90", "91-180", "181+"], 0),
    "vendedor_fichas_12m": ([49, 149, 299, 499],
                            ["0-49", "50-149", "150-299", "300-499", "500+"], 0),
    # en dias: menos de 1 anio, de 1 a 3, 4 o mas. La base arranca en 2019,
    # asi que "4+" quiere decir "desde antes de 2020".
    "vendedor_antiguedad": ([364, 1460], ["menos_de_1", "1-3", "4+"], 0),
    "fu_registros": ([1, 2], ["1", "2", "3+"], 1),
}
# Para la banda 5-9 el gasto por pasajero se calcula con este tamanio, para
# que dividir venta / gasto por pasajero no delate el tamanio exacto del
# grupo. De 10 en adelante no se publica.
PASAJEROS_REPRESENTATIVO = {"5-9": 6}
PASAJEROS_SIN_POR_PASAJERO = ["10+", SIN_DATO]

# ------------------------------------------------------------------ montos
TOPE_VENTA = 30000
TOPE_VENTA_POR_PASAJERO = 10000
TOPE_INDICE = (-100, 2000)

# -------------------------------------------------------------- vendedores
VENDEDOR_MINIMO = 50              # con menos clientes en la tabla -> V-otros
VENDEDOR_OTROS = "V-otros"

# ------------------------------------------------------------- el contrato
CONTRATO = [
    # identificacion y particion
    ("cliente", {"tipo": "codigo", "patron": r"C-\d{5}", "identificador": True}),
    ("cohorte", {"tipo": "categoria", "valores": ["2023", "2024", "2025"]}),
    ("bloque", {"tipo": "categoria", "valores": BLOQUES}),
    ("bloque_60_20_20", {"tipo": "categoria", "valores": BLOQUES}),
    # etiqueta
    ("vuelve_12", {"tipo": "categoria", "valores": BINARIA}),
    ("vuelve_12_comprando", {"tipo": "categoria", "valores": BINARIA}),
    # la compania
    ("fue_acompaniante_antes", {"tipo": "categoria", "valores": BINARIA}),
    ("viajes_previos_acompaniante", {"tipo": "categoria", "valores": BANDAS["viajes_previos_acompaniante"][1]}),
    ("viaja_con_cliente_previo", {"tipo": "categoria", "valores": BINARIA}),
    ("viaja_con_alguien_con_historial", {"tipo": "categoria", "valores": BINARIA}),
    ("pasajeros", {"tipo": "categoria", "valores": BANDAS["pasajeros"][1] + [SIN_DATO]}),
    # la compra
    ("venta_usd", {"tipo": "monto", "tope": TOPE_VENTA, "vacio": True}),
    ("venta_por_pasajero_usd", {"tipo": "monto", "tope": TOPE_VENTA_POR_PASAJERO, "vacio": True}),
    ("utilidad_indice", {"tipo": "indice", "topes": TOPE_INDICE}),
    ("canje_millas", {"tipo": "categoria", "valores": BINARIA}),
    ("pagador", {"tipo": "categoria", "valores": ["cliente", "tercero", "solo_millas", SIN_DATO]}),
    ("tipo_producto", {"tipo": "categoria", "valores": sorted(set(TIPOS_PRODUCTO.values())) + [SIN_DATO]}),
    ("tiene_seguro", {"tipo": "categoria", "valores": BINARIA}),
    ("lleva_hotel", {"tipo": "categoria", "valores": BINARIA}),
    ("regimen_hotel", {"tipo": "categoria", "valores": sorted(set(REGIMENES.values())) + [SIN_HOTEL, SIN_DATO]}),
    ("aerolinea", {"tipo": "categoria", "valores": sorted(set(AEROLINEAS.values())) + [OTRA, SIN_AEREO, SIN_DATO]}),
    ("servicios", {"tipo": "categoria", "valores": BANDAS["servicios"][1] + [SIN_DATO]}),
    # el viaje
    ("region_destino", {"tipo": "categoria", "valores": REGIONES + [SIN_DATO]}),
    ("pais_destino", {"tipo": "categoria", "valores": PAISES + [OTRO, SIN_DATO]}),
    ("destinos", {"tipo": "categoria", "valores": BANDAS["destinos"][1] + [SIN_DATO]}),
    ("noches", {"tipo": "categoria", "valores": BANDAS["noches"][1] + [SIN_DATO]}),
    ("anticipacion", {"tipo": "categoria", "valores": BANDAS["anticipacion"][1] + [SIN_DATO]}),
    # el vendedor
    ("vendedor", {"tipo": "codigo", "patron": r"V-(\d{3}|otros)"}),
    ("vendedor_es_persona", {"tipo": "categoria", "valores": BINARIA}),
    ("vendedor_fichas_12m", {"tipo": "categoria", "valores": BANDAS["vendedor_fichas_12m"][1]}),
    ("vendedor_antiguedad", {"tipo": "categoria", "valores": BANDAS["vendedor_antiguedad"][1] + [SIN_DATO]}),
    # ficha unica: el estado de HOY. Trae fuga de informacion (H3).
    ("fu_tiene_mail", {"tipo": "categoria", "valores": BINARIA}),
    ("fu_tiene_telefono", {"tipo": "categoria", "valores": BINARIA}),
    ("fu_tiene_documento", {"tipo": "categoria", "valores": BINARIA}),
    ("fu_tiene_nacimiento", {"tipo": "categoria", "valores": BINARIA}),
    ("fu_registros", {"tipo": "categoria", "valores": BANDAS["fu_registros"][1]}),
    # ficha del dia 0: lo que tenia el registro usado en la primera compra
    ("d0_tiene_mail", {"tipo": "categoria", "valores": BINARIA}),
    ("d0_tiene_telefono", {"tipo": "categoria", "valores": BINARIA}),
    ("d0_tiene_documento", {"tipo": "categoria", "valores": BINARIA}),
    ("d0_tiene_nacimiento", {"tipo": "categoria", "valores": BINARIA}),
]
COLUMNAS = [c for c, _ in CONTRATO]

# ------------------------------------------------------------ anonimato
# Lo que alguien de afuera puede saber del primer viaje de un conocido:
# cuando, a donde, con cuantos, por cuanto tiempo y que tipo de viaje.
# Cada combinacion tiene que repetirse en al menos K_1 clientes.
CUASI_1 = ["cohorte", "region_destino", "pais_destino", "pasajeros", "noches",
           "tipo_producto", "lleva_hotel"]
K_1 = 5
# Lo mismo, sabiendo ademas la aerolinea, el regimen del hotel y cuantos
# destinos tuvo el viaje.
DETALLE = ["aerolinea", "regimen_hotel", "destinos"]
CUASI_2 = CUASI_1 + DETALLE
K_2 = 3
# Ninguna categoria de ninguna columna puede tener menos clientes que esto.
MINIMO_POR_CATEGORIA = 20
