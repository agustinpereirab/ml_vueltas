"""Paso 3 · Verifica la tabla antes de entregarla.

    py exportacion/03_verificar.py [ruta_al_csv]

Mira SOLO el archivo, sin la foto ni las correspondencias: lo puede correr
cualquiera que reciba la tabla. Sale con 0 si pasa y con 1 si no.

Que controla
------------
1. Que las columnas sean exactamente las del contrato (`reglas.py`).
2. Que cada valor este en la lista cerrada de su columna: no hay texto libre.
3. Que nada tenga forma de mail, telefono, documento o nombre.
4. Que los codigos de cliente no se repitan.
5. Que cada combinacion de lo que alguien de afuera puede saber de un viaje
   (cohorte, destino, pasajeros, noches, tipo de producto, hotel) aparezca en
   al menos 5 clientes; y en al menos 3 sumando aerolinea, regimen y destinos.
6. Que ninguna categoria tenga menos de 20 clientes.
7. Que el orden de las filas no diga nada.
8. Que el gasto por pasajero no delate el tamanio exacto del grupo.
"""
import collections
import csv
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from exportacion import anonimato, reglas  # noqa: E402


def grupos(filas, cuasi):
    cuenta = collections.Counter(tuple(f[c] for c in cuasi) for f in filas)
    return len(cuenta), min(cuenta.values())


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "datos", "tabla_modelo.csv")
    with open(ruta, newline="", encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    print("%s · %d filas · %d columnas" % (os.path.basename(ruta), len(filas), len(filas[0]) if filas else 0))

    problemas = anonimato.revisar_todo(filas, reglas)

    manifiesto = os.path.join(os.path.dirname(ruta), "manifiesto.json")
    if os.path.exists(manifiesto):
        with open(manifiesto, encoding="utf-8") as fh:
            esperado = json.load(fh).get("sha256")
        with open(ruta, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != esperado:
                problemas.append("el archivo no coincide con la huella del manifiesto")

    if problemas:
        print("NO PASA:")
        for p in problemas:
            print("  - " + p)
        return 1

    n1, min1 = grupos(filas, reglas.CUASI_1)
    n2, min2 = grupos(filas, reglas.CUASI_2)
    completas = collections.Counter(tuple(f[c] for c in reglas.COLUMNAS[1:]) for f in filas)
    unicas = sum(1 for n in completas.values() if n == 1)
    print("PASA")
    print("  lo que sabe un conocido del viaje: %d grupos, el mas chico de %d clientes" % (n1, min1))
    print("  con aerolinea, regimen y destinos: %d grupos, el mas chico de %d clientes" % (n2, min2))
    print("  limite conocido: %.1f%% de las filas es unica mirando TODAS las columnas; quien "
          "tenga la base de la empresa puede volver a cruzarlas" % (100.0 * unicas / len(filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
