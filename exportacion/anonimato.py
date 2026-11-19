"""Convierte la tabla interna en la tabla que sale, y la verifica.

Dos mitades:

- `armar_publica` toma las filas internas (ids de la base, fechas y montos
  exactos) y devuelve la tabla publica: codigos al azar, bandas, montos
  redondeados y supresion de valores en los grupos chicos.
- `revisar_todo` mira SOLO la tabla publica, sin saber como se armo, y
  devuelve la lista de problemas. Lista vacia = se puede entregar.
"""
import collections
import datetime
import random
import re

from exportacion import reglas as R

SD = R.SIN_DATO


# ------------------------------------------------------------ bandas y montos
def banda(valor, limites, etiquetas, minimo=None):
    """Etiqueta de la banda de `valor`. Los limites son superiores e inclusivos."""
    if valor is None or (minimo is not None and valor < minimo):
        return SD
    for limite, etiqueta in zip(limites, etiquetas):
        if valor <= limite:
            return etiqueta
    return etiquetas[-1]


def _banda(nombre, valor):
    limites, etiquetas, minimo = R.BANDAS[nombre]
    return banda(valor, limites, etiquetas, minimo)


def redondear_monto(x, tope):
    """USD redondeados: de a 50 hasta 1.000, de a 100 hasta 5.000, de a 500
    hasta 20.000 y de a 1.000 despues; nunca por encima del tope."""
    if x is None or x <= 0:
        return None
    if x >= tope:
        return tope
    paso = 50 if x < 1000 else 100 if x < 5000 else 500 if x < 20000 else 1000
    return min(max(int(x / paso + 0.5) * paso, 50), tope)


def redondear_indice(x, topes):
    """Indice redondeado: de a 5 hasta 100, de a 10 hasta 1.000, de a 50 despues."""
    if x is None:
        return None
    bajo, alto = topes
    if x <= bajo:
        return bajo
    if x >= alto:
        return alto
    a = abs(x)
    paso = 5 if a < 100 else 10 if a < 1000 else 50
    r = int(a / paso + 0.5) * paso
    return max(bajo, min(alto, -r if x < 0 else r))


# -------------------------------------------------------------------- codigos
def asignar_codigos(ids, prefijo, ancho, semilla):
    """Codigos correlativos repartidos al azar. No son un hash del id: no hay
    forma de volver del codigo al id sin la tabla de correspondencia."""
    orden = sorted(set(ids))
    random.Random(semilla).shuffle(orden)
    return {original: "%s%0*d" % (prefijo, ancho, i) for i, original in enumerate(orden, 1)}


# ------------------------------------------------------------- grupos chicos
def _clave(fila, cuasi):
    return tuple(fila[c] for c in cuasi)


def filas_en_grupos_chicos(filas, cuasi, k):
    """Indices de las filas cuya combinacion de `cuasi` aparece menos de k veces."""
    cuenta = collections.Counter(_clave(f, cuasi) for f in filas)
    return [i for i, f in enumerate(filas) if cuenta[_clave(f, cuasi)] < k]


def generalizar(filas, cuasi, k, pasos):
    """Aplica cada paso, en orden, solo a las filas que siguen en grupos chicos.
    Devuelve (cuantas filas toco cada paso, indices que siguen en grupos chicos)."""
    informe = []
    for nombre, aplicar in pasos:
        chicas = filas_en_grupos_chicos(filas, cuasi, k)
        if not chicas:
            break
        for i in chicas:
            aplicar(filas[i])
        informe.append((nombre, len(chicas)))
    return informe, filas_en_grupos_chicos(filas, cuasi, k)


