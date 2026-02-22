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
    CLI con modo STUB para probar interfaz.

    - modo_stub=True: NO usa módulos reales. Solo muestra menús y usa el JSON para listas.
    - modo_stub=False: usa módulos reales (si están disponibles).
    """

    def __init__(self, dataset_path: str, modo_stub: bool = True):
        self.dataset_path = dataset_path
        self.modo_stub = modo_stub or (not MODULOS_OK)

        # Dataset para modo stub
        self.dataset: Dict[str, Any] = self._cargar_dataset_simple(dataset_path)

        # Componentes reales (solo si NO stub)
        self.store = None
        self.adq = None
        self.ont = None
        self.motor = None
        self.rep = None

        if not self.modo_stub:
            self.store = DatasetStore(dataset_path)
            self.store.load()

            self.adq = AdquisicionConocimiento(self.store)
            self.ont = OntologiaDominio(self.store)
            self.motor = MotorInferencia(self.store)
            self.rep = ReporteCobertura(self.store, self.motor, self.ont)

    # -------------------------
    # Utilidades UI
    # -------------------------
    def _header(self, title: str) -> None:
        print("\n" + "=" * 78)
        print(f" {title}")
        print("=" * 78)

    def _pause(self) -> None:
        input("\nPresiona Enter para continuar...")

    # -------------------------
    # Dataset (modo stub)
    # -------------------------
    def _cargar_dataset_simple(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _dominio_actual(self) -> str:
        if self.modo_stub:
            return self.dataset.get("dominio", "(sin dataset)")
        return self.store.data.get("dominio", "?")

    def _vocab(self) -> Dict[str, Any]:
        if self.modo_stub:
            return self.dataset.get("vocabulario", {})
        return self.store.data.get("vocabulario", {})

    # -------------------------
    # Run
    # -------------------------
    def run(self) -> None:
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
                print("Saliendo...")
                return
            else:
                print("Opción inválida.")
                self._pause()

    def _menu_principal(self) -> None:
        dom = self._dominio_actual()
        modo = "STUB (solo interfaz)" if self.modo_stub else "REAL (módulos activos)"

        self._header(f"SIMULADOR IC — Dominio: {dom} — Modo: {modo}")

        # Aviso si está en stub por falta de imports
        if self.modo_stub and not MODULOS_OK:
            print("⚠️  Modo STUB activado porque no se pudieron importar módulos reales.")
            if IMPORT_ERROR:
                print(f"    Detalle: {IMPORT_ERROR}")
            print()

        print("1) Adquisición de conocimiento (entrevistas por escenarios)")
        print("2) Ontología (ver/validar)")
        print("3) Diagnóstico + explicación (por perfil)")
        print("4) Reporte de cobertura")
        print("0) Salir")

    # -------------------------
    # Opciones (stub o real)
    # -------------------------
    def _op_adquisicion(self) -> None:
        if not self.modo_stub:
            self.adq.iniciar_entrevistas()
            return

        self._header("MÓDULO 1 — ADQUISICIÓN (STUB)")
        esc = self.dataset.get("escenarios_adquisicion", [])
        print("✅ Interfaz OK. Aún no ejecuta entrevistas reales.")
        print(f"Escenarios cargados en JSON: {len(esc)}")
        print("Tip: cuando implementemos esto, aquí se presentarán escenarios y se capturarán reglas.")
        self._pause()

    def _op_ontologia(self) -> None:
        if not self.modo_stub:
            self.ont.menu_ontologia()
            return

        while True:
            self._header("MÓDULO 2 — ONTOLOGÍA (STUB)")
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
        self._header("ONTOLOGÍA — Árbol ASCII (desde JSON)")
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
            self._diagnostico_interactivo_real()
            return

        self._header("MÓDULO 3 — DIAGNÓSTICO (STUB)")
        vocab = self._vocab()
        sintomas_validos: Set[str] = set(vocab.get("sintomas", []))

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
        sintomas_validos: Set[str] = set(vocab.get("sintomas", []))

        print("\nIngresa síntomas separados por coma.")
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

        print("\n" + "-" * 78)
        print(explic)
        print("-" * 78)

    def _op_reporte(self) -> None:
        if not self.modo_stub:
            self.rep.generar()
            return

        self._header("MÓDULO 4 — REPORTE (STUB)")
        reglas = self.dataset.get("reglas_criticas", [])
        casos = self.dataset.get("casos_prueba", [])
        capt = self.dataset.get("reglas_capturadas", [])

        print("✅ Interfaz OK. Aún no calcula métricas reales.")
        print(f"Reglas críticas en JSON: {len(reglas)}")
        print(f"Casos de prueba en JSON: {len(casos)}")
        print(f"Reglas capturadas (si ya las marcaste): {len(capt)}")
        self._pause()
