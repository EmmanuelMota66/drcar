from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from modulos.dataset_store import DatasetStore


class AdquisicionConocimiento:
    """
    MÓDULO 1 — Adquisición del Conocimiento

    Objetivo (según ejemplo del profesor):
    - Presentar escenarios concretos.
    - Permitir formular preguntas al experto simulado.
    - Registrar reglas extraídas.
    - Mostrar salida "visual e informativa" (Tú / Experto / Regla capturada).

    En el dataset:
    - escenarios_adquisicion[] contiene:
        - contexto
        - preguntas_sugeridas
        - respuesta_base
        - respuestas_por_keyword
        - regla_extraida: { "id": "SSB_Rx" }

    Este módulo:
    - Simula entrevista.
    - Marca la regla como capturada en store.reglas_capturadas.
    - Muestra la regla completa consultándola en store.reglas_criticas.
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, store: DatasetStore):
        self.store = store

    # -------------------------
    # Compatibilidad con CLI
    # -------------------------
    def iniciar_entrevistas(self) -> None:
        """Alias para mantener compatibilidad con la CLI."""
        self.ejecutar()

    # -------------------------
    # Ejecución principal
    # -------------------------
    def ejecutar(self) -> None:
        escenarios = self.store.escenarios
        if not escenarios:
            print("No hay escenarios de adquisición en el dataset.")
            return

        expert = (self.store.data.get("expert_simulation") or {})
        expert_name = expert.get("expert_name", "Experto")
        role = expert.get("role", "Especialista")
        yrs = expert.get("experience_years", None)

        self._banner("SIMULACIÓN: Adquisición de conocimiento mediante escenarios reales")
        print("\nContexto:")
        if yrs is not None:
            print(f"Estás entrevistando a {expert_name}, {role} con {yrs} años de experiencia.\n")
        else:
            print(f"Estás entrevistando a {expert_name}, {role}.\n")

        print("Selecciona un modo:")
        print("1) DEMOSTRACIÓN (como ejemplo del profesor): recorre escenarios automáticamente")
        print("2) INTERACTIVO: eliges escenario y pregunta (más realista)")
        print("0) Regresar")

        op = input("Elige opción: ").strip()

        if op == "1":
            self._modo_demostracion(escenarios, expert_name)
        elif op == "2":
            self._modo_interactivo(escenarios, expert_name)
        else:
            return

    # -------------------------
    # Modos
    # -------------------------
    def _modo_demostracion(self, escenarios: List[Dict[str, Any]], expert_name: str) -> None:
        """
        Modo 'presentación' (como en el PDF):
        - Por cada escenario, toma la primera pregunta sugerida (si existe).
        - Muestra Tú / Experto / Regla capturada.
        """
        capt_antes = set(self.store.reglas_capturadas_ids)
        nuevas: List[str] = []

        for i, scn in enumerate(escenarios, 1):
            pregunta = self._pregunta_por_defecto(scn)
            respuesta = self._respuesta_experto(scn, pregunta)

            self._imprimir_escenario(i, scn, pregunta, expert_name, respuesta)

            regla_id = self._regla_id_extraida(scn)
            if regla_id:
                es_nueva = self._capturar_regla(regla_id)
                if es_nueva:
                    nuevas.append(regla_id)
                self._imprimir_regla_capturada(regla_id)
            else:
                print("\n⚠️ Este escenario no tiene 'regla_extraida.id'.")

            print()  # espacio entre escenarios

        self.store.save()
        self._resultado_final(capt_antes, nuevas)

    def _modo_interactivo(self, escenarios: List[Dict[str, Any]], expert_name: str) -> None:
        """
        Modo interactivo:
        - Lista escenarios.
        - Usuario elige uno.
        - Usuario elige pregunta sugerida o escribe una.
        - Simula respuesta del experto con keywords.
        - Captura regla asociada al escenario.
        """
        capt_antes = set(self.store.reglas_capturadas_ids)

        while True:
            self._banner("ADQUISICIÓN (INTERACTIVO) — Selección de escenario")
            self._listar_escenarios(escenarios)

            raw = input("\nElige escenario (número) o 0 para salir: ").strip()
            if raw == "0":
                break

            idx = self._parse_int(raw)
            if idx is None or idx < 1 or idx > len(escenarios):
                print("Opción inválida.")
                input("Enter para continuar...")
                continue

            scn = escenarios[idx - 1]

            self._banner(f"ESCENARIO {idx}: {scn.get('id', f'SCN_{idx:02d}')}")
            print("Contexto:")
            print(scn.get("contexto", "(sin contexto)"))
            print("\nPreguntas sugeridas:")
            preguntas = scn.get("preguntas_sugeridas", []) or []
            if preguntas:
                for i, p in enumerate(preguntas, 1):
                    print(f"{i}) {p}")
                print("0) Escribir mi propia pregunta")
            else:
                print("(No hay preguntas sugeridas, escribe una pregunta.)")

            rawq = input("\nElige pregunta: ").strip()
            pregunta = ""

            if preguntas and rawq != "0":
                qidx = self._parse_int(rawq)
                if qidx is None or qidx < 1 or qidx > len(preguntas):
                    print("Selección inválida. Se usará la primera pregunta sugerida.")
                    pregunta = preguntas[0]
                else:
                    pregunta = preguntas[qidx - 1]
            else:
                pregunta = input('Tú (escribe tu pregunta): ').strip()
                if not pregunta:
                    pregunta = self._pregunta_por_defecto(scn)

            respuesta = self._respuesta_experto(scn, pregunta)

            # Mostrar diálogo estilo profesor
            print("\n" + self.DIV)
            print(f'Tú: "{pregunta}"')
            print(f'\n{expert_name}: "{respuesta}"')
            print(self.DIV)

            regla_id = self._regla_id_extraida(scn)
            if regla_id:
                es_nueva = self._capturar_regla(regla_id)
                self._imprimir_regla_capturada(regla_id)
                if es_nueva:
                    print("✅ Se registró como regla capturada en esta sesión.")
                else:
                    print("ℹ️ La regla ya estaba marcada como capturada.")
                self.store.save()
            else:
                print("⚠️ Este escenario no tiene 'regla_extraida.id'.")

            input("\nEnter para continuar...")

        # Cierre del modo interactivo
        capt_despues = set(self.store.reglas_capturadas_ids)
        nuevas = sorted(list(capt_despues - capt_antes))
        self._resultado_final(capt_antes, nuevas)

    # -------------------------
    # Impresiones estilo “profesor”
    # -------------------------
    def _banner(self, titulo: str) -> None:
        print("\n" + self.LINE)
        print(f" {titulo}")
        print(self.LINE)

    def _imprimir_escenario(
        self, numero: int, scn: Dict[str, Any], pregunta: str, expert_name: str, respuesta: str
    ) -> None:
        print(f"\n ESCENARIO {numero}: {scn.get('contexto', '(sin contexto)')}")
        print(f'\n Tú: "{pregunta}"')
        print(f'\n {expert_name}: "{respuesta}"')

    def _imprimir_regla_capturada(self, regla_id: str) -> None:
        regla = self.store.get_regla_por_id(regla_id)
        print("\n Regla capturada:")
        if not regla:
            print(f" SI ...")
            print(f" ENTONCES ... (regla {regla_id} no encontrada en reglas_criticas)")
            return

        condiciones = regla.get("condiciones", []) or []
        conclusion = regla.get("conclusion", "desconocida")
        certeza = regla.get("certeza", 0.0)

        # Formato tipo ejemplo: SI cond1 Y cond2 ... ENTONCES conclusion (certeza: x)
        if condiciones:
            print(f" SI {' Y '.join(condiciones)}")
        else:
            print(" SI (sin condiciones definidas)")

        print(f" ENTONCES {conclusion} (certeza: {certeza})")

        # “Explicación” (en el dataset hay explicación técnica y para cliente)
        exp_tec = regla.get("explicacion_tecnica", "")
        exp_cli = regla.get("explicacion_cliente", "")

        if exp_tec:
            print(f" Explicación (técnica): {exp_tec}")
        elif exp_cli:
            print(f" Explicación: {exp_cli}")
        else:
            print(" Explicación: (no disponible)")

    # -------------------------
    # Lógica de entrevista
    # -------------------------
    def _pregunta_por_defecto(self, scn: Dict[str, Any]) -> str:
        preguntas = scn.get("preguntas_sugeridas", []) or []
        if preguntas and isinstance(preguntas, list) and isinstance(preguntas[0], str):
            return preguntas[0]
        return "¿Qué verificaría primero y por qué?"

    def _respuesta_experto(self, scn: Dict[str, Any], pregunta: str) -> str:
        """
        Respuesta del experto:
        - Base: respuesta_base
        - Si detecta keywords en la pregunta, agrega 'respuestas_por_keyword' relevantes.
        """
        base = scn.get("respuesta_base", "").strip()
        kw_map = scn.get("respuestas_por_keyword", {}) or {}

        # Buscar keywords dentro de la pregunta
        p = (pregunta or "").lower()
        extras: List[str] = []
        if isinstance(kw_map, dict):
            for kw, resp in kw_map.items():
                if isinstance(kw, str) and kw.lower() in p and isinstance(resp, str) and resp.strip():
                    extras.append(resp.strip())

        # Evitar duplicados
        unique_extras = []
        seen = set()
        for e in extras:
            if e not in seen:
                unique_extras.append(e)
                seen.add(e)

        if base and unique_extras:
            return base + " " + " ".join(unique_extras)
        if base:
            return base
        if unique_extras:
            return " ".join(unique_extras)

        # Fallback
        return "Necesitaría más contexto técnico para responder con certeza."

    def _regla_id_extraida(self, scn: Dict[str, Any]) -> Optional[str]:
        regla = scn.get("regla_extraida") or {}
        rid = regla.get("id")
        if isinstance(rid, str) and rid.strip():
            return rid.strip()
        return None

    def _capturar_regla(self, regla_id: str) -> bool:
        """
        Marca la regla como capturada.
        Regresa True si fue nueva, False si ya estaba.
        """
        antes = set(self.store.reglas_capturadas_ids)
        self.store.marcar_regla_capturada(regla_id)
        despues = set(self.store.reglas_capturadas_ids)
        return regla_id in (despues - antes)

    def _resultado_final(self, capt_antes: set, nuevas: List[str]) -> None:
        capt_despues = set(self.store.reglas_capturadas_ids)

        reglas_crit = set(self.store.reglas_criticas_ids)
        capt_crit = capt_despues.intersection(reglas_crit)
        cobertura = (len(capt_crit) / len(reglas_crit) * 100.0) if reglas_crit else 0.0

        self._banner("RESULTADO DE LA ADQUISICIÓN")
        print(f"Reglas capturadas totales: {len(capt_despues)}")
        if nuevas:
            print(f"Nuevas en esta sesión: {', '.join(sorted(nuevas))}")
        else:
            print("Nuevas en esta sesión: ninguna (ya estaban marcadas).")

        print(f"Cobertura estimada del dominio (reglas críticas): {cobertura:.1f}%")

        print("\n LECCIÓN CLAVE:")
        print(" Escenarios concretos revelan heurísticas que preguntas abstractas suelen ocultar.")
        print(" Si hay casos no cubiertos, eso no es “fracaso”: es parte normal del ciclo IC (iterar).")

    # -------------------------
    # Helpers
    # -------------------------
    def _listar_escenarios(self, escenarios: List[Dict[str, Any]]) -> None:
        for i, scn in enumerate(escenarios, 1):
            sid = scn.get("id", f"SCN_{i:02d}")
            ctx = (scn.get("contexto") or "").strip()
            # Recortar para que sea “visual e informativo”
            if len(ctx) > 90:
                ctx = ctx[:87] + "..."
            print(f"{i}) {sid} — {ctx}")

    @staticmethod
    def _parse_int(s: str) -> Optional[int]:
        try:
            return int(s)
        except Exception:
            return None