def asegurar_detalle(filas, cuasi_base, detalle, k, pasos):
    """Segunda capa. Dentro de cada grupo de `cuasi_base`, ningun subgrupo por
    `detalle` puede tener menos de k filas. Primero suprime de a un atributo
    (como `generalizar`). Si los que quedaron con todo el detalle suprimido no
    llegan a k, les suma filas del subgrupo mas grande que pueda prestar; y si
    nadie puede, suprime el detalle de todo el grupo."""
    informe, quedan = generalizar(filas, cuasi_base + detalle, k, pasos)
    prestadas = completos = 0

    def suprimir(fila):
        for _, aplicar in pasos:
            aplicar(fila)

    for base in sorted({_clave(filas[i], cuasi_base) for i in quedan}):
        grupo = [i for i, f in enumerate(filas) if _clave(f, cuasi_base) == base]
        while True:
            sub = collections.defaultdict(list)
            for i in grupo:
                sub[_clave(filas[i], detalle)].append(i)
            chicos = [i for idx in sub.values() if len(idx) < k for i in idx]
            if not chicos:
                break
            for i in chicos:
                suprimir(filas[i])
            vacio = _clave(filas[chicos[0]], detalle)
            suprimidas = sum(1 for i in grupo if _clave(filas[i], detalle) == vacio)
            faltan = k - suprimidas
            donantes = sorted((idx for clave, idx in sub.items() if clave != vacio and len(idx) > k),
                              key=len, reverse=True)
            for idx in donantes:
                while faltan > 0 and len(idx) > k:
                    suprimir(filas[idx.pop()])
                    prestadas += 1
                    faltan -= 1
            if faltan > 0:
                for i in grupo:
                    if _clave(filas[i], detalle) != vacio:
                        suprimir(filas[i])
                        completos += 1
                break
    if prestadas:
        informe.append(("prestadas", prestadas))
    if completos:
        informe.append(("grupo_completo", completos))
    return informe, filas_en_grupos_chicos(filas, cuasi_base + detalle, k)


def _sin_noches(f):
    f["noches"] = SD


def _sin_pais(f):
    if f["pais_destino"] != SD:
        f["pais_destino"] = R.OTRO


def _sin_pasajeros(f):
    f["pasajeros"] = SD
    f["venta_por_pasajero_usd"] = ""


def _sin_producto(f):
    # la aerolinea y el regimen dejan adivinar el tipo de producto: se van con el
    f["tipo_producto"] = SD
    f["aerolinea"] = SD
    f["regimen_hotel"] = SD


def _sin_region(f):
    f["region_destino"] = SD
    f["pais_destino"] = SD


def _sin_destinos(f):
    f["destinos"] = SD


def _sin_aerolinea(f):
    f["aerolinea"] = SD


def _sin_regimen(f):
    f["regimen_hotel"] = SD


PASOS_1 = [("noches", _sin_noches), ("pais_destino", _sin_pais), ("pasajeros", _sin_pasajeros),
           ("tipo_producto", _sin_producto), ("region_destino", _sin_region)]
PASOS_2 = [("aerolinea", _sin_aerolinea), ("regimen_hotel", _sin_regimen), ("destinos", _sin_destinos)]


# ------------------------------------------------------------------- particion
def cortes_60_20_20(fechas):
    """Dos inicios de mes que dejan cerca del 60% y del 80% de las fechas antes."""
    fechas = sorted(fechas)
    n = len(fechas)
    candidatos, d = [], fechas[0].replace(day=1)
    while d <= fechas[-1]:
        candidatos.append(d)
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    def mejor(objetivo, despues_de=None):
        validos = [c for c in candidatos if despues_de is None or c > despues_de]
        return min(validos, key=lambda c: abs(sum(f < c for f in fechas) / n - objetivo))

    c1 = mejor(0.60)
    return c1, mejor(0.80, c1)


# --------------------------------------------------------------- fila publica
def _bit(x):
    return "1" if x else "0"


def _texto(x):
    return "" if x is None else str(x)


def fila_publica(f, codigo_cliente, codigo_vendedor, cortes, k_utilidad):
    """Una fila interna -> una fila publica (todo texto), mas `_anio_viaje`,
    que se usa para medir grupos y se quita antes de escribir."""
    if f["utilidad"] is None:
        raise ValueError("cliente sin utilidad: revisar la foto")
    pasajeros = _banda("pasajeros", f["pax"])
    venta = redondear_monto(f["venta"], R.TOPE_VENTA)
    if venta is None or pasajeros in R.PASAJEROS_SIN_POR_PASAJERO:
        por_pasajero = None
    elif pasajeros in R.PASAJEROS_REPRESENTATIVO:
        por_pasajero = redondear_monto(venta / R.PASAJEROS_REPRESENTATIVO[pasajeros],
                                       R.TOPE_VENTA_POR_PASAJERO)
    else:
        por_pasajero = redondear_monto(f["venta"] / f["pax"], R.TOPE_VENTA_POR_PASAJERO)

    pais = f["pais"]
    if f["regimen"] is None:
        regimen = R.SIN_HOTEL if not f["lleva_hotel"] else R.OTRO
    else:
        regimen = R.REGIMENES.get(f["regimen"], R.OTRO)
    if f["aerolinea_iata"] is None:
        aerolinea = R.SIN_AEREO
    else:
        aerolinea = R.AEROLINEAS.get(f["aerolinea_iata"], R.OTRA)
    c1, c2 = cortes
    bloque_60 = "entrenamiento" if f["f1"] < c1 else "validacion" if f["f1"] < c2 else "prueba"

    p = {
        "cliente": codigo_cliente,
        "cohorte": str(f["cohorte"]),
        "bloque": R.BLOQUE_POR_COHORTE[f["cohorte"]],
        "bloque_60_20_20": bloque_60,
        "vuelve_12": _bit(f["vuelve_12"]),
        "vuelve_12_comprando": _bit(f["vuelve_12_comprando"]),
        "fue_acompaniante_antes": _bit(f["n_prev_pasajero"] > 0),
        "viajes_previos_acompaniante": _banda("viajes_previos_acompaniante", f["n_prev_pasajero"]),
        "viaja_con_cliente_previo": _bit(f["n_comp_cliente_previo"] > 0),
        "viaja_con_alguien_con_historial": _bit(f["n_comp_historial"] > 0),
        "pasajeros": pasajeros,
        "venta_usd": _texto(venta),
        "venta_por_pasajero_usd": _texto(por_pasajero),
        "utilidad_indice": str(redondear_indice(f["utilidad"] / k_utilidad * 100, R.TOPE_INDICE)),
        "canje_millas": _bit(f["canje_millas"]),
        "pagador": f["pagador"],
        "tipo_producto": R.TIPOS_PRODUCTO.get(f["tipo_producto"], SD),
        "tiene_seguro": _bit(f["tiene_seguro"]),
        "lleva_hotel": _bit(f["lleva_hotel"]),
        "regimen_hotel": regimen,
        "aerolinea": aerolinea,
        "servicios": _banda("servicios", f["n_servicios"]),
        "region_destino": SD if pais is None else R.REGION_DE_PAIS.get(pais, R.OTRO),
        "pais_destino": SD if pais is None else pais if pais in R.PAISES else R.OTRO,
        "destinos": _banda("destinos", f["n_destinos"]),
        "noches": _banda("noches", f["noches"]),
        "anticipacion": _banda("anticipacion", f["anticipacion_dias"]),
        "vendedor": codigo_vendedor,
        "vendedor_es_persona": _bit(f["vend_es_persona"]),
        "vendedor_fichas_12m": _banda("vendedor_fichas_12m", f["vend_fichas_12m"]),
        "vendedor_antiguedad": _banda("vendedor_antiguedad", f["vend_antiguedad_dias"]),
        "fu_tiene_mail": _bit(f["fu_tiene_mail"]),
        "fu_tiene_telefono": _bit(f["fu_tiene_telefono"]),
        "fu_tiene_documento": _bit(f["fu_tiene_documento"]),
        "fu_tiene_nacimiento": _bit(f["fu_tiene_nacimiento"]),
        "fu_registros": _banda("fu_registros", f["fu_registros"]),
        "d0_tiene_mail": _bit(f["d0_tiene_mail"]),
        "d0_tiene_telefono": _bit(f["d0_tiene_telefono"]),
        "d0_tiene_documento": _bit(f["d0_tiene_documento"]),
        "d0_tiene_nacimiento": _bit(f["d0_tiene_nacimiento"]),
    }
    assert list(p) == R.COLUMNAS
    p["_anio_viaje"] = SD if f["v1"] is None else str(f["v1"].year)
    return p


def _agrupar_raras(filas):
    """Una categoria con menos clientes que el minimo pasa a `otro`; y si la
    rara es justamente `otro` (o la columna no lo tiene), a `sin_dato`.
    Devuelve cuantas filas cambio."""
    cambios = 0
    for columna, regla in R.CONTRATO:
        if regla.get("identificador") or regla["tipo"] not in ("categoria", "codigo"):
            continue
        if regla["tipo"] == "codigo":
            destinos = [R.VENDEDOR_OTROS]
        else:
            destinos = [d for d in (R.OTRO, R.OTRA, SD) if d in regla["valores"]]
        if not destinos:
            continue
        cuenta = collections.Counter(f[columna] for f in filas)
        reemplazo = {}
        for valor, n in cuenta.items():
            if n >= R.MINIMO_POR_CATEGORIA or valor == SD:
                continue
            posibles = [d for d in destinos if d != valor]
            if posibles:
                reemplazo[valor] = posibles[0] if valor not in destinos else posibles[-1]
        for f in filas:
            if f[columna] in reemplazo:
                f[columna] = reemplazo[f[columna]]
                cambios += 1
    return cambios


