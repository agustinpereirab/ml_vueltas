"""Pruebas de la interpretacion de la logistica. Datos inventados."""
import unittest

import numpy as np
import pandas as pd

from modelo import datos, interpretacion as it, modelos


def sinteticos(n=3000, semilla=0):
    r = np.random.default_rng(semilla)
    x = pd.DataFrame({
        "pais_destino": r.choice(["AR", "BR", "ES", "US", "otro", "sin_dato"], n).astype(object),
        "fue_acompaniante_antes": r.choice(["0", "1"], n, p=[0.8, 0.2]).astype(object),
        "venta_usd": np.where(r.random(n) < 0.1, np.nan, r.gamma(2, 800, n)),
    })
    logit = -1.3 + 0.9 * (x["fue_acompaniante_antes"] == "1") + 0.3 * (x["pais_destino"] == "AR")
    y = (r.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return x, y


def ajustar(x, y, C=1.0):
    cats, nums = ["pais_destino", "fue_acompaniante_antes"], ["venta_usd"]
    return modelos._logistica(cats, nums, C).fit(x, y), cats, nums


class Grupos(unittest.TestCase):
    def test_los_grupos_reparten_exactamente_las_variables_del_brazo_dia_0(self):
        todas = [v for vs in it.GRUPOS.values() for v in vs]
        self.assertEqual(len(todas), len(set(todas)))
        self.assertEqual(set(todas), set(datos.BRAZOS["dia0"]))

    def test_los_tres_grupos_de_h2_estan(self):
        for g in ("H2 · compañía previa", "H2 · destino", "H2 · vendedor"):
            self.assertIn(g, it.GRUPOS)


class Shap(unittest.TestCase):
    def setUp(self):
        self.x, self.y = sinteticos()
        self.modelo, self.cats, self.nums = ajustar(self.x, self.y)

    def test_cada_columna_transformada_tiene_su_variable(self):
        variables = it.columnas_por_variable(self.modelo)
        n = it.transformar(self.modelo, self.x.head(3)).shape[1]
        self.assertEqual(len(variables), n)
        self.assertEqual(set(variables), {"pais_destino", "fue_acompaniante_antes", "venta_usd"})

    def test_base_mas_contribuciones_da_el_logit_del_modelo(self):
        base, s = it.shap_lineal(self.modelo, self.x, self.x.head(200))
        logit = self.modelo.decision_function(self.x.head(200))
        np.testing.assert_allclose(base + s.sum(axis=1).to_numpy(), logit, atol=1e-9)
        self.assertEqual(list(s.columns), ["pais_destino", "fue_acompaniante_antes", "venta_usd"])

    def test_coincide_con_la_libreria_shap(self):
        import shap
        fondo = it.transformar(self.modelo, self.x)
        lr = self.modelo.named_steps["modelo"]
        explicador = shap.LinearExplainer((lr.coef_[0], lr.intercept_[0]),
                                          shap.maskers.Independent(fondo, max_samples=len(fondo)))
        valores = explicador.shap_values(it.transformar(self.modelo, self.x.head(50)))
        variables = np.array(it.columnas_por_variable(self.modelo))
        _, s = it.shap_lineal(self.modelo, self.x, self.x.head(50))
        for v in s.columns:
            np.testing.assert_allclose(valores[:, variables == v].sum(axis=1), s[v].to_numpy(), atol=1e-9)

    def test_la_contribucion_media_sobre_el_fondo_es_cero(self):
        _, s = it.shap_lineal(self.modelo, self.x, self.x)
        np.testing.assert_allclose(s.mean().to_numpy(), 0, atol=1e-9)

    def test_por_grupo_suma_las_variables_del_grupo(self):
        _, s = it.shap_lineal(self.modelo, self.x, self.x.head(20))
        g = it.por_grupo(s, {"a": ["pais_destino", "venta_usd"], "b": ["fue_acompaniante_antes"]})
        np.testing.assert_allclose(g["a"], s["pais_destino"] + s["venta_usd"])
        np.testing.assert_allclose(g["b"], s["fue_acompaniante_antes"])


class OddsRatios(unittest.TestCase):
    def test_recupera_el_efecto_de_una_binaria(self):
        x, y = sinteticos(40000, semilla=3)
        modelo, _, _ = ajustar(x, y, C=100.0)
        orr = it.odds_ratios(modelo, "fue_acompaniante_antes", "0")
        self.assertAlmostEqual(orr["0"], 1.0)
        self.assertAlmostEqual(np.log(orr["1"]), 0.9, delta=0.1)

    def test_referencia_inexistente_falla(self):
        x, y = sinteticos()
        modelo, _, _ = ajustar(x, y)
        with self.assertRaises(KeyError):
            it.odds_ratios(modelo, "fue_acompaniante_antes", "9")


class Regional(unittest.TestCase):
    def test_reemplaza_pais_y_region_por_una_marca_regional(self):
        x = pd.DataFrame({"pais_destino": ["AR", "BR", "CL", "PY", "ES", "otro", "sin_dato"],
                          "region_destino": ["sudamerica", "brasil", "sudamerica", "sudamerica",
                                             "europa", "caribe", "sin_dato"],
                          "noches": ["4-7"] * 7})
        r = it.con_regional(x)
        self.assertEqual(list(r.columns), ["noches", "destino_regional"])
        self.assertEqual(list(r["destino_regional"]), ["1", "1", "1", "1", "0", "0", "0"])


if __name__ == "__main__":
    unittest.main()
