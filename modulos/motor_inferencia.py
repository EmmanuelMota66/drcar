from typing import Any, Dict, List, Optional, Tuple
from modulos.dataset_store import DatasetStore


class MotorInferencia:
    """
    Motor de inferencia basado en reglas (matching por condiciones).
    - Si una regla cumple TODAS sus condiciones -> candidato principal.
    - Si no hay match completo -> devuelve diagnostico_no_posible.
    Incluye explicación por perfil: cliente / aprendiz / experto.
    """

    def __init__(self, store: DatasetStore):
        self.store = store

    def _reglas_activas(self) -> List[Dict[str, Any]]:
        # Reglas críticas siempre están disponibles
        reglas = self.store.reglas_criticas

        # Si en adquisición se “capturó” alguna regla, igual ya está en reglas_criticas,
        # pero esto sirve para reportar/filtrar si quisieras.
        # Aquí no filtramos: el motor puede usar reglas aunque no se “capten”.
        return reglas

    def inferir(self, sintomas: List[str]) -> Dict[str, Any]:
        reglas = self._reglas_activas()
        mejor: Optional[Dict[str, Any]] = None
        mejor_score = -1.0
        mejor_certeza = -1.0
        traza: List[Dict[str, Any]] = []

        sset = set(sintomas)

        for r in reglas:
            condiciones = r.get("condiciones", [])
            if not condiciones:
                continue

            cset = set(condiciones)
            cumple = cset.issubset(sset)
            score = len(cset.intersection(sset)) / max(1, len(cset))
            certeza = float(r.get("certeza", 0.0))

            traza.append({
                "regla_id": r.get("id"),
                "cumple": cumple,
                "score": round(score, 3),
                "certeza": certeza,
                "conclusion": r.get("conclusion"),
            })

            # Preferimos match completo; si hay empate, mayor certeza
            if cumple:
                if score > mejor_score or (score == mejor_score and certeza > mejor_certeza):
                    mejor = r
                    mejor_score = score
                    mejor_certeza = certeza

        if mejor is None:
            return {
                "diagnostico": "diagnostico_no_posible",
                "regla": None,
                "certeza": 0.0,
                "traza": traza,
            }

        return {
            "diagnostico": mejor.get("conclusion"),
            "regla": mejor.get("id"),
            "certeza": float(mejor.get("certeza", 0.0)),
            "requiere_reparacion": mejor.get("requiere_reparacion", []),
            "explicacion_cliente": mejor.get("explicacion_cliente", ""),
            "explicacion_tecnica": mejor.get("explicacion_tecnica", ""),
            "traza": traza,
        }

    def explicar(self, resultado: Dict[str, Any], perfil: str) -> str:
        diagnostico = resultado.get("diagnostico", "diagnostico_no_posible")
        regla = resultado.get("regla")
        certeza = resultado.get("certeza", 0.0)
        reparaciones = resultado.get("requiere_reparacion", [])

        if diagnostico == "diagnostico_no_posible":
            return (
                "No se pudo obtener un diagnóstico con las reglas actuales.\n"
                "Sugerencia: hacer más adquisición de conocimiento (nuevas reglas) o revisar síntomas."
            )

        if perfil == "cliente":
            base = resultado.get("explicacion_cliente", "")
            rec = ""
            if reparaciones:
                rec = "Recomendación: " + ", ".join(reparaciones)
            return f"Diagnóstico: {diagnostico}\n{base}\n{rec}"

        if perfil == "aprendiz":
            base = resultado.get("explicacion_tecnica", "")
            return (
                f"Diagnóstico: {diagnostico}\n"
                f"Regla aplicada: {regla} (certeza={certeza})\n"
                f"Justificación técnica: {base}\n"
                f"Acciones sugeridas: {', '.join(reparaciones) if reparaciones else 'N/A'}"
            )

        # experto
        traza = resultado.get("traza", [])
        lines = [
            f"Diagnóstico: {diagnostico}",
            f"Regla ganadora: {regla} (certeza={certeza})",
            "TRAZA (reglas evaluadas):"
        ]
        for t in traza:
            lines.append(
                f"- {t['regla_id']}: cumple={t['cumple']} score={t['score']} certeza={t['certeza']} -> {t['conclusion']}"
            )
        if reparaciones:
            lines.append("Requiere reparación: " + ", ".join(reparaciones))
        return "\n".join(lines)