def armar_publica(internas, semilla, k_utilidad):
    """Devuelve (filas publicas, informe, correspondencias). Las
    correspondencias NO salen de la empresa."""
    por_vendedor = collections.Counter(f["vend_clave"] for f in internas)
    grandes = [v for v, n in por_vendedor.items() if n >= R.VENDEDOR_MINIMO and v is not None]
    cod_vendedor = asignar_codigos(grandes, "V-", 3, semilla + 1)
    vendedores = {v: cod_vendedor.get(v, R.VENDEDOR_OTROS) for v in por_vendedor}
    clientes = asignar_codigos([f["cid"] for f in internas], "C-", 5, semilla)
    cortes = cortes_60_20_20([f["f1"] for f in internas])

    filas = [fila_publica(f, clientes[f["cid"]], vendedores[f["vend_clave"]], cortes, k_utilidad)
             for f in internas]
    informe = {"filas_entrada": len(filas),
               "cortes_60_20_20": [c.isoformat() for c in cortes],
               "vendedores_con_codigo": len(grandes),
               "categorias_raras_agrupadas": _agrupar_raras(filas)}

    cuasi_1 = R.CUASI_1 + ["_anio_viaje"]
    cuasi_2 = cuasi_1 + R.DETALLE
    retiradas = 0
    pasos_1, pasos_2 = collections.Counter(), collections.Counter()
    for _ in range(4):
        hecho_1, quedan = generalizar(filas, cuasi_1, R.K_1, PASOS_1)
        pasos_1.update(dict(hecho_1))
        if quedan:                     # ni suprimiendo todo llegan a k: no salen
            fuera = set(quedan)
            filas = [f for i, f in enumerate(filas) if i not in fuera]
            retiradas += len(fuera)
        hecho_2, _ = asegurar_detalle(filas, cuasi_1, R.DETALLE, R.K_2, PASOS_2)
        pasos_2.update(dict(hecho_2))
        informe["categorias_raras_agrupadas"] += _agrupar_raras(filas)
        if not (filas_en_grupos_chicos(filas, cuasi_1, R.K_1)
                or filas_en_grupos_chicos(filas, cuasi_2, R.K_2)):
            break

    informe["supresiones_cuasi_1"] = dict(pasos_1)
    informe["supresiones_cuasi_2"] = dict(pasos_2)
    informe["filas_retiradas"] = retiradas
    informe["filas_salida"] = len(filas)
    informe["grupos_chicos_al_final"] = {
        "cuasi_1": len(filas_en_grupos_chicos(filas, cuasi_1, R.K_1)),
        "cuasi_2": len(filas_en_grupos_chicos(filas, cuasi_2, R.K_2))}

    filas.sort(key=lambda f: f["cliente"])
    for f in filas:
        del f["_anio_viaje"]
    publicados = {f["cliente"] for f in filas}
    mapas = {"clientes": {o: c for o, c in clientes.items() if c in publicados},
             "vendedores": vendedores}
    return filas, informe, mapas


# ----------------------------------------------------------------- verificacion
def _muestra(valores):
    return ", ".join(repr(str(v)[:12]) for v in sorted(valores)[:3])


def revisar_columnas(columnas, contrato):
    esperadas = [c for c, _ in contrato]
    problemas = ["columna que no esta en el contrato: %s" % c for c in columnas if c not in esperadas]
    problemas += ["falta la columna: %s" % c for c in esperadas if c not in columnas]
    if not problemas and list(columnas) != esperadas:
        problemas.append("las columnas no estan en el orden del contrato")
    return problemas


def _valor_valido(valor, regla):
    tipo = regla["tipo"]
    if tipo == "categoria":
        return valor in regla["valores"]
    if tipo == "codigo":
        return re.fullmatch(regla["patron"], valor) is not None
    if tipo == "monto":
        if valor == "":
            return bool(regla.get("vacio"))
        return (re.fullmatch(r"\d+", valor) is not None
                and redondear_monto(int(valor), regla["tope"]) == int(valor))
    if tipo == "indice":
        return (re.fullmatch(r"-?\d+", valor) is not None
                and regla["topes"][0] <= int(valor) <= regla["topes"][1]
                and redondear_indice(int(valor), regla["topes"]) == int(valor))
    return False


def revisar_dominios(filas, contrato):
    problemas = []
    for columna, regla in contrato:
        malos = collections.Counter(f[columna] for f in filas if not _valor_valido(f[columna], regla))
        if malos:
            problemas.append("%s: %d valores fuera del contrato (%s)"
                             % (columna, sum(malos.values()), _muestra(malos)))
    return problemas


