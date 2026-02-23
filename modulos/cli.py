from typing import Any, Dict, List, Set, Optional
import json
import os

# Intento de imports reales (si no existen, no rompe)
MODULOS_OK = True
IMPORT_ERROR: Optional[str] = None

try:
    from modulos.dataset_store import DatasetStore
    from modulos.adquisicion import AdquisicionConocimiento
    from modulos.ontologia import OntologiaDominio
    from modulos.motor_inferencia import MotorInferencia
    from modulos.reporte import ReporteCobertura
except Exception as e:
    MODULOS_OK = False
    IMPORT_ERROR = str(e)
    DatasetStore = None
    AdquisicionConocimiento = None
    OntologiaDominio = None
    MotorInferencia = None
    ReporteCobertura = None


class CLI:
    """
    CLI principal del Simulador de Ingeniería del Conocimiento.

    Objetivo (según el enunciado del profesor):
    - Menú principal con 4 módulos:
        1) Adquisición (entrevistas por escenarios)
        2) Ontología (visualizar + validar coherencia)
        3) Diagnóstico (motor de inferencia + explicación por perfil)
        4) Reporte de cobertura (reglas, casos, ontología, rúbrica)

    Nota:
    - Se mantiene modo STUB como respaldo, pero por defecto se trabaja en REAL.
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, dataset_path: str, modo_stub: bool = False):
        self.dataset_path = os.path.abspath(dataset_path)
        self.modo_stub = modo_stub or (not MODULOS_OK)

        # Dataset para modo stub (solo lectura)
        self.dataset: Dict[str, Any] = self._cargar_dataset_simple(self.dataset_path)

        # Componentes reales (solo si NO stub)
        self.store = None
        self.adq = None
        self.ont = None
        self.motor = None
        self.rep = None

        if not self.modo_stub:
            # DatasetStore ya carga y normaliza el JSON en __init__
            self.store = DatasetStore(self.dataset_path)
            self.adq = AdquisicionConocimiento(self.store)
            self.ont = OntologiaDominio(self.store)
            self.motor = MotorInferencia(self.store)
            self.rep = ReporteCobertura(self.store)

    # -------------------------
    # Utilidades UI
    # -------------------------
    def _banner(self, title: str) -> None:
        print("\n" + self.LINE)
        print(f" {title}")
        print(self.LINE)

    def _pause(self) -> None:
        input("\nPresiona Enter para continuar...")

    def _print_tu_turno(self, bullets: List[str]) -> None:
        print("\n" + self.LINE)
        print(" TU TURNO:")
        print(self.LINE)
        for i, b in enumerate(bullets, 1):
            print(f"{i}. {b}")

    # -------------------------
    # Dataset (modo stub)
    # -------------------------
    def _cargar_dataset_simple(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _dominio_actual(self) -> str:
        if self.modo_stub:
            return self.dataset.get("dominio", "(sin dataset)")
        return self.store.data.get("dominio", "(?)")

    def _vocab(self) -> Dict[str, Any]:
        if self.modo_stub:
            return self.dataset.get("vocabulario", {})
        return self.store.data.get("vocabulario", {})

    def _resumen_estado(self) -> Dict[str, Any]:
        """
        Regresa un resumen compacto para mostrar en el menú, estilo 'visualmente informativo'.
        """
        if self.modo_stub:
            reglas = self.dataset.get("reglas_criticas", [])
            casos = self.dataset.get("casos_prueba", [])
            capt = self.dataset.get("reglas_capturadas", [])
            return {
                "reglas_total": len(reglas) if isinstance(reglas, list) else 0,
                "casos_total": len(casos) if isinstance(casos, list) else 0,
                "capturadas": len(capt) if isinstance(capt, list) else 0,
                "cobertura_pct": None,
                "ontologia_ok": None,
            }

        reglas_ids = set(self.store.reglas_criticas_ids)
        capt_ids = set(self.store.reglas_capturadas_ids)
        capt_crit = capt_ids.intersection(reglas_ids)
        cobertura_pct = (len(capt_crit) / len(reglas_ids) * 100.0) if reglas_ids else 0.0

        # Ontología rápida (sin imprimir todo)
        inconsistencias = []
        try:
            inconsistencias = self.ont.validar_coherencia()
        except Exception:
            inconsistencias = ["(error al validar ontología)"]

        return {
            "reglas_total": len(reglas_ids),
            "casos_total": len(self.store.casos_prueba),
            "capturadas": len(capt_ids),
            "cobertura_pct": round(cobertura_pct, 1),
            "ontologia_ok": (len(inconsistencias) == 0),
        }

    # -------------------------
    # Run
    # -------------------------
    def run(self) -> None:
        # Mensaje inicial tipo “guía” como en ejemplos
        dom = self._dominio_actual()
        modo = "STUB (solo interfaz)" if self.modo_stub else "REAL (módulos activos)"

        self._banner("SIMULADOR EDUCATIVO — INGENIERÍA DEL CONOCIMIENTO")
        print("Objetivo: simular el proceso completo de construir un sistema experto")
        print("para diagnóstico de averías en coches eléctricos (baterías de estado sólido).")
        print(f"Dominio activo: {dom}")
        print(f"Modo: {modo}")

        # Si estamos en REAL, validar dataset al inicio
        if not self.modo_stub:
            self._validar_dataset_al_inicio()

        while True:
            self._menu_principal()
            op = input("Elige opción: ").strip()

            if op == "1":
                self._op_adquisicion()
            elif op == "2":
                self._op_ontologia()
            elif op == "3":
                self._op_diagnostico()
            elif op == "4":
                self._op_reporte()
            elif op == "0":
                print("\nSaliendo...")
                return
            else:
                print("Opción inválida.")
                self._pause()

    def _validar_dataset_al_inicio(self) -> None:
        self._banner("VALIDACIÓN INICIAL DEL DATASET (estructura mínima)")
        if not hasattr(self.store, "validate_basic_schema"):
            print("⚠️  DatasetStore no tiene validate_basic_schema(). (Tu repo puede estar desactualizado)")
            print("    Recomendación: aseguren el cambio de dataset_store.py primero.")
            self._pause()
            return

        errores = self.store.validate_basic_schema()
        if not errores:
            print("✅ Dataset OK: estructura mínima válida.")
        else:
            print(f"❌ Se detectaron {len(errores)} problemas en el JSON:")
            for e in errores:
                print(f" - {e}")
            print("\nPuedes continuar, pero es recomendable corregir el JSON para evitar fallas en módulos.")
        self._pause()

    def _menu_principal(self) -> None:
        dom = self._dominio_actual()
        modo = "STUB" if self.modo_stub else "REAL"
        estado = self._resumen_estado()

        self._banner(f"MENÚ PRINCIPAL — Dominio: {dom} — Modo: {modo}")

        # Aviso si está en stub por falta de imports
        if self.modo_stub and not MODULOS_OK:
            print("⚠️  Modo STUB activado porque no se pudieron importar módulos reales.")
            if IMPORT_ERROR:
                print(f"    Detalle: {IMPORT_ERROR}")
            print()

        # Resumen estilo "dashboard"
        print("ESTADO RÁPIDO:")
        print(f"- Reglas críticas totales: {estado['reglas_total']}")
        print(f"- Reglas capturadas:       {estado['capturadas']}")
        if estado["cobertura_pct"] is not None:
            print(f"- Cobertura estimada:      {estado['cobertura_pct']}%")
        if estado["ontologia_ok"] is not None:
            print(f"- Ontología coherente:     {'SI' if estado['ontologia_ok'] else 'NO'}")
        print(f"- Casos de prueba:         {estado['casos_total']}")

        print("\nSELECCIONA MÓDULO:")
        print("1) MÓDULO 1 — Adquisición de conocimiento (entrevistas por escenarios)")
        print("2) MÓDULO 2 — Ontología (visualizar + validar coherencia)")
        print("3) MÓDULO 3 — Diagnóstico (inferencia + explicación por perfil)")
        print("4) MÓDULO 4 — Reporte de cobertura / calidad (rúbrica)")
        print("0) Salir")

    # -------------------------
    # Ejecución segura de métodos (compatibilidad)
    # -------------------------
    def _call_any(self, obj: Any, methods: List[str]) -> bool:
        """
        Intenta llamar el primer método existente de la lista.
        Regresa True si pudo llamarlo.
        """
        for m in methods:
            fn = getattr(obj, m, None)
            if callable(fn):
                fn()
                return True
        return False

    # -------------------------
    # Opciones
    # -------------------------
    def _op_adquisicion(self) -> None:
        if not self.modo_stub:
            self._banner("SIMULACIÓN: Adquisición de conocimiento mediante escenarios reales")
            ok = self._call_any(self.adq, ["iniciar_entrevistas", "ejecutar"])
            if not ok:
                print("❌ No se encontró método de ejecución en AdquisicionConocimiento.")
                self._pause()
                return

            # “TU TURNO” estilo profesor (para que se vea alineado a guía)
            self._print_tu_turno([
                "Diseña un escenario adicional para capturar una avería nueva (baterías de estado sólido).",
                "Escribe la pregunta que harías al experto para revelar conocimiento tácito.",
                "Agrega la regla extraída y valida con un caso de prueba.",
                "Reflexiona: ¿qué caso límite podría no estar cubierto por las reglas actuales?"
            ])
            self._pause()
            return

        # STUB
        self._banner("MÓDULO 1 — ADQUISICIÓN (STUB)")
        esc = self.dataset.get("escenarios_adquisicion", [])
        print("✅ Interfaz OK. Aún no ejecuta entrevistas reales.")
        print(f"Escenarios cargados en JSON: {len(esc) if isinstance(esc, list) else 0}")
        self._pause()

    def _op_ontologia(self) -> None:
        if not self.modo_stub:
            # Para alinearse al ejemplo del profe: menú simple y validación
            self._banner("MÓDULO 2 — Ontología (visualización + coherencia)")
            ok = self._call_any(self.ont, ["menu_ontologia", "ejecutar"])
            if not ok:
                print("❌ No se encontró método de ejecución en OntologiaDominio.")
                self._pause()
                return

            self._print_tu_turno([
                "Agrega una nueva avería al árbol (jerarquía) dentro de 'electrica' o 'electronica'.",
                "Define relaciones semánticas: 'sintoma', 'causa' y 'requiere_reparacion'.",
                "Ejecuta la validación y confirma que haya 0 inconsistencias.",
                "Demuestra una inferencia simple que antes no era posible sin la ontología."
            ])
            self._pause()
            return

        # STUB
        while True:
            self._banner("MÓDULO 2 — ONTOLOGÍA (STUB)")
            print("1) Ver árbol jerárquico (ASCII) [lectura del JSON]")
            print("2) Validar ontología [stub]")
            print("0) Regresar")

            op = input("Elige opción: ").strip()
            if op == "1":
                self._mostrar_arbol_ascii_stub()
            elif op == "2":
                print("\n(Stub) Aquí validaremos: ciclos/contradicciones/relaciones permitidas.")
                self._pause()
            elif op == "0":
                return
            else:
                print("Opción inválida.")
                self._pause()

    def _mostrar_arbol_ascii_stub(self) -> None:
        self._banner("ONTOLOGÍA — Árbol ASCII (desde JSON)")
        ont = (self.dataset.get("ontologia_inicial") or {}).get("jerarquias")
        if not ont:
            print("No hay ontologia_inicial.jerarquias en el dataset.")
            self._pause()
            return

        for root, subtree in ont.items():
            print(root)
            self._print_tree(subtree, prefix="  ")

        self._pause()

    def _print_tree(self, node: Any, prefix: str) -> None:
        if not isinstance(node, dict):
            return
        items = list(node.items())
        for idx, (k, v) in enumerate(items):
            connector = "└─ " if idx == len(items) - 1 else "├─ "
            print(prefix + connector + str(k))
            next_prefix = prefix + ("   " if idx == len(items) - 1 else "│  ")
            self._print_tree(v, next_prefix)

    def _op_diagnostico(self) -> None:
        if not self.modo_stub:
            self._banner("MÓDULO 3 — Diagnóstico (motor de inferencia + explicación adaptativa)")
            self._diagnostico_interactivo_real()
            self._pause()
            return

        # STUB
        self._banner("MÓDULO 3 — DIAGNÓSTICO (STUB)")
        vocab = self._vocab()
        sintomas_validos: Set[str] = set(vocab.get("sintomas", [])) if isinstance(vocab, dict) else set()

        print("✅ Interfaz OK. Aún no hay inferencia real.")
        print("Tip: escribe 'lista' para ver síntomas válidos.\n")

        raw = input("> Síntomas (coma): ").strip()
        if raw.lower() == "lista":
            print("\nSíntomas válidos:")
            for s in sorted(sintomas_validos):
                print(" -", s)
            self._pause()
            return

        sintomas = [s.strip() for s in raw.split(",") if s.strip()]
        perfil = input("Perfil (cliente/aprendiz/experto): ").strip().lower() or "cliente"

        desconocidos = [s for s in sintomas if s not in sintomas_validos]
        if desconocidos:
            print("\n⚠️  Síntomas no reconocidos:", ", ".join(desconocidos))

        print("\n(Stub) Síntomas recibidos:", sintomas)
        print("(Stub) Perfil:", perfil)
        print("(Stub) Diagnóstico:", "diagnostico_no_posible")
        self._pause()

    def _diagnostico_interactivo_real(self) -> None:
        vocab = self.store.data.get("vocabulario", {})
        sintomas_validos: Set[str] = set(vocab.get("sintomas", [])) if isinstance(vocab, dict) else set()

        print("Ingresa síntomas separados por coma.")
        print("Tip: escribe 'lista' para ver síntomas válidos.")
        raw = input("> ").strip()

        if raw.lower() == "lista":
            print("\nSíntomas válidos:")
            for s in sorted(sintomas_validos):
                print(" -", s)
            return

        sintomas: List[str] = [s.strip() for s in raw.split(",") if s.strip()]
        if not sintomas:
            print("No ingresaste síntomas.")
            return

        desconocidos = [s for s in sintomas if s not in sintomas_validos]
        if desconocidos:
            print("⚠️  Síntomas no reconocidos:", ", ".join(desconocidos))

        perfil = input("Perfil (cliente/aprendiz/experto): ").strip().lower() or "cliente"

        diag, explic, rid, certeza = self.motor.diagnosticar(sintomas, perfil)

        # Presentación estilo ejemplo del profe
        print("\n" + self.DIV)
        if perfil == "cliente":
            print(" EXPLICACIÓN PARA CLIENTE (lenguaje sencillo):")
        elif perfil == "aprendiz":
            print(" EXPLICACIÓN PARA APRENDIZ (detalle técnico):")
        else:
            print(" EXPLICACIÓN PARA EXPERTO (máximo detalle):")
        print(self.DIV)
        print(explic)
        print(self.DIV)

        if diag == "diagnostico_no_posible":
            self._print_tu_turno([
                "Regresa a Adquisición y captura más reglas (o crea un escenario nuevo).",
                "Agrega un caso de prueba que represente este caso límite.",
                "Reflexiona qué información faltó para poder decidir."
            ])

    def _op_reporte(self) -> None:
        if not self.modo_stub:
            self._banner("MÓDULO 4 — Reporte de cobertura / calidad (rúbrica)")
            ok = self._call_any(self.rep, ["generar", "ejecutar"])
            if not ok:
                print("❌ No se encontró método de ejecución en ReporteCobertura.")
                self._pause()
                return

            self._print_tu_turno([
                "Identifica qué reglas críticas faltan por capturar (si cobertura < 70%).",
                "Si precisión < 80%, revisa qué casos fallan y qué regla falta/refinar.",
                "Si ontología NO es coherente, corrige relaciones o jerarquías y revalida.",
                "Redacta 3–5 líneas de reflexión: brecha teoría–práctica y lecciones aprendidas."
            ])
            self._pause()
            return

        # STUB
        self._banner("MÓDULO 4 — REPORTE (STUB)")
        reglas = self.dataset.get("reglas_criticas", [])
        casos = self.dataset.get("casos_prueba", [])
        capt = self.dataset.get("reglas_capturadas", [])

        print("✅ Interfaz OK. Aún no calcula métricas reales.")
        print(f"Reglas críticas en JSON: {len(reglas) if isinstance(reglas, list) else 0}")
        print(f"Casos de prueba en JSON: {len(casos) if isinstance(casos, list) else 0}")
        print(f"Reglas capturadas (si ya las marcaste): {len(capt) if isinstance(capt, list) else 0}")
        self._pause()