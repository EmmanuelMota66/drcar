from typing import Any, Dict, List, Tuple
from modulos.dataset_store import DatasetStore
from modulos.ontologia import OntologiaDominio
from modulos.motor_inferencia import MotorInferencia


class ReporteCobertura:
    """
    Reporte de:
    - Cobertura de reglas críticas capturadas
    - Precisión en casos de prueba
    - Inconsistencias ontología
    """

    def __init__(self, store: DatasetStore):
        self.store = store
        self.onto = OntologiaDominio(store)
        self.motor = MotorInferencia(store)

    def ejecutar(self) -> None:
        reglas_criticas_ids = set(self.store.reglas_criticas_ids)
        capturadas = set(self.store.reglas_capturadas_ids)
        capturadas_criticas = capturadas.intersection(reglas_criticas_ids)

        cobertura_pct = 0.0
        if reglas_criticas_ids:
            cobertura_pct = (len(capturadas_criticas) / len(reglas_criticas_ids)) * 100.0

        # Ontología
        inconsistencias = self.onto.validar_coherencia()
        inc_count = len(inconsistencias)

        # Casos de prueba (precisión)
        casos = self.store.casos_prueba
        aciertos = 0
        resultados: List[Dict[str, Any]] = []

        for caso in casos:
            sintomas = caso.get("sintomas", [])
            esperado = caso.get("diagnostico_esperado")
            out = self.motor.inferir(sintomas)
            obtenido = out.get("diagnostico")
            ok = (obtenido == esperado)
            if ok:
                aciertos += 1
            resultados.append({
                "id": caso.get("id"),
                "esperado": esperado,
                "obtenido": obtenido,
                "ok": ok,
                "criticidad": caso.get("criticidad"),
            })

        precision_pct = (aciertos / len(casos) * 100.0) if casos else 0.0

        # Objetivos rúbrica (del dataset)
        objetivos = (self.store.reporte_config.get("objetivos_rubrica") or {})
        min_cov = objetivos.get("min_cobertura_reglas_criticas_pct", 70)
        min_prec = objetivos.get("min_precision_casos_prueba_pct", 80)
        max_inc = objetivos.get("inconsistencias_ontologia_permitidas", 0)

        print("\n" + "=" * 70)
        print(" REPORTE DE COBERTURA / CALIDAD")
        print("=" * 70)
        print(f"Dominio: {self.store.dominio}")

        print("\n--- Cobertura de reglas críticas ---")
        print(f"Reglas críticas capturadas: {len(capturadas_criticas)}/{len(reglas_criticas_ids)}")
        print(f"Cobertura: {cobertura_pct:.1f}% (mínimo requerido: {min_cov}%)")

        print("\n--- Ontología ---")
        print(f"Inconsistencias: {inc_count} (permitidas: {max_inc})")
        if inconsistencias:
            for inc in inconsistencias:
                print(f" - {inc}")

        print("\n--- Casos de prueba ---")
        print(f"Aciertos: {aciertos}/{len(casos)}")
        print(f"Precisión: {precision_pct:.1f}% (mínimo requerido: {min_prec}%)")

        print("\nDetalle por caso:")
        for r in resultados:
            simbolo = "✓" if r["ok"] else "✗"
            print(f"{simbolo} {r['id']}: esperado={r['esperado']} obtenido={r['obtenido']} criticidad={r['criticidad']}")

        print("\n" + "=" * 70)
        print(" ESTADO CONTRA RÚBRICA")
        print("=" * 70)
        print(f"Cobertura OK: {'SI' if cobertura_pct >= min_cov else 'NO'}")
        print(f"Precisión OK: {'SI' if precision_pct >= min_prec else 'NO'}")
        print(f"Ontología OK: {'SI' if inc_count <= max_inc else 'NO'}")