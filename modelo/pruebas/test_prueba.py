"""Pruebas de los controles de `prueba.py`. No tocan el bloque de prueba."""
import os
import tempfile
import unittest

from modelo import prueba


class Controles(unittest.TestCase):
    def test_plan_versionado_y_sin_cambios_pasa(self):
        self.assertEqual(prueba.verificar_versionado("plan.md", "", "abc123 2026-11-19T10:00:00"),
                         "abc123 2026-11-19T10:00:00")

    def test_plan_con_cambios_sin_versionar_no_corre(self):
        with self.assertRaises(SystemExit):
            prueba.verificar_versionado("plan.md", " M plan.md", "abc123 2026-11-19T10:00:00")

    def test_plan_nunca_versionado_no_corre(self):
        with self.assertRaises(SystemExit):
            prueba.verificar_versionado("plan.md", "?? plan.md", "")

    def test_si_la_prueba_ya_se_corrio_no_vuelve_a_correr(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "prueba.json")
            prueba.verificar_no_corrida(ruta)
            open(ruta, "w").close()
            with self.assertRaises(SystemExit):
                prueba.verificar_no_corrida(ruta)


def dif(desde, hasta):
    return {"punto": (desde + hasta) / 2, "desde": desde, "hasta": hasta}


class VeredictoH1(unittest.TestCase):
    def base(self, **cambios):
        d = {"principal - prevalencia": {"pr_auc": dif(0.1, 0.2), "roc_auc": dif(0.1, 0.2)},
             "principal - regla_acompaniante": {"pr_auc": dif(0.05, 0.1), "roc_auc": dif(0.04, 0.09)}}
        for clave, valor in cambios.items():
            par, metrica = clave.split("__")
            d[par.replace("_menos_", " - ")][metrica] = valor
        return d

    def test_se_confirma_si_las_cuatro_diferencias_son_positivas_con_intervalo(self):
        self.assertTrue(prueba.veredicto_h1(self.base())["confirmada"])

    def test_no_se_confirma_si_una_incluye_el_cero(self):
        v = prueba.veredicto_h1(self.base(principal_menos_regla_acompaniante__roc_auc=dif(-0.01, 0.05)))
        self.assertFalse(v["confirmada"])
        self.assertEqual([c["par"] for c in v["comparaciones"] if not c["gana"]],
                         ["principal - regla_acompaniante"])


if __name__ == "__main__":
    unittest.main()
