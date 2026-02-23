from typing import Any, Dict, List, Tuple, Set
from modulos.dataset_store import DatasetStore


class OntologiaDominio:
    """
    Valida:
    - Relaciones permitidas (causa, sintoma, requiere_reparacion)
    - Ciclos en jerarquía (si está activado)
    También imprime el árbol ASCII de jerarquías.
    """

    def __init__(self, store: DatasetStore):
        self.store = store
        self.ont = store.ontologia
        self.inconsistencias: List[str] = []

    def _flatten_jerarquia(self, jer: Dict[str, Any], parent: str = "") -> List[Tuple[str, str]]:
        """
        Convierte jerarquías anidadas dict -> lista de aristas (parent -> child)
        """
        edges: List[Tuple[str, str]] = []
        for k, v in jer.items():
            if parent:
                edges.append((parent, k))
            if isinstance(v, dict) and v:
                edges.extend(self._flatten_jerarquia(v, k))
        return edges

    def _detectar_ciclos(self, edges: List[Tuple[str, str]]) -> bool:
        graph: Dict[str, List[str]] = {}
        for a, b in edges:
            graph.setdefault(a, []).append(b)
            graph.setdefault(b, [])

        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(n: str) -> bool:
            visited.add(n)
            stack.add(n)
            for nb in graph.get(n, []):
                if nb not in visited:
                    if dfs(nb):
                        return True
                elif nb in stack:
                    return True
            stack.remove(n)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def imprimir_arbol(self) -> None:
        jerarquias = (self.ont.get("jerarquias") or {})
        if not jerarquias:
            print("No hay jerarquías en ontología.")
            return

        def print_node(d: Dict[str, Any], indent: str = ""):
            for k, v in d.items():
                print(f"{indent}- {k}")
                if isinstance(v, dict) and v:
                    print_node(v, indent + "  ")

        print("\n" + "=" * 70)
        print(" ONTOLOGÍA: JERARQUÍAS (ÁRBOL)")
        print("=" * 70)
        print_node(jerarquias)

    def validar_coherencia(self) -> List[str]:
        self.inconsistencias = []

        jerarquias = (self.ont.get("jerarquias") or {})
        relaciones = (self.ont.get("relaciones") or [])
        config = self.store.validacion_config

        relaciones_permitidas = set(config.get("relaciones_permitidas", ["causa", "sintoma", "requiere_reparacion"]))
        no_ciclos = bool(config.get("no_permitir_ciclos_jerarquia", True))

        # Validar relaciones permitidas
        for r in relaciones:
            rel = r.get("relacion")
            if rel not in relaciones_permitidas:
                self.inconsistencias.append(f"Relación no permitida: '{rel}' en {r}")

            if not r.get("origen") or not r.get("destino"):
                self.inconsistencias.append(f"Relación incompleta (falta origen/destino): {r}")

        # Ciclos en jerarquía
        if no_ciclos and jerarquias:
            edges = self._flatten_jerarquia(jerarquias, "")
            if self._detectar_ciclos(edges):
                self.inconsistencias.append("Se detectó un ciclo en la jerarquía (no permitido).")

        return self.inconsistencias

    def ejecutar(self) -> None:
        self.imprimir_arbol()
        inconsistencias = self.validar_coherencia()

        print("\n" + "=" * 70)
        print(" VALIDACIÓN DE COHERENCIA")
        print("=" * 70)
        if not inconsistencias:
            print("✅ Ontología coherente: 0 inconsistencias.")
        else:
            print(f"❌ Inconsistencias encontradas: {len(inconsistencias)}")
            for inc in inconsistencias:
                print(f" - {inc}")