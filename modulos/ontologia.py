from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from modulos.dataset_store import DatasetStore


class OntologiaDominio:
    """
    MÓDULO 2 — Ontología del dominio (visualización + validación)

    Dataset esperado (en ontologia_inicial):
    - jerarquias: dict (árboles por raíz)
    - relaciones: dict (nombre_relacion -> {from:[], to:[], descripcion})
    - validacion_config: { max_depth?, forbid_cycles?, allowed_relation_types? } (opcional)

    Funciones:
    - menu_ontologia(): UI estilo profesor.
    - mostrar_arbol(): imprime jerarquía en ASCII.
    - mostrar_relaciones(): imprime relaciones definidas.
    - validar_coherencia(): regresa lista de inconsistencias.
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, store: DatasetStore):
        self.store = store

    # Compatibilidad con otros módulos
    def ejecutar(self) -> None:
        self.menu_ontologia()

    def menu_ontologia(self) -> None:
        while True:
            self._banner("MÓDULO 2 — ONTOLOGÍA (visualizar + validar coherencia)")

            print("1) Ver jerarquías (árbol ASCII)")
            print("2) Ver relaciones semánticas")
            print("3) Validar coherencia (ciclos, tipos, relaciones)")
            print("0) Regresar")

            op = input("Elige opción: ").strip()

            if op == "1":
                self.mostrar_arbol()
                self._pause()
            elif op == "2":
                self.mostrar_relaciones()
                self._pause()
            elif op == "3":
                inconsistencias = self.validar_coherencia()
                self._mostrar_resultado_validacion(inconsistencias)
                self._pause()
            elif op == "0":
                return
            else:
                print("Opción inválida.")
                self._pause()

    # ---------------------------------------------------------------------
    # Visualización
    # ---------------------------------------------------------------------
    def mostrar_arbol(self) -> None:
        self._banner("ONTOLOGÍA — Jerarquías (Árbol ASCII)")

        ont = self.store.ontologia or {}
        jer = ont.get("jerarquias", {})

        if not isinstance(jer, dict) or not jer:
            print("No hay jerarquías definidas en ontologia_inicial.jerarquias.")
            return

        for root_name, subtree in jer.items():
            print(root_name)
            self._print_tree(subtree, prefix="  ")

    def _print_tree(self, node: Any, prefix: str) -> None:
        if not isinstance(node, dict):
            return

        items = list(node.items())
        for idx, (k, v) in enumerate(items):
            connector = "└─ " if idx == len(items) - 1 else "├─ "
            print(prefix + connector + str(k))
            next_prefix = prefix + ("   " if idx == len(items) - 1 else "│  ")
            self._print_tree(v, next_prefix)

    def mostrar_relaciones(self) -> None:
        self._banner("ONTOLOGÍA — Relaciones semánticas")

        ont = self.store.ontologia or {}
        rel = ont.get("relaciones", {})

        if not isinstance(rel, dict) or not rel:
            print("No hay relaciones definidas en ontologia_inicial.relaciones.")
            return

        for rname, spec in rel.items():
            print(f"\n{self.DIV}")
            print(f"Relación: {rname}")
            print(self.DIV)

            if isinstance(spec, dict):
                from_types = spec.get("from", [])
                to_types = spec.get("to", [])
                desc = spec.get("descripcion", "")

                print(f"from: {from_types if isinstance(from_types, list) else from_types}")
                print(f"to:   {to_types if isinstance(to_types, list) else to_types}")
                if desc:
                    print(f"Descripción: {desc}")
            else:
                print("(Formato no válido; se esperaba dict)")

    # ---------------------------------------------------------------------
    # Validación
    # ---------------------------------------------------------------------
    def validar_coherencia(self) -> List[str]:
        """
        Regresa lista de inconsistencias.
        """
        ont = self.store.ontologia or {}
        cfg = self._get_cfg(ont)

        jer = ont.get("jerarquias", {})
        rel = ont.get("relaciones", {})

        inconsistencias: List[str] = []

        # 1) Validar tipos básicos
        if not isinstance(jer, dict):
            inconsistencias.append("ontologia_inicial.jerarquias debe ser un objeto (dict).")
            return inconsistencias

        if rel and not isinstance(rel, dict):
            inconsistencias.append("ontologia_inicial.relaciones debe ser un objeto (dict).")

        # 2) Validar jerarquías: ciclos y duplicados por rama
        forbid_cycles = bool(cfg.get("forbid_cycles", True))
        max_depth = cfg.get("max_depth", None)

        # Recolectar todos los nodos (para validar relaciones después)
        all_nodes: Set[str] = set()

        def dfs(node_name: str, node: Any, path: List[str], depth: int) -> None:
            nonlocal inconsistencias, all_nodes

            all_nodes.add(node_name)

            # profundidad
            if isinstance(max_depth, int) and depth > max_depth:
                inconsistencias.append(f"Jerarquía excede max_depth={max_depth} en nodo '{node_name}' (ruta: {' > '.join(path)})")

            # ciclos
            if forbid_cycles and node_name in path[:-1]:
                inconsistencias.append(f"Ciclo detectado en jerarquía: '{node_name}' (ruta: {' > '.join(path)})")
                return

            if not isinstance(node, dict):
                return

            # duplicados directos
            seen_children = set()
            for child_name, child_node in node.items():
                cname = str(child_name)
                if cname in seen_children:
                    inconsistencias.append(f"Duplicado: '{cname}' aparece más de una vez como hijo de '{node_name}'.")
                seen_children.add(cname)

                dfs(cname, child_node, path + [cname], depth + 1)

        for root_name, subtree in jer.items():
            r = str(root_name)
            dfs(r, subtree, [r], 1)

        # 3) Validar relaciones semánticas (formato)
        if isinstance(rel, dict) and rel:
            allowed_rel_types = cfg.get("allowed_relation_types", None)  # opcional

            for rname, spec in rel.items():
                if not isinstance(spec, dict):
                    inconsistencias.append(f"Relación '{rname}' debe ser un dict.")
                    continue

                from_types = spec.get("from", [])
                to_types = spec.get("to", [])

                if not isinstance(from_types, list) or not all(isinstance(x, str) for x in from_types):
                    inconsistencias.append(f"Relación '{rname}': campo 'from' debe ser lista de strings.")
                if not isinstance(to_types, list) or not all(isinstance(x, str) for x in to_types):
                    inconsistencias.append(f"Relación '{rname}': campo 'to' debe ser lista de strings.")

                # Si el profe define tipos permitidos, validarlos
                if allowed_rel_types and isinstance(allowed_rel_types, list):
                    # aquí validar rname en lista, si aplica
                    if rname not in allowed_rel_types:
                        inconsistencias.append(f"Relación '{rname}' no está en allowed_relation_types (config).")

        # 4) Validar vocabulario vs ontología (si existe vocabulario)
        vocab = self.store.data.get("vocabulario", {}) or {}
        if isinstance(vocab, dict):
            # por ejemplo: componentes, sintomas, reparaciones
            # Si un elemento del vocabulario no aparece en ontología, lo marcamos como aviso leve
            for key in ("componentes", "sintomas", "reparaciones"):
                vals = vocab.get(key, [])
                if isinstance(vals, list):
                    for v in vals:
                        sv = str(v)
                        if all_nodes and (sv not in all_nodes):
                            # Aviso (no necesariamente error), pero lo reportamos como "advertencia"
                            inconsistencias.append(f"Advertencia: '{sv}' (vocabulario.{key}) no aparece en jerarquías de ontología.")

        return inconsistencias

    def _get_cfg(self, ont: Dict[str, Any]) -> Dict[str, Any]:
        cfg = ont.get("validacion_config", {})
        if isinstance(cfg, dict):
            return cfg
        return {}

    def _mostrar_resultado_validacion(self, inconsistencias: List[str]) -> None:
        self._banner("RESULTADO DE VALIDACIÓN DE ONTOLOGÍA")
        if not inconsistencias:
            print("✅ Ontología coherente: 0 inconsistencias.")
            return

        # Separar advertencias de errores
        errores = [x for x in inconsistencias if not x.lower().startswith("advertencia")]
        warns = [x for x in inconsistencias if x.lower().startswith("advertencia")]

        if errores:
            print(f"❌ Errores encontrados: {len(errores)}")
            for e in errores[:15]:
                print(" -", e)
            if len(errores) > 15:
                print(f" ... y {len(errores) - 15} más")
        else:
            print("✅ No hay errores estructurales en ontología.")

        if warns:
            print(f"\n⚠️ Advertencias: {len(warns)}")
            for w in warns[:15]:
                print(" -", w)
            if len(warns) > 15:
                print(f" ... y {len(warns) - 15} más")

    # ---------------------------------------------------------------------
    # UI helpers
    # ---------------------------------------------------------------------
    def _banner(self, titulo: str) -> None:
        print("\n" + self.LINE)
        print(f" {titulo}")
        print(self.LINE)

    def _pause(self) -> None:
        input("\nPresiona Enter para continuar...")