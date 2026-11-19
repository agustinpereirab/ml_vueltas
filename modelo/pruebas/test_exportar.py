"""Pruebas de la exportacion portable del modelo. Datos inventados."""
import csv
import json
import math
import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from modelo import calibracion as cal
from modelo import exportar, modelos, puntuar


def sinteticos(n=2000, semilla=0):
    r = np.random.default_rng(semilla)
    x = pd.DataFrame({
        "pais_destino": r.choice(["AR", "BR", "ES", "otro", "sin_dato"], n).astype(object),
        "fue_acompaniante_antes": r.choice(["0", "1"], n, p=[0.8, 0.2]).astype(object),
        "venta_usd": np.where(r.random(n) < 0.15, np.nan, r.gamma(2, 800, n)),
        "utilidad_indice": r.integers(-100, 600, n).astype(float),
    })
    logit = -1.3 + 0.9 * (x["fue_acompaniante_antes"] == "1") + 0.0002 * np.nan_to_num(x["venta_usd"])
    y = (r.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return x, y


CATS, NUMS = ["pais_destino", "fue_acompaniante_antes"], ["venta_usd", "utilidad_indice"]


def como_texto(x):
    """La fila tal como viene en el CSV: todo texto, faltante = cadena vacia."""
    return [{c: ("" if isinstance(v, float) and math.isnan(v) else
                 (repr(v) if isinstance(v, float) else str(v))) for c, v in fila.items()}
            for fila in x.to_dict("records")]


class Exportacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x, cls.y = sinteticos()
        cls.pipe = modelos._logistica(CATS, NUMS, 0.5).fit(cls.x, cls.y)
        cls.calibrador = cal.Intercepto().fit(cls.pipe.predict_proba(cls.x)[:, 1], cls.y)
        cls.modelo = exportar.exportar(cls.pipe, CATS, NUMS, cls.calibrador.parametros(), {"nombre": "prueba"})

    def test_el_modelo_exportado_es_json_puro(self):
        copia = json.loads(json.dumps(self.modelo))
        self.assertEqual(copia, self.modelo)

    def test_sin_recalibrar_reproduce_la_probabilidad_del_pipeline(self):
        filas = como_texto(self.x.head(300))
        esperado = self.pipe.predict_proba(self.x.head(300))[:, 1]
        obtenido = [puntuar.probabilidad(f, self.modelo, recalibrar=False) for f in filas]
        np.testing.assert_allclose(obtenido, esperado, atol=1e-12)

    def test_recalibrado_reproduce_al_calibrador(self):
        filas = como_texto(self.x.head(300))
        esperado = self.calibrador.predict(self.pipe.predict_proba(self.x.head(300))[:, 1])
        obtenido = [puntuar.probabilidad(f, self.modelo) for f in filas]
        np.testing.assert_allclose(obtenido, esperado, atol=1e-12)

    def test_una_categoria_que_el_modelo_no_conoce_no_aporta(self):
        f = como_texto(self.x.head(1))[0]
        conocida = dict(f, pais_destino="ZZ")
        nueva = pd.DataFrame([{**self.x.iloc[0].to_dict(), "pais_destino": "ZZ"}])
        np.testing.assert_allclose(puntuar.probabilidad(conocida, self.modelo, recalibrar=False),
                                   self.pipe.predict_proba(nueva)[:, 1], atol=1e-12)

    def test_falta_una_columna_del_modelo_falla_con_mensaje(self):
        f = como_texto(self.x.head(1))[0]
        del f["venta_usd"]
        with self.assertRaises(KeyError):
            puntuar.probabilidad(f, self.modelo)

    def test_puntuar_un_csv_agrega_la_columna_de_probabilidad(self):
        with tempfile.TemporaryDirectory() as tmp:
            entrada, salida, ruta_modelo = (os.path.join(tmp, n) for n in ("in.csv", "out.csv", "m.json"))
            filas = como_texto(self.x.head(20))
            with open(entrada, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(filas[0]))
                w.writeheader()
                w.writerows(filas)
            with open(ruta_modelo, "w", encoding="utf-8") as fh:
                json.dump(self.modelo, fh)
            puntuar.puntuar_csv(ruta_modelo, entrada, salida)
            with open(salida, newline="", encoding="utf-8") as fh:
                leidas = list(csv.DictReader(fh))
            self.assertEqual(len(leidas), 20)
            esperado = self.calibrador.predict(self.pipe.predict_proba(self.x.head(20))[:, 1])
            np.testing.assert_allclose([float(r["prob_vuelve_12"]) for r in leidas], esperado, atol=1e-9)


if __name__ == "__main__":
    unittest.main()
