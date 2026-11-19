"""Carga de los datos de contacto por anio: un descriptivo POSTERIOR A LA PRUEBA.

    python modelo/carga_contacto.py

Mide, para cada bloque (2023, 2024 y enero a agosto de 2025), que parte de los
clientes nuevos tenia cada dato de contacto cargado en el registro de su
primera compra, y cuanto vuelven unos y otros. Se corrio despues de la prueba
(2026-11-19), para explicar la sobreestimacion del modelo: no entrena, no
ajusta ni elige nada. Usa la etiqueta del bloque de prueba solo para describir.

Escribe `modelo/resultados/carga_contacto.md` y `.json`.
"""
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from modelo import datos  # noqa: E402
from modelo.escalera import huella_tabla, pct  # noqa: E402

SALIDA = os.path.join(REPO, "modelo", "resultados")
BLOQUES = [("entrenamiento", "2023"), ("validacion", "2024"), ("prueba", "enero a agosto de 2025")]
DATOS = [("d0_tiene_mail", "mail"), ("d0_tiene_telefono", "teléfono"), ("d0_tiene_nacimiento", "fecha de nacimiento")]


def main():
    huella = huella_tabla()
    d = datos.cargar(bloques=tuple(b for b, _ in BLOQUES), permitir_prueba=True)
    r = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "tabla_sha256": huella,
         "posterior_a_la_prueba": True, "bloques": {}}
    for bloque, _ in BLOQUES:
        x = d[d["bloque"] == bloque]
        fila = {"clientes": int(len(x)), "vuelven": float(x[datos.ETIQUETA].mean())}
        for col, _ in DATOS:
            con, sin = x[x[col] == "1"], x[x[col] == "0"]
            fila[col] = {"tienen": float(len(con) / len(x)), "vuelven_con": float(con[datos.ETIQUETA].mean()),
                         "vuelven_sin": float(sin[datos.ETIQUETA].mean()) if len(sin) else None}
        ninguno = x[(x["d0_tiene_mail"] == "0") & (x["d0_tiene_telefono"] == "0")]
        fila["sin_mail_ni_telefono"] = {"tienen": float(len(ninguno) / len(x)),
                                        "vuelven": float(ninguno[datos.ETIQUETA].mean())}
        r["bloques"][bloque] = fila

    with open(os.path.join(SALIDA, "carga_contacto.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=2, ensure_ascii=False)
    l = ["# Carga de los datos de contacto por año · *posterior a la prueba*\n",
         "Generado por `modelo/carga_contacto.py` el %s. Tabla `%s…`. Es un descriptivo hecho **después** de "
         "correr la prueba, para explicar la sobreestimación del modelo. No entrena, no ajusta ni elige nada. "
         "«Cargado» quiere decir que el dato estaba en el registro de cliente usado en la primera compra "
         "(columnas `d0_*`).\n" % (r["generado"][:10], huella[:12]),
         "| | " + " | ".join(n for _, n in BLOQUES) + " |", "|---|" + "---|" * len(BLOQUES)]
    l.append("| Clientes | " + " | ".join("{:,}".format(r["bloques"][b]["clientes"]).replace(",", ".") for b, _ in BLOQUES) + " |")
    l.append("| Vuelven | " + " | ".join(pct(r["bloques"][b]["vuelven"]) for b, _ in BLOQUES) + " |")
    for col, nombre in DATOS:
        l.append("| Tienen %s cargado | %s |" % (nombre, " | ".join(pct(r["bloques"][b][col]["tienen"]) for b, _ in BLOQUES)))
        l.append("| Vuelven, con %s | %s |" % (nombre, " | ".join(pct(r["bloques"][b][col]["vuelven_con"]) for b, _ in BLOQUES)))
        l.append("| Vuelven, sin %s | %s |" % (nombre, " | ".join(
            "—" if r["bloques"][b][col]["vuelven_sin"] is None else pct(r["bloques"][b][col]["vuelven_sin"]) for b, _ in BLOQUES)))
    l.append("| No tienen ni mail ni teléfono | %s |" % " | ".join(pct(r["bloques"][b]["sin_mail_ni_telefono"]["tienen"]) for b, _ in BLOQUES))
    l.append("| Vuelven, sin mail ni teléfono | %s |" % " | ".join(pct(r["bloques"][b]["sin_mail_ni_telefono"]["vuelven"]) for b, _ in BLOQUES))
    l.append("")
    with open(os.path.join(SALIDA, "carga_contacto.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(l))
    print("\n".join(l))


if __name__ == "__main__":
    main()
