from typing import Any, Dict, List, Optional
from modulos.dataset_store import DatasetStore


class AdquisicionConocimiento:
    """
    Simula adquisición de conocimiento mediante entrevistas guiadas por escenarios.
    En el dataset, cada escenario trae 'regla_extraida': {'id': 'SSB_Rx'}.
    Nosotros marcamos esa regla como capturada.
    """

    def __init__(self, store: DatasetStore):
        self.store = store

    def ejecutar(self) -> None:
        escenarios = self.store.escenarios
        if not escenarios:
            print("No hay escenarios de adquisición en el dataset.")
            return

        print("\n" + "=" * 70)
        print(" ADQUISICIÓN DE CONOCIMIENTO (ENTREVISTAS POR ESCENARIOS)")
        print("=" * 70)
        print(f"Experto simulado: {self.store.data.get('expert_simulation', {}).get('expert_name', 'Experto')}")
        print(f"Escenarios disponibles: {len(escenarios)}")
        print()

        # Modo simple: recorrer todos los escenarios y capturar reglas
        capturadas_antes = set(self.store.reglas_capturadas_ids)

        for i, scn in enumerate(escenarios, 1):
            scn_id = scn.get("id", f"SCN_{i:02d}")
            contexto = scn.get("contexto", "")
            respuesta_base = scn.get("respuesta_base", "")
            regla_id = (scn.get("regla_extraida") or {}).get("id")

            print(f"\n--- ESCENARIO {i}: {scn_id} ---")
            print(f"Contexto: {contexto}")
            print(f"Respuesta del experto: {respuesta_base}")

            if regla_id:
                self.store.marcar_regla_capturada(regla_id)
                print(f"✅ Regla capturada: {regla_id}")
            else:
                print("⚠️ Este escenario no tiene regla_extraida.")

        self.store.save()

        capturadas_despues = set(self.store.reglas_capturadas_ids)
        nuevas = capturadas_despues - capturadas_antes

        print("\n" + "=" * 70)
        print(" RESULTADO DE ADQUISICIÓN")
        print("=" * 70)
        print(f"Reglas capturadas totales: {len(capturadas_despues)}")
        if nuevas:
            print(f"Nuevas en esta sesión: {', '.join(sorted(nuevas))}")
        else:
            print("No se capturaron reglas nuevas (ya estaban marcadas).")