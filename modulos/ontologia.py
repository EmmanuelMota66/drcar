from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from modulos.dataset_store import DatasetStore


class OntologiaDominio:
    """
    MÓDULO 2 — Ontología del dominio (visualización + validación)

    Soporta el formato de tu dataset:
    - ontologia_inicial.jerarquias: dict (árbol)
    - ontologia_inicial.relaciones: lista de triples:
        { "origen": "...", "relacion": "sintoma|causa|requiere_reparacion", "destino": "..." }

    También soporta validacion_config del dataset:
    - no_permitir_ciclos_jerarquia: bool
    - relaciones_permitidas: [ ... ]
    - requerir_0_inconsistencias_para_aprobacion: bool
    """

    LINE = "=" * 70
    DIV = "-" * 70

    def __init__(self, store: DatasetStore):
        self.store = store

    # Compatibilidad
    def ejecutar(self) -> None:
        self.menu_ontologia()

    # -------------------------
    # Menú (estilo profe)
    # -------------------------
    def menu_ontologia(self) -> None:
        while True:
            self._banner("MÓDULO 2 — ONTOLOGÍA (visualizar + validar coherencia)")
            print("1) Ver jerarquías (árbol ASCII)")
            print("2) Ver relaciones semánticas (triplas)")
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
                errores, advertencias = self.validar_coherencia_detallada()
                self._mostrar_resultado_validacion(errores, advertencias)
                self._pause()
            elif op == "0":
                return
            else:
                print("Opción inválida.")
                self._pause()

    # -------------------------
    # Visualización
    # -------------------------
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
        self._banner("ONTOLOGÍA — Relaciones semánticas (formato tripla)")
        ont = self.store.ontologia or {}
        rel = ont.get("relaciones", [])

        if not isinstance(rel, list) or not rel:
            print("No hay relaciones definidas en ontologia_inicial.relaciones (se esperaba lista).")
            return

        allowed = self._allowed_relations()
        print(f"Relaciones permitidas: {', '.join(allowed) if allowed else '(no definidas)'}\n")

        for i, t in enumerate(rel, 1):
            if not isinstance(t, dict):
                print(f"{i}) (inválida) — no es dict")
                continue
            origen = t.get("origen", "")
            relacion = t.get("relacion", "")
            destino = t.get("destino", "")
            print(f"{i}) {origen} --[{relacion}]--> {destino}")

    # -------------------------
    # Validación
    # -------------------------
    def validar_coherencia(self) -> List[str]:
        """
        Regresa SOLO ERRORES (para que el reporte no se caiga por advertencias).
        """
        errores, _ = self.validar_coherencia_detallada()
        return errores

    def validar_coherencia_detallada(self) -> Tuple[List[str], List[str]]:
        """
        Regresa (errores, advertencias).
        - Errores: rompen coherencia (ciclos, formatos inválidos, relaciones no permitidas, referencias desconocidas).
        - Advertencias: cosas “mejorables” que NO deberían tumbar la rúbrica.
        """
        ont = self.store.ontologia or {}
        cfg = self._get_cfg(ont)

        errores: List[str] = []
        advertencias: List[str] = []

        jer = ont.get("jerarquias", {})
        rel = ont.get("relaciones", [])

        # 1) Tipos básicos
        if not isinstance(jer, dict):
            errores.append("ontologia_inicial.jerarquias debe ser un objeto (dict).")
            return errores, advertencias

        if not isinstance(rel, list):
            errores.append("ontologia_inicial.relaciones debe ser una lista de triplas (origen/relacion/destino).")
            return errores, advertencias

        # 2) Ciclos en jerarquías
        no_ciclos = bool(cfg.get("no_permitir_ciclos_jerarquia", True))

        all_nodes: Set[str] = set()

        def dfs(node_name: str, node: Any, path: List[str]) -> None:
            all_nodes.add(node_name)

            if no_ciclos and node_name in path[:-1]:
                errores.append(f"Ciclo detectado en jerarquía: '{node_name}' (ruta: {' > '.join(path)})")
                return

            if not isinstance(node, dict):
                return

            seen_children = set()
            for child_name, child_node in node.items():
                cname = str(child_name)
                if cname in seen_children:
                    errores.append(f"Duplicado: '{cname}' aparece más de una vez como hijo de '{node_name}'.")
                seen_children.add(cname)
                dfs(cname, child_node, path + [cname])

        for root_name, subtree in jer.items():
            r = str(root_name)
            dfs(r, subtree, [r])

        # 3) Validar relaciones (triples)
        allowed_rel = self._allowed_relations()
        vocab = self.store.data.get("vocabulario", {}) or {}
        vocab_sint = set(vocab.get("sintomas", []) if isinstance(vocab.get("sintomas", []), list) else [])
        vocab_diag = set(vocab.get("diagnosticos", []) if isinstance(vocab.get("diagnosticos", []), list) else [])
        vocab_rep = set(vocab.get("reparaciones", []) if isinstance(vocab.get("reparaciones", []), list) else [])

        for i, t in enumerate(rel):
            if not isinstance(t, dict):
                errores.append(f"relaciones[{i}] no es dict.")
                continue

            origen = t.get("origen")
            relacion = t.get("relacion")
            destino = t.get("destino")

            if not isinstance(origen, str) or not origen.strip():
                errores.append(f"relaciones[{i}].origen inválido.")
                continue
            if not isinstance(relacion, str) or not relacion.strip():
                errores.append(f"relaciones[{i}].relacion inválida.")
                continue
            if not isinstance(destino, str) or not destino.strip():
                errores.append(f"relaciones[{i}].destino inválido.")
                continue

            origen = origen.strip()
            relacion = relacion.strip()
            destino = destino.strip()

            # Relación permitida
            if allowed_rel and relacion not in allowed_rel:
                errores.append(f"Relación no permitida: '{relacion}' en relaciones[{i}] (permitidas: {allowed_rel}).")

            # Validar origen/destino con vocabulario (más realista que exigir que existan como nodos de jerarquía)
            if origen not in vocab_diag and origen not in all_nodes:
                advertencias.append(f"Advertencia: origen '{origen}' no está en vocabulario.diagnosticos ni en jerarquías.")

            if relacion == "sintoma":
                if destino not in vocab_sint and destino not in all_nodes:
                    errores.append(f"Destino '{destino}' no reconocido como síntoma (relaciones[{i}]).")
            elif relacion == "requiere_reparacion":
                if destino not in vocab_rep and destino not in all_nodes:
                    errores.append(f"Destino '{destino}' no reconocido como reparación (relaciones[{i}]).")
            elif relacion == "causa":
                # Causa puede apuntar a diagnóstico/componente/otro nodo
                if destino not in vocab_diag and destino not in all_nodes:
                    advertencias.append(f"Advertencia: destino '{destino}' en relación 'causa' no está en diagnósticos ni en jerarquías.")
            else:
                # Si no estaba permitido arriba, ya habrá error; si no hay lista permitida, lo marcamos
                if not allowed_rel:
                    advertencias.append(f"Advertencia: relación '{relacion}' no validada (no hay lista de permitidas).")

        # 4) Config “cero inconsistencias”
        if cfg.get("requerir_0_inconsistencias_para_aprobacion", False) and errores:
            # no añade nada extra; solo deja explícito que esto es bloqueo
            pass

        return errores, advertencias

    def _allowed_relations(self) -> List[str]:
        """
        Toma relaciones permitidas desde:
        - ontologia_inicial.validacion_config.relaciones_permitidas (preferente)
        o fallback:
        - vocabulario.relaciones_permitidas
        """
        ont = self.store.ontologia or {}
        cfg = self._get_cfg(ont)

        rels = cfg.get("relaciones_permitidas")
        if isinstance(rels, list) and all(isinstance(x, str) for x in rels):
            return rels

        vocab = self.store.data.get("vocabulario", {}) or {}
        rels2 = vocab.get("relaciones_permitidas")
        if isinstance(rels2, list) and all(isinstance(x, str) for x in rels2):
            return rels2

        return []

    def _get_cfg(self, ont: Dict[str, Any]) -> Dict[str, Any]:
        cfg = ont.get("validacion_config", {})
        return cfg if isinstance(cfg, dict) else {}

    def _mostrar_resultado_validacion(self, errores: List[str], advertencias: List[str]) -> None:
        self._banner("RESULTADO DE VALIDACIÓN DE ONTOLOGÍA")

        if not errores:
            print("✅ Ontología coherente: 0 errores.")
        else:
            print(f"❌ Errores encontrados: {len(errores)}")
            for e in errores[:20]:
                print(" -", e)
            if len(errores) > 20:
                print(f" ... y {len(errores) - 20} más")

        if advertencias:
            print(f"\n⚠️ Advertencias: {len(advertencias)}")
            for w in advertencias[:15]:
                print(" -", w)
            if len(advertencias) > 15:
                print(f" ... y {len(advertencias) - 15} más")

    # -------------------------
    # UI helpers
    # -------------------------
    def _banner(self, titulo: str) -> None:
        print("\n" + self.LINE)
        print(f" {titulo}")
        print(self.LINE)

    def _pause(self) -> None:
        input("\nPresiona Enter para continuar...")