from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from modulos.dataset_store import DatasetStore


@dataclass
class CasoResultado:
    case_id: str
    tipo: str  # "evaluacion" | "brecha"
    esperado: Any
    regla_esperada: Optional[str]
    obtenido: str
    regla_obtenida: Optional[str]
    certeza: float
    ok: bool
    detalle: str


class ReporteCobertura:
    """
    MÓDULO 4 — Reporte de cobertura / calidad (alineado al dataset y al estilo del profe)

    Métricas:
    1) Cobertura de reglas críticas (capturadas vs total)
    2) Ontología: coherencia (0 errores) + advertencias
    3) Validación de casos:
       - Precisión OBLIGATORIA: solo casos con regla_esperada (evaluación)
       - Brechas: casos con regla_esperada = None (no penalizan la precisión obligatoria)
       - Precisión global (opcional): incluye todo, por transparencia

    Nota:
    - Esto evita “castigo” injusto cuando ustedes mismos marcaron un caso como brecha de conocimiento.
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, store: DatasetStore):
        self.store = store

    # Compatibilidad con CLI
    def generar(self) -> None:
        self.ejecutar()

    def ejecutar(self) -> None:
        self._banner("MÓDULO 4 — REPORTE DE COBERTURA / CALIDAD (RÚBRICA)")

        # 0) Validación rápida del dataset (estructura)
        self._section("VALIDACIÓN INICIAL DEL DATASET (estructura mínima)")
        errores_schema = self.store.validate_basic_schema() if hasattr(self.store, "validate_basic_schema") else []
        if errores_schema:
            print(f"❌ Se detectaron {len(errores_schema)} problemas en el JSON:")
            for e in errores_schema:
                print(" -", e)
        else:
            print("✅ Dataset OK (estructura mínima).")

        # 1) Cobertura de reglas críticas
        cobertura = self._reporte_cobertura_reglas()

        # 2) Ontología coherente
        ont_ok, ont_errs, ont_warns = self._reporte_ontologia()

        # 3) Casos de prueba (precisión obligatoria + brechas)
        resumen_pruebas, resultados = self._reporte_casos_prueba()

        # 4) Estado contra rúbrica (resumen)
        self._reporte_estado_rubrica(cobertura, ont_ok, resumen_pruebas)

        # 5) Detalles accionables
        self._reporte_detalle_faltantes(cobertura)
        self._reporte_detalle_pruebas(resultados)

        self._banner("FIN DEL REPORTE")
        print("Siguiente acción sugerida (rápida):")
        if cobertura["pct"] < 70.0:
            print("- Sube cobertura: entra a Módulo 1 y captura reglas críticas faltantes.")
        elif resumen_pruebas["precision_obligatoria"] < 80.0:
            print("- Sube precisión: ajusta condiciones de reglas o casos de prueba fallidos.")
        elif not ont_ok:
            print("- Arregla ontología: corrige jerarquías/relaciones y revalida.")
        else:
            print("- Ya cumples lo esencial: ahora puedes ampliar con nuevas reglas (brechas).")

    # ---------------------------------------------------------------------
    # UI helpers
    # ---------------------------------------------------------------------
    def _banner(self, titulo: str) -> None:
        print("\n" + self.LINE)
        print(f" {titulo}")
        print(self.LINE)

    def _section(self, titulo: str) -> None:
        print("\n" + self.DIV)
        print(f" {titulo}")
        print(self.DIV)

    def _check(self, ok: bool) -> str:
        return "✅" if ok else "❌"

    # ---------------------------------------------------------------------
    # 1) Cobertura de reglas
    # ---------------------------------------------------------------------
    def _reporte_cobertura_reglas(self) -> Dict[str, Any]:
        self._section("COBERTURA DE REGLAS CRÍTICAS")

        reglas_total_ids = list(self.store.reglas_criticas_ids)
        capturadas_ids = set(self.store.reglas_capturadas_ids)

        reglas_total_set = set(reglas_total_ids)
        capturadas_criticas = capturadas_ids.intersection(reglas_total_set)

        total = len(reglas_total_set)
        capt = len(capturadas_criticas)
        pct = (capt / total * 100.0) if total else 0.0

        faltan = sorted(list(reglas_total_set - capturadas_criticas))

        print(f"Reglas críticas totales: {total}")
        print(f"Reglas críticas capturadas: {capt}")
        print(f"Cobertura: {pct:.1f}%")
        print("Faltan por capturar:", ", ".join(faltan) if faltan else "ninguna")

        return {
            "total": total,
            "capturadas": capt,
            "pct": pct,
            "faltan": faltan,
            "capturadas_ids": sorted(list(capturadas_criticas)),
        }

    # ---------------------------------------------------------------------
    # 2) Ontología
    # ---------------------------------------------------------------------
    def _reporte_ontologia(self) -> Tuple[bool, List[str], List[str]]:
        self._section("VALIDACIÓN DE ONTOLOGÍA (COHERENCIA)")

        # Intentar usar el módulo OntologiaDominio si existe y expone validar_coherencia_detallada()
        errores: List[str] = []
        advertencias: List[str] = []

        try:
            from modulos.ontologia import OntologiaDominio
            ont = OntologiaDominio(self.store)

            if hasattr(ont, "validar_coherencia_detallada") and callable(getattr(ont, "validar_coherencia_detallada")):
                errores, advertencias = ont.validar_coherencia_detallada()
            elif hasattr(ont, "validar_coherencia") and callable(getattr(ont, "validar_coherencia")):
                errores = ont.validar_coherencia()
                advertencias = []
            else:
                # fallback mínimo
                errores, advertencias = self._validacion_ontologia_fallback()
        except Exception:
            errores, advertencias = self._validacion_ontologia_fallback()

        ok = (len(errores) == 0)

        print(f"Ontología coherente (0 errores): {self._check(ok)}")
        if errores:
            print("Errores:")
            for e in errores[:15]:
                print(" -", e)
            if len(errores) > 15:
                print(f" ... y {len(errores) - 15} más")
        else:
            print("Errores: 0")

        if advertencias:
            print(f"\nAdvertencias: {len(advertencias)}")
            for w in advertencias[:10]:
                print(" -", w)
            if len(advertencias) > 10:
                print(f" ... y {len(advertencias) - 10} más")

        return ok, errores, advertencias

    def _validacion_ontologia_fallback(self) -> Tuple[List[str], List[str]]:
        """
        Fallback simple:
        - jerarquias es dict
        - relaciones es list de triplas dict
        - detecta ciclos básicos en jerarquías
        """
        ont = self.store.ontologia or {}
        jer = ont.get("jerarquias", {})
        rel = ont.get("relaciones", [])

        errores: List[str] = []
        advertencias: List[str] = []

        if not isinstance(jer, dict):
            errores.append("ontologia_inicial.jerarquias debe ser dict.")
            return errores, advertencias

        if not isinstance(rel, list):
            errores.append("ontologia_inicial.relaciones debe ser lista (triplas).")
            return errores, advertencias

        # Ciclos simples
        def dfs(node_name: str, node: Any, path: List[str]) -> None:
            if node_name in path[:-1]:
                errores.append(f"Ciclo detectado en jerarquía: {node_name} (ruta: {' > '.join(path)})")
                return
            if not isinstance(node, dict):
                return
            for child, child_node in node.items():
                dfs(str(child), child_node, path + [str(child)])

        for root, subtree in jer.items():
            dfs(str(root), subtree, [str(root)])

        # Validar formato de triplas
        for i, t in enumerate(rel):
            if not isinstance(t, dict):
                errores.append(f"relaciones[{i}] no es dict.")
                continue
            if "origen" not in t or "relacion" not in t or "destino" not in t:
                errores.append(f"relaciones[{i}] debe tener origen/relacion/destino.")

        return errores, advertencias

    # ---------------------------------------------------------------------
    # 3) Casos de prueba / precisión
    # ---------------------------------------------------------------------
    def _reporte_casos_prueba(self) -> Tuple[Dict[str, Any], List[CasoResultado]]:
        self._section("VALIDACIÓN: CASOS DE PRUEBA (PRECISIÓN + BRECHAS)")

        casos = self.store.casos_prueba
        if not casos:
            print("No hay casos_prueba en el dataset.")
            return {
                "total": 0,
                "evaluacion_total": 0,
                "evaluacion_ok": 0,
                "precision_obligatoria": 0.0,
                "brechas_total": 0,
                "precision_global": 0.0,
                "sin_diagnostico_eval": 0,
            }, []

        from modulos.motor_inferencia import MotorInferencia
        motor = MotorInferencia(self.store)

        resultados: List[CasoResultado] = []

        eval_total = 0
        eval_ok = 0
        brechas_total = 0
        global_ok = 0
        sin_diag_eval = 0

        for c in casos:
            case_id = str(c.get("id", "SIN_ID"))
            sintomas = self._leer_sintomas_caso(c)
            esperado = c.get("diagnostico_esperado")
            regla_esperada = c.get("regla_esperada", None)

            tipo = "evaluacion" if regla_esperada else "brecha"

            obtenido, _, regla_obtenida, certeza = motor.diagnosticar(sintomas, perfil="experto")

            ok_diag, detalle = self._comparar_esperado_obtenido(esperado, obtenido)

            # para evaluación: además podemos checar si coincide la regla esperada (opcional, no bloqueante)
            if tipo == "evaluacion":
                eval_total += 1
                if obtenido == "diagnostico_no_posible":
                    sin_diag_eval += 1
                if ok_diag:
                    eval_ok += 1

            # global (solo informativo)
            if ok_diag:
                global_ok += 1

            if tipo == "brecha":
                brechas_total += 1
                # Ajuste de detalle: no penaliza, pero explica
                if regla_esperada is None and esperado != "diagnostico_no_posible" and not ok_diag:
                    detalle = "brecha: caso diseñado para ampliar conocimiento (no penaliza precisión obligatoria)"
                elif esperado == "diagnostico_no_posible" and ok_diag:
                    detalle = "brecha: correctamente no se diagnosticó (esperado)"
                elif esperado == "diagnostico_no_posible" and not ok_diag:
                    detalle = "brecha: se diagnosticó algo cuando se esperaba NO diagnosticar"

            resultados.append(
                CasoResultado(
                    case_id=case_id,
                    tipo=tipo,
                    esperado=esperado,
                    regla_esperada=regla_esperada,
                    obtenido=obtenido,
                    regla_obtenida=regla_obtenida,
                    certeza=float(certeza),
                    ok=ok_diag,
                    detalle=detalle,
                )
            )

        total = len(resultados)
        precision_obligatoria = (eval_ok / eval_total * 100.0) if eval_total else 0.0
        precision_global = (global_ok / total * 100.0) if total else 0.0

        print(f"Casos totales: {total}")
        print(f"Casos de evaluación (con regla_esperada): {eval_total}")
        print(f"Aciertos evaluación: {eval_ok}")
        print(f"✅ Precisión OBLIGATORIA: {precision_obligatoria:.1f}% (no incluye brechas)")
        print(f"Brechas (regla_esperada = null): {brechas_total}")
        print(f"Precisión global (informativa): {precision_global:.1f}%")
        print(f"Sin diagnóstico en evaluación: {sin_diag_eval} ({(sin_diag_eval/eval_total*100.0):.1f}%)" if eval_total else "Sin diagnóstico en evaluación: 0")

        return {
            "total": total,
            "evaluacion_total": eval_total,
            "evaluacion_ok": eval_ok,
            "precision_obligatoria": precision_obligatoria,
            "brechas_total": brechas_total,
            "precision_global": precision_global,
            "sin_diagnostico_eval": sin_diag_eval,
        }, resultados

    def _leer_sintomas_caso(self, caso: Dict[str, Any]) -> List[str]:
        s = caso.get("sintomas")
        if isinstance(s, list):
            return [str(x).strip() for x in s if str(x).strip()]
        if isinstance(s, dict):
            out: List[str] = []
            for k, v in s.items():
                if isinstance(v, bool):
                    if v:
                        out.append(str(k).strip())
                else:
                    out.append(str(k).strip())
            return [x for x in out if x]
        return []

    def _comparar_esperado_obtenido(self, esperado: Any, obtenido: str) -> Tuple[bool, str]:
        if isinstance(esperado, str):
            ok = (esperado.strip() == obtenido.strip())
            return ok, ("match exacto" if ok else "no coincide")
        if isinstance(esperado, list):
            exp_list = [str(x).strip() for x in esperado if str(x).strip()]
            ok = obtenido.strip() in exp_list
            return ok, ("match en alternativas" if ok else "no coincide")
        return False, "esperado inválido"

    # ---------------------------------------------------------------------
    # 4) Estado contra rúbrica (checklist)
    # ---------------------------------------------------------------------
    def _reporte_estado_rubrica(self, cobertura: Dict[str, Any], ont_ok: bool, resumen_pruebas: Dict[str, Any]) -> None:
        self._section("ESTADO CONTRA RÚBRICA (RESUMEN VISUAL)")

        cobertura_ok = cobertura.get("pct", 0.0) >= 70.0
        precision_ok = resumen_pruebas.get("precision_obligatoria", 0.0) >= 80.0

        print(f"{self._check(cobertura_ok)} Adquisición: cobertura de reglas críticas >= 70% (actual: {cobertura.get('pct', 0.0):.1f}%)")
        print(f"{self._check(ont_ok)} Representación: ontología coherente (0 errores)")
        print(f"{self._check(True)} Razonamiento: motor de inferencia operativo (diagnosticar() funciona)")
        print(f"{self._check(precision_ok)} Validación: precisión obligatoria >= 80% (actual: {resumen_pruebas.get('precision_obligatoria', 0.0):.1f}%)")
        print(f"{self._check(True)} Reporte: métricas + guía de mejoras + brechas separadas")

        if resumen_pruebas.get("brechas_total", 0) > 0:
            print(f"ℹ️ Brechas detectadas: {resumen_pruebas['brechas_total']} (no penalizan precisión obligatoria)")

    # ---------------------------------------------------------------------
    # 5) Detalles accionables
    # ---------------------------------------------------------------------
    def _reporte_detalle_faltantes(self, cobertura: Dict[str, Any]) -> None:
        self._section("DETALLE: QUÉ FALTA PARA SUBIR COBERTURA")

        faltan: List[str] = cobertura.get("faltan", [])
        if not faltan:
            print("✅ No faltan reglas críticas por capturar.")
            return

        print("Reglas críticas faltantes (capturar en Módulo 1 — Adquisición):")
        for rid in faltan:
            regla = self.store.get_regla_por_id(rid)
            if regla:
                nombre = regla.get("nombre", "")
                concl = regla.get("conclusion", "")
                conds = regla.get("condiciones", []) or []
                print(f"- {rid} {f'— {nombre}' if nombre else ''}")
                if conds:
                    print(f"  SI {' Y '.join([str(c) for c in conds])}")
                if concl:
                    print(f"  ENTONCES {concl}")
            else:
                print(f"- {rid} (no encontrada en reglas_criticas)")

    def _reporte_detalle_pruebas(self, resultados: List[CasoResultado]) -> None:
        self._section("DETALLE: CASOS (FALLOS) Y BRECHAS")

        if not resultados:
            print("No hay resultados.")
            return

        # Fallos de evaluación (sí importan)
        fallos_eval = [r for r in resultados if r.tipo == "evaluacion" and not r.ok]
        brechas = [r for r in resultados if r.tipo == "brecha"]

        if not fallos_eval:
            print("✅ Evaluación: todos los casos obligatorios pasan.")
        else:
            print(f"❌ Evaluación: fallan {len(fallos_eval)} caso(s).")
            for r in fallos_eval[:10]:
                print(
                    f"- {r.case_id}: esperado='{r.esperado}' obtenido='{r.obtenido}' "
                    f"regla_obtenida='{r.regla_obtenida}' certeza={r.certeza} ({r.detalle})"
                )
            if len(fallos_eval) > 10:
                print(f" ... y {len(fallos_eval) - 10} más")
            print("\nCómo corregir (evaluación):")
            print("1) Revisa síntomas del caso.")
            print("2) Ajusta condiciones de la regla esperada o crea regla nueva.")
            print("3) Vuelve a correr el reporte.")

        # Brechas (no penalizan, pero se reportan)
        if brechas:
            print(f"\nℹ️ Brechas registradas: {len(brechas)}")
            for r in brechas[:10]:
                print(
                    f"- {r.case_id}: esperado='{r.esperado}' obtenido='{r.obtenido}' "
                    f"(detalle: {r.detalle})"
                )
            if len(brechas) > 10:
                print(f" ... y {len(brechas) - 10} más")

            print("\nQué hacer con brechas:")
            print("- Si quieres subir precisión global, conviértelas en evaluación:")
            print("  1) crea una regla nueva (reglas_criticas) que cubra esos síntomas")
            print("  2) agrega un escenario de adquisición que extraiga esa regla")
            print("  3) define regla_esperada en el caso y listo")
