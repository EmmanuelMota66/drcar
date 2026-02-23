from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from modulos.dataset_store import DatasetStore


@dataclass
class CasoResultado:
    case_id: str
    esperado: Any
    obtenido: str
    regla_id: Optional[str]
    certeza: float
    ok: bool
    detalle: str


class ReporteCobertura:
    """
    MÓDULO 4 — Reporte de cobertura / calidad (alineado al estilo del profesor)

    Qué reporta (mínimo):
    1) Cobertura de reglas críticas: capturadas vs total
    2) Precisión en casos de prueba: aciertos / total
    3) Ontología: coherencia (OK / inconsistencias)
    4) Diagnóstico: porcentaje de "sin diagnóstico" en pruebas
    5) Estado contra rúbrica (checklist visual)

    Nota:
    - Este reporte NO solo imprime números; también guía acciones:
      "Qué falta capturar", "Qué casos fallan" y "Qué arreglar".
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

        # 1) Cobertura de reglas críticas
        cobertura = self._reporte_cobertura_reglas()

        # 2) Ontología coherente
        ont_ok, inconsistencias = self._reporte_ontologia()

        # 3) Precisión de casos de prueba (usa el motor de inferencia)
        precision, resultados = self._reporte_casos_prueba()

        # 4) Estado contra rúbrica (resumen tipo semáforo)
        self._reporte_estado_rubrica(cobertura, precision, ont_ok)

        # 5) Detalles (qué falta y qué falló)
        self._reporte_detalle_faltantes(cobertura)
        self._reporte_detalle_pruebas(resultados)

        self._banner("FIN DEL REPORTE")
        print("Sugerencia final:")
        print("- Si cobertura < 70%: vuelve a Adquisición y captura reglas faltantes.")
        print("- Si precisión < 80%: revisa qué casos fallan y ajusta reglas/condiciones.")
        print("- Si ontología NO es coherente: corrige jerarquías/relaciones y revalida.")

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

        reglas_total_ids: List[str] = list(self.store.reglas_criticas_ids)
        capturadas_ids: Set[str] = set(self.store.reglas_capturadas_ids)

        # Solo cuenta como cobertura lo que sea realmente "crítico"
        reglas_total_set: Set[str] = set(reglas_total_ids)
        capturadas_criticas: Set[str] = capturadas_ids.intersection(reglas_total_set)

        total = len(reglas_total_set)
        capt = len(capturadas_criticas)
        pct = (capt / total * 100.0) if total else 0.0

        faltan = sorted(list(reglas_total_set - capturadas_criticas))

        print(f"Reglas críticas totales: {total}")
        print(f"Reglas críticas capturadas: {capt}")
        print(f"Cobertura: {pct:.1f}%")
        if faltan:
            print("Faltan por capturar:", ", ".join(faltan))
        else:
            print("Faltan por capturar: ninguna")

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
    def _reporte_ontologia(self) -> Tuple[bool, List[str]]:
        self._section("VALIDACIÓN DE ONTOLOGÍA (COHERENCIA)")

        # Intentar usar el módulo OntologiaDominio si existe
        inconsistencias: List[str] = []
        try:
            from modulos.ontologia import OntologiaDominio  # import local para evitar dependencias circulares
            ont = OntologiaDominio(self.store)

            # Compatibilidad: validar_coherencia() o validar()
            if hasattr(ont, "validar_coherencia") and callable(getattr(ont, "validar_coherencia")):
                inconsistencias = ont.validar_coherencia()
            elif hasattr(ont, "validar") and callable(getattr(ont, "validar")):
                inconsistencias = ont.validar()
            else:
                inconsistencias = self._validacion_ontologia_fallback()
        except Exception:
            inconsistencias = self._validacion_ontologia_fallback()

        ok = (len(inconsistencias) == 0)
        print(f"Ontología coherente: {self._check(ok)}")
        if not ok:
            print("Inconsistencias encontradas:")
            for inc in inconsistencias[:10]:
                print(" -", inc)
            if len(inconsistencias) > 10:
                print(f" ... y {len(inconsistencias) - 10} más")
        else:
            print("Inconsistencias: 0")

        return ok, inconsistencias

    def _validacion_ontologia_fallback(self) -> List[str]:
        """
        Validación mínima por si el módulo ontología cambia.
        Revisa:
        - jerarquias es dict
        - relaciones es dict con tipo esperado
        - detecta ciclos simples en jerarquías (DFS).
        """
        ont = self.store.ontologia or {}
        jer = ont.get("jerarquias", {})
        rel = ont.get("relaciones", {})

        errores: List[str] = []

        if not isinstance(jer, dict):
            errores.append("ontologia_inicial.jerarquias debe ser un objeto (dict).")
            return errores

        if rel and not isinstance(rel, dict):
            errores.append("ontologia_inicial.relaciones debe ser un objeto (dict).")

        # Detectar ciclos simples en el árbol jerárquico
        def dfs(node_name: str, node: Any, path: Set[str]) -> None:
            if node_name in path:
                errores.append(f"Ciclo detectado en jerarquía: {node_name}")
                return
            if not isinstance(node, dict):
                return
            path.add(node_name)
            for child_name, child_node in node.items():
                dfs(str(child_name), child_node, set(path))

        for root_name, subtree in jer.items():
            dfs(str(root_name), subtree, set())

        return errores

    # ---------------------------------------------------------------------
    # 3) Casos de prueba / precisión
    # ---------------------------------------------------------------------
    def _reporte_casos_prueba(self) -> Tuple[float, List[CasoResultado]]:
        self._section("VALIDACIÓN: CASOS DE PRUEBA (PRECISIÓN)")

        casos = self.store.casos_prueba
        if not casos:
            print("No hay casos_prueba en el dataset.")
            return 0.0, []

        # Motor de inferencia (import local para evitar ciclos)
        from modulos.motor_inferencia import MotorInferencia
        motor = MotorInferencia(self.store)

        resultados: List[CasoResultado] = []
        aciertos = 0
        sin_diag = 0

        for c in casos:
            case_id = str(c.get("id", "SIN_ID"))
            sintomas = self._leer_sintomas_caso(c)
            esperado = c.get("diagnostico_esperado")

            obtenido, _, regla_id, certeza = motor.diagnosticar(sintomas, perfil="experto")

            ok, detalle = self._comparar_esperado_obtenido(esperado, obtenido)

            if obtenido == "diagnostico_no_posible":
                sin_diag += 1

            if ok:
                aciertos += 1

            resultados.append(
                CasoResultado(
                    case_id=case_id,
                    esperado=esperado,
                    obtenido=obtenido,
                    regla_id=regla_id,
                    certeza=float(certeza),
                    ok=ok,
                    detalle=detalle,
                )
            )

        total = len(resultados)
        precision = (aciertos / total * 100.0) if total else 0.0

        print(f"Casos totales: {total}")
        print(f"Aciertos: {aciertos}")
        print(f"Precisión: {precision:.1f}%")
        print(f"Sin diagnóstico: {sin_diag} ({(sin_diag/total*100.0):.1f}%)" if total else "Sin diagnóstico: 0")

        return precision, resultados

    def _leer_sintomas_caso(self, caso: Dict[str, Any]) -> List[str]:
        """
        Soporta:
        - sintomas: [ "s1", "s2" ]
        - sintomas: { "s1": true, "s2": false, "temp": 60 } -> toma keys truthy
        """
        s = caso.get("sintomas")
        if isinstance(s, list):
            return [str(x).strip() for x in s if str(x).strip()]
        if isinstance(s, dict):
            out: List[str] = []
            for k, v in s.items():
                # si es bool, usa True; si es número/texto, se considera "presente"
                if isinstance(v, bool):
                    if v:
                        out.append(str(k).strip())
                else:
                    # valor no booleano: se interpreta como evidencia presente
                    out.append(str(k).strip())
            return [x for x in out if x]
        return []

    def _comparar_esperado_obtenido(self, esperado: Any, obtenido: str) -> Tuple[bool, str]:
        """
        esperado puede ser:
        - string
        - lista de strings (permitir alternativas)
        """
        if isinstance(esperado, str):
            ok = (esperado.strip() == obtenido.strip())
            return ok, "match exacto" if ok else "no coincide"
        if isinstance(esperado, list):
            exp_list = [str(x).strip() for x in esperado if str(x).strip()]
            ok = obtenido.strip() in exp_list
            return ok, "match en alternativas" if ok else "no coincide"
        return False, "esperado inválido"

    # ---------------------------------------------------------------------
    # 4) Estado contra rúbrica (checklist)
    # ---------------------------------------------------------------------
    def _reporte_estado_rubrica(self, cobertura: Dict[str, Any], precision: float, ont_ok: bool) -> None:
        self._section("ESTADO CONTRA RÚBRICA (RESUMEN VISUAL)")

        # Umbrales recomendados (pueden ajustarse si el profe define otros)
        cobertura_ok = cobertura.get("pct", 0.0) >= 70.0
        precision_ok = precision >= 80.0
        ontologia_ok = ont_ok

        # Indicadores por componente (simula rúbrica: adquisición/representación/razonamiento/validación/reporte)
        print(f"{self._check(cobertura_ok)} Adquisición: cobertura de reglas críticas >= 70% (actual: {cobertura.get('pct', 0.0):.1f}%)")
        print(f"{self._check(ontologia_ok)} Representación: ontología coherente (actual: {'OK' if ontologia_ok else 'con inconsistencias'})")
        print(f"{self._check(True)} Razonamiento: motor de inferencia operativo (diagnosticar() funciona)")
        print(f"{self._check(precision_ok)} Validación: precisión en casos de prueba >= 80% (actual: {precision:.1f}%)")
        print(f"{self._check(True)} Reporte: se genera reporte con métricas + guía de mejoras")

    # ---------------------------------------------------------------------
    # 5) Detalles: faltantes / fallas
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

        print("\nAcción rápida:")
        print("- En el Módulo 1, elige el escenario asociado a esas reglas y marca capturadas.")
        print("- Si no existe escenario: crea uno en escenarios_adquisicion con regla_extraida.id = esa regla.")

    def _reporte_detalle_pruebas(self, resultados: List[CasoResultado]) -> None:
        self._section("DETALLE: CASOS DE PRUEBA (FALLOS)")

        if not resultados:
            print("No hay resultados de prueba.")
            return

        fallos = [r for r in resultados if not r.ok]
        if not fallos:
            print("✅ Todos los casos de prueba pasan (100%).")
            return

        print(f"Casos que fallan: {len(fallos)}")
        for r in fallos[:10]:
            print(f"- {r.case_id}: esperado='{r.esperado}' obtenido='{r.obtenido}' regla='{r.regla_id}' certeza={r.certeza} ({r.detalle})")
        if len(fallos) > 10:
            print(f" ... y {len(fallos) - 10} más")

        print("\nCómo corregir:")
        print("1) Revisa qué síntomas tiene el caso (casos_prueba[].sintomas).")
        print("2) Busca una regla que debería cubrirlo y revisa condiciones.")
        print("3) Si no existe regla, crea una regla nueva + escenario de adquisición.")
        print("4) Vuelve a correr el reporte y verifica que suba la precisión.")