def revisar_patrones(filas):
    """Red de seguridad: nada con forma de mail, telefono, documento o nombre."""
    malos = collections.Counter()
    for f in filas:
        for columna, valor in f.items():
            valor = str(valor)
            if "@" in valor or " " in valor or len(valor) > 24 or re.search(r"\d{7,}", valor):
                malos[columna] += 1
    return ["%s: %d valores con forma de dato personal" % (c, n) for c, n in sorted(malos.items())]


def revisar_codigos(filas, columna):
    repetidos = [c for c, n in collections.Counter(f[columna] for f in filas).items() if n > 1]
    return ["%s: %d codigos repetidos" % (columna, len(repetidos))] if repetidos else []


def revisar_k(filas, cuasi, k, nombre):
    chicas = filas_en_grupos_chicos(filas, cuasi, k)
    if not chicas:
        return []
    return ["%s: %d clientes en grupos de menos de %d" % (nombre, len(chicas), k)]


def revisar_categorias(filas, contrato, minimo):
    problemas = []
    for columna, regla in contrato:
        if regla.get("identificador") or regla["tipo"] not in ("categoria", "codigo"):
            continue
        for valor, n in sorted(collections.Counter(f[columna] for f in filas).items()):
            if n < minimo and valor != SD:
                problemas.append("%s: la categoria %s tiene %d clientes (minimo %d)"
                                 % (columna, valor, n, minimo))
    return problemas


def revisar_orden(filas, columna):
    """El orden del archivo no puede decir nada: ni de la cohorte ni del id."""
    n = len(filas)
    xs = [float(f[columna]) for f in filas]
    mx, mi = sum(xs) / n, (n - 1) / 2.0
    sxx = sum((x - mx) ** 2 for x in xs)
    sii = sum((i - mi) ** 2 for i in range(n))
    if sxx == 0 or sii == 0:
        return []
    r = sum((i - mi) * (x - mx) for i, x in enumerate(xs)) / (sxx * sii) ** 0.5
    return ["el orden de las filas sigue a %s (r = %.2f)" % (columna, r)] if abs(r) > 0.1 else []


def revisar_por_pasajero(filas):
    """Dividir venta / gasto por pasajero no puede delatar el tamanio del grupo."""
    malas = 0
    for f in filas:
        pasajeros, venta, pp = f["pasajeros"], f["venta_usd"], f["venta_por_pasajero_usd"]
        if pasajeros in R.PASAJEROS_SIN_POR_PASAJERO or venta == "":
            malas += pp != ""
        elif pasajeros in R.PASAJEROS_REPRESENTATIVO:
            esperado = redondear_monto(int(venta) / R.PASAJEROS_REPRESENTATIVO[pasajeros],
                                       R.TOPE_VENTA_POR_PASAJERO)
            malas += pp != str(esperado)
    return ["venta_por_pasajero_usd: %d filas delatan el tamanio del grupo" % malas] if malas else []


def revisar_supresion(filas):
    """Si se suprimio el tipo de producto, tambien la aerolinea y el regimen."""
    malas = sum(1 for f in filas if f["tipo_producto"] == SD
                and (f["aerolinea"] != SD or f["regimen_hotel"] != SD))
    return ["tipo_producto suprimido pero aerolinea o regimen visibles en %d filas" % malas] if malas else []


def revisar_todo(filas, reglas):
    """Todas las verificaciones sobre la tabla publica. Lista vacia = pasa."""
    if not filas:
        return ["la tabla esta vacia"]
    columnas = list(filas[0])
    problemas = revisar_columnas(columnas, reglas.CONTRATO)
    problemas += revisar_patrones(filas)
    if any(list(f) != columnas for f in filas):
        problemas.append("hay filas con columnas distintas")
    if problemas:
        return problemas
    problemas += revisar_dominios(filas, reglas.CONTRATO)
    problemas += revisar_codigos(filas, "cliente")
    if problemas:
        return problemas
    problemas += revisar_k(filas, reglas.CUASI_1, reglas.K_1, "lo que sabe un conocido del viaje")
    problemas += revisar_k(filas, reglas.CUASI_2, reglas.K_2, "con aerolinea, regimen y destinos")
    problemas += revisar_categorias(filas, reglas.CONTRATO, reglas.MINIMO_POR_CATEGORIA)
    problemas += revisar_orden(filas, "cohorte")
    problemas += revisar_por_pasajero(filas)
    problemas += revisar_supresion(filas)
    return problemas
