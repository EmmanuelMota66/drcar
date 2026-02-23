from typing import Any, Dict, List, Optional, Tuple
from modulos.dataset_store import DatasetStore


class MotorInferencia:
    """
    MÓDULO 3 — Motor de inferencia (reglas) + explicación por perfil.

    Estrategia:
    - Se evalúan todas las reglas críticas.
    - Una regla "cumple" si TODAS sus condiciones están dentro de los síntomas ingresados.
    - Si hay varias reglas que cumplen, se desempata por:
        1) Mayor certeza
        2) Mayor especificidad (más condiciones)
        3) Mayor score (por si se habilita parcial en el futuro)
    - Si no hay match completo: diagnostico_no_posible.

    Explicación por perfiles:
    - cliente: sencillo, corto, con "nivel de confianza" y recomendación.
    - aprendiz: muestra regla aplicada y condiciones (cumplidas/faltantes).
    - experto: traza completa y motivos de descarte.
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, store: DatasetStore):
        self.store = store

    def _reglas_activas(self) -> List[Dict[str, Any]]:
        # En este proyecto, las "reglas críticas" son las reglas disponibles para inferencia.
        return self.store.reglas_criticas

    # -------------------------
    # Inferencia
    # -------------------------
    def inferir(self, sintomas: List[str]) -> Dict[str, Any]:
        reglas = self._reglas_activas()

        sset = set(s.strip() for s in sintomas if s and s.strip())
        traza: List[Dict[str, Any]] = []

        mejor: Optional[Dict[str, Any]] = None
        mejor_key = None  # tupla para comparar

        for r in reglas:
            condiciones = r.get("condiciones", []) or []
            if not isinstance(condiciones, list) or not condiciones:
                continue

            cset = set(str(c).strip() for c in condiciones if str(c).strip())
            matched = sorted(list(cset.intersection(sset)))
            missing = sorted(list(cset.difference(sset)))

            cumple = (len(missing) == 0)
            score = len(matched) / max(1, len(cset))
            certeza = float(r.get("certeza", 0.0))

            entry = {
                "regla_id": r.get("id"),
                "nombre": r.get("nombre", ""),
                "cumple": cumple,
                "score": round(score, 3),
                "certeza": certeza,
                "matched": matched,
                "missing": missing,
                "conclusion": r.get("conclusion"),
                "tipo_falla": r.get("tipo_falla", ""),
                "requiere_reparacion": r.get("requiere_reparacion", []),
            }
            traza.append(entry)

            # Clave para desempate:
            # (cumple? 1:0, certeza, especificidad, score)
            # Nota: score para match completo es 1.0, pero lo dejamos por robustez.
            key = (
                1 if cumple else 0,
                certeza,
                len(cset),      # más condiciones = más específica
                score
            )

            if mejor is None or key > mejor_key:
                mejor = r
                mejor_key = key

        if mejor is None:
            return {
                "diagnostico": "diagnostico_no_posible",
                "regla": None,
                "certeza": 0.0,
                "tipo_falla": "",
                "requiere_reparacion": [],
                "explicacion_cliente": "",
                "explicacion_tecnica": "",
                "traza": traza,
                "hechos": sorted(list(sset)),
            }

        # Si la "mejor" no cumple completo, no se diagnostica (política del proyecto)
        # (Esto mantiene la lógica alineada a sistema experto conservador)
        mejores_entry = next((t for t in traza if t["regla_id"] == mejor.get("id")), None)
        if not mejores_entry or not mejores_entry["cumple"]:
            return {
                "diagnostico": "diagnostico_no_posible",
                "regla": None,
                "certeza": 0.0,
                "tipo_falla": "",
                "requiere_reparacion": [],
                "explicacion_cliente": "",
                "explicacion_tecnica": "",
                "traza": traza,
                "hechos": sorted(list(sset)),
            }

        return {
            "diagnostico": mejor.get("conclusion"),
            "regla": mejor.get("id"),
            "regla_nombre": mejor.get("nombre", ""),
            "certeza": float(mejor.get("certeza", 0.0)),
            "tipo_falla": mejor.get("tipo_falla", ""),
            "requiere_reparacion": mejor.get("requiere_reparacion", []),
            "explicacion_cliente": mejor.get("explicacion_cliente", ""),
            "explicacion_tecnica": mejor.get("explicacion_tecnica", ""),
            "condiciones": mejor.get("condiciones", []),
            "traza": traza,
            "hechos": sorted(list(sset)),
        }

    # -------------------------
    # Explicación por perfil
    # -------------------------
    def explicar(self, resultado: Dict[str, Any], perfil: str) -> str:
        perfil = (perfil or "cliente").strip().lower()
        if perfil not in ("cliente", "aprendiz", "experto"):
            perfil = "cliente"

        diagnostico = resultado.get("diagnostico", "diagnostico_no_posible")
        regla = resultado.get("regla")
        regla_nombre = resultado.get("regla_nombre", "")
        certeza = float(resultado.get("certeza", 0.0))
        tipo_falla = resultado.get("tipo_falla", "")
        reparaciones = resultado.get("requiere_reparacion", []) or []
        hechos = resultado.get("hechos", []) or []
        traza = resultado.get("traza", []) or []
        condiciones = resultado.get("condiciones", []) or []

        if diagnostico == "diagnostico_no_posible":
            return self._explicacion_sin_diagnostico(perfil, hechos, traza)

        if perfil == "cliente":
            base = (resultado.get("explicacion_cliente", "") or "").strip()
            return self._explicacion_cliente(diagnostico, certeza, tipo_falla, base, reparaciones)

        if perfil == "aprendiz":
            base = (resultado.get("explicacion_tecnica", "") or "").strip()
            return self._explicacion_aprendiz(
                diagnostico=diagnostico,
                regla_id=regla,
                regla_nombre=regla_nombre,
                certeza=certeza,
                condiciones=condiciones,
                hechos=hechos,
                base_tecnica=base,
                reparaciones=reparaciones,
                traza=traza,
            )

        # experto
        return self._explicacion_experto(
            diagnostico=diagnostico,
            regla_id=regla,
            regla_nombre=regla_nombre,
            certeza=certeza,
            condiciones=condiciones,
            hechos=hechos,
            tipo_falla=tipo_falla,
            reparaciones=reparaciones,
            traza=traza,
        )

    # -------------------------
    # Formateadores de salida
    # -------------------------
    def _pct(self, x: float) -> str:
        return f"{round(x * 100, 0):.0f}%"

    def _join(self, items: List[str]) -> str:
        return ", ".join(items) if items else "N/A"

    def _explicacion_sin_diagnostico(self, perfil: str, hechos: List[str], traza: List[Dict[str, Any]]) -> str:
        if perfil == "cliente":
            return (
                f"{self.DIV}\n"
                f"Diagnóstico: NO DISPONIBLE\n"
                f"{self.DIV}\n"
                f"No se pudo obtener un diagnóstico con las reglas actuales.\n"
                f"Esto puede pasar si faltan reglas o si los síntomas no coinciden con ningún caso conocido.\n\n"
                f"¿Qué puedes hacer ahora?\n"
                f"- Verifica si escribiste correctamente los síntomas.\n"
                f"- Si el problema continúa, se recomienda revisión en taller.\n"
                f"{self.DIV}"
            )

        if perfil == "aprendiz":
            # Mostrar los 2 mejores candidatos por score y certeza para guiar adquisición
            candidatos = sorted(
                traza,
                key=lambda t: (t.get("score", 0.0), t.get("certeza", 0.0), len(t.get("matched", []))),
                reverse=True
            )[:2]

            lines = [
                self.DIV,
                "Diagnóstico: NO DISPONIBLE (no hubo match completo)",
                self.DIV,
                f"Hechos ingresados: {self._join(hechos)}",
                "",
                "Candidatos cercanos (para guiar nuevas reglas o preguntas):"
            ]
            if not candidatos:
                lines.append("- (sin candidatos)")
            else:
                for c in candidatos:
                    lines.append(
                        f"- {c.get('regla_id')} score={c.get('score')} certeza={c.get('certeza')} "
                        f"faltan: {self._join(c.get('missing', []))}"
                    )

            lines.append("")
            lines.append("Sugerencia: vuelve a Adquisición para capturar una regla que cubra los síntomas faltantes.")
            lines.append(self.DIV)
            return "\n".join(lines)

        # experto
        candidatos = sorted(
            traza,
            key=lambda t: (t.get("cumple", False), t.get("score", 0.0), t.get("certeza", 0.0), len(t.get("matched", []))),
            reverse=True
        )[:5]

        lines = [
            self.DIV,
            "Diagnóstico: NO DISPONIBLE (no hubo match completo)",
            self.DIV,
            f"Hechos ingresados: {self._join(hechos)}",
            "",
            "TRAZA resumida (top 5 reglas por score/certeza):"
        ]
        for t in candidatos:
            lines.append(
                f"- {t.get('regla_id')} cumple={t.get('cumple')} score={t.get('score')} certeza={t.get('certeza')} "
                f"missing=[{self._join(t.get('missing', []))}] -> {t.get('conclusion')}"
            )
        lines.append("")
        lines.append("Acción recomendada: crear regla nueva o refinar condiciones para cubrir este patrón.")
        lines.append(self.DIV)
        return "\n".join(lines)

    def _explicacion_cliente(
        self,
        diagnostico: str,
        certeza: float,
        tipo_falla: str,
        base: str,
        reparaciones: List[str],
    ) -> str:
        lines = [
            self.DIV,
            "EXPLICACIÓN PARA CLIENTE (lenguaje sencillo)",
            self.DIV,
            f"Diagnóstico: {diagnostico}",
            f"Nivel de confianza: {self._pct(certeza)}",
        ]
        if tipo_falla:
            lines.append(f"Tipo de falla: {tipo_falla}")

        if base:
            lines.append("")
            lines.append(base)

        lines.append("")
        if reparaciones:
            lines.append("¿Qué hacer ahora?: " + self._join(reparaciones))
        else:
            lines.append("¿Qué hacer ahora?: Revisión general en taller (sin acción específica).")

        lines.append(self.DIV)
        return "\n".join(lines)

    def _explicacion_aprendiz(
        self,
        diagnostico: str,
        regla_id: str,
        regla_nombre: str,
        certeza: float,
        condiciones: List[str],
        hechos: List[str],
        base_tecnica: str,
        reparaciones: List[str],
        traza: List[Dict[str, Any]],
    ) -> str:
        # Buscar traza de la regla ganadora
        info = next((t for t in traza if t.get("regla_id") == regla_id), None)
        matched = info.get("matched", []) if info else []
        missing = info.get("missing", []) if info else []

        lines = [
            self.DIV,
            "EXPLICACIÓN PARA APRENDIZ (detalle técnico)",
            self.DIV,
            f"Diagnóstico: {diagnostico}",
            f"Regla aplicada: {regla_id}" + (f" — {regla_nombre}" if regla_nombre else ""),
            f"Certeza (regla): {certeza}",
            "",
            f"Hechos (síntomas) ingresados: {self._join(hechos)}",
            f"Condiciones de la regla: {self._join([str(c) for c in condiciones])}",
            f"Condiciones cumplidas: {self._join(matched)}",
            f"Condiciones faltantes: {self._join(missing)}",
        ]

        if base_tecnica:
            lines.append("")
            lines.append("Justificación técnica:")
            lines.append(base_tecnica)

        lines.append("")
        lines.append("Acciones sugeridas: " + self._join(reparaciones) if reparaciones else "Acciones sugeridas: N/A")

        # Mini-refuerzo de cómo decidió el motor (alineado a metodología)
        lines.append("")
        lines.append("Cómo decidió el sistema:")
        lines.append("- Primero busca reglas con match completo (todas las condiciones).")
        lines.append("- Si hay varias, elige la de mayor certeza y más específica (más condiciones).")

        lines.append(self.DIV)
        return "\n".join(lines)

    def _explicacion_experto(
        self,
        diagnostico: str,
        regla_id: str,
        regla_nombre: str,
        certeza: float,
        condiciones: List[str],
        hechos: List[str],
        tipo_falla: str,
        reparaciones: List[str],
        traza: List[Dict[str, Any]],
    ) -> str:
        # Ordenar traza por "mejor a peor"
        traza_sorted = sorted(
            traza,
            key=lambda t: (
                1 if t.get("cumple") else 0,
                float(t.get("certeza", 0.0)),
                len(t.get("matched", [])),
                float(t.get("score", 0.0)),
            ),
            reverse=True
        )

        win = next((t for t in traza_sorted if t.get("regla_id") == regla_id), None)
        win_missing = win.get("missing", []) if win else []

        lines = [
            self.DIV,
            "EXPLICACIÓN PARA EXPERTO (traza y descartes)",
            self.DIV,
            f"Diagnóstico: {diagnostico}",
            f"Regla ganadora: {regla_id}" + (f" — {regla_nombre}" if regla_nombre else ""),
            f"Certeza: {certeza}",
        ]
        if tipo_falla:
            lines.append(f"Tipo de falla: {tipo_falla}")

        lines.extend([
            "",
            f"Hechos (síntomas): {self._join(hechos)}",
            f"Condiciones ganadoras: {self._join([str(c) for c in condiciones])}",
            f"Faltantes en ganadora: {self._join(win_missing)}",
            "",
            "TRAZA COMPLETA (ordenada):"
        ])

        for t in traza_sorted:
            motivo = ""
            if not t.get("cumple"):
                motivo = f"DESCARTADA (faltan: {self._join(t.get('missing', []))})"
            else:
                # Cumple pero perdió: menor certeza o menor especificidad
                if t.get("regla_id") != regla_id:
                    motivo = "DESCARTADA (cumple pero menor prioridad: certeza/especificidad)"

            lines.append(
                f"- {t.get('regla_id')} cumple={t.get('cumple')} score={t.get('score')} certeza={t.get('certeza')} "
                f"matched=[{self._join(t.get('matched', []))}] missing=[{self._join(t.get('missing', []))}] "
                f"-> {t.get('conclusion')} {motivo}"
            )

        if reparaciones:
            lines.append("")
            lines.append("Requiere reparación: " + self._join(reparaciones))

        lines.append(self.DIV)
        return "\n".join(lines)

    # -------------------------
    # API usada por la CLI
    # -------------------------
    def diagnosticar(self, sintomas: List[str], perfil: str = "cliente") -> Tuple[str, str, Optional[str], float]:
        """
        Retorna:
        (diagnostico, explicacion, regla_id, certeza)
        """
        resultado = self.inferir(sintomas)
        explicacion = self.explicar(resultado, perfil)
        return (
            resultado.get("diagnostico", "diagnostico_no_posible"),
            explicacion,
            resultado.get("regla"),
            float(resultado.get("certeza", 0.0)),
        )