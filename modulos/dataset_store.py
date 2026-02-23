import json
import os
from json import JSONDecodeError
from typing import Any, Dict, List, Optional


class DatasetStore:
    """
    Carga y guarda el dataset JSON del simulador.

    Responsabilidades:
    - Cargar el dataset (JSON) desde disco.
    - Normalizar campos opcionales que el resto de módulos esperan.
    - Validar estructura mínima (schema básico) para detectar errores temprano.
    - Guardar el dataset de vuelta en disco (con rutas robustas).

    Nota clave:
    - 'reglas_criticas_ids' se sincroniza automáticamente a partir de 'reglas_criticas'
      para evitar inconsistencias si alguien agrega/modifica reglas y olvida actualizar la lista.
    """

    # Llaves mínimas esperadas (muy básicas; no bloquean la creatividad del dataset)
    _REQUIRED_TOP_LEVEL = [
        "meta",
        "dominio",
        "vocabulario",
        "reglas_criticas",
        "casos_prueba",
        "escenarios_adquisicion",
        "ontologia_inicial",
        "reporte_config",
        "reglas_capturadas",
    ]

    def __init__(self, dataset_file: str):
        # Guardar ruta absoluta para evitar problemas si ejecutan desde otra carpeta
        self.dataset_file = os.path.abspath(dataset_file)
        self.data: Dict[str, Any] = {}
        self._load()

    # -------------------------
    # Carga / Normalización
    # -------------------------
    def _load(self) -> None:
        if not os.path.exists(self.dataset_file):
            raise FileNotFoundError(f"No se encontró el dataset: {self.dataset_file}")

        try:
            with open(self.dataset_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except JSONDecodeError as e:
            raise ValueError(
                f"El archivo JSON está mal formado: {self.dataset_file}\n"
                f"Detalle: {e}"
            ) from e

        if not isinstance(self.data, dict):
            raise ValueError("El dataset JSON debe ser un objeto (dict) en el nivel raíz.")

        # Normalizar campos opcionales para que el resto de módulos no truenen
        self.data.setdefault("meta", {})
        self.data.setdefault("dominio", "DESCONOCIDO")
        self.data.setdefault("vocabulario", {})

        self.data.setdefault("reglas_capturadas", [])
        self.data.setdefault("reglas_criticas", [])
        self.data.setdefault("reglas_criticas_ids", [])  # se sincroniza abajo
        self.data.setdefault("casos_prueba", [])
        self.data.setdefault("escenarios_adquisicion", [])
        self.data.setdefault("ontologia_inicial", {})
        self.data.setdefault("reporte_config", {})

        # Sincronizar IDs de reglas críticas (evita que cobertura quede mal)
        self._sync_reglas_criticas_ids()

    def _sync_reglas_criticas_ids(self) -> None:
        reglas = self.data.get("reglas_criticas", [])
        if not isinstance(reglas, list):
            # No reventamos aquí; se reporta en validate_basic_schema()
            return

        ids_from_rules: List[str] = []
        for r in reglas:
            if isinstance(r, dict) and isinstance(r.get("id"), str) and r["id"].strip():
                ids_from_rules.append(r["id"].strip())

        # Quitar duplicados preservando orden
        seen = set()
        ids_from_rules_unique = []
        for rid in ids_from_rules:
            if rid not in seen:
                ids_from_rules_unique.append(rid)
                seen.add(rid)

        # Si la lista del JSON está vacía o desactualizada, la corregimos
        current = self.data.get("reglas_criticas_ids", [])
        if not isinstance(current, list) or current != ids_from_rules_unique:
            self.data["reglas_criticas_ids"] = ids_from_rules_unique

    # -------------------------
    # Validación básica
    # -------------------------
    def validate_basic_schema(self) -> List[str]:
        """
        Valida que exista lo mínimo necesario y que los tipos sean razonables.
        Regresa una lista de errores (vacía si OK).
        """
        errors: List[str] = []

        # Llaves mínimas
        for k in self._REQUIRED_TOP_LEVEL:
            if k not in self.data:
                errors.append(f"Falta la llave requerida '{k}' en el JSON.")

        # Tipos esperados (básicos)
        if not isinstance(self.data.get("meta", {}), dict):
            errors.append("'meta' debe ser un objeto (dict).")

        if not isinstance(self.data.get("dominio", ""), str):
            errors.append("'dominio' debe ser string.")

        if not isinstance(self.data.get("vocabulario", {}), dict):
            errors.append("'vocabulario' debe ser objeto (dict).")

        if not isinstance(self.data.get("reglas_criticas", []), list):
            errors.append("'reglas_criticas' debe ser lista.")

        if not isinstance(self.data.get("reglas_criticas_ids", []), list):
            errors.append("'reglas_criticas_ids' debe ser lista.")

        if not isinstance(self.data.get("casos_prueba", []), list):
            errors.append("'casos_prueba' debe ser lista.")

        if not isinstance(self.data.get("escenarios_adquisicion", []), list):
            errors.append("'escenarios_adquisicion' debe ser lista.")

        if not isinstance(self.data.get("ontologia_inicial", {}), dict):
            errors.append("'ontologia_inicial' debe ser objeto (dict).")

        if not isinstance(self.data.get("reporte_config", {}), dict):
            errors.append("'reporte_config' debe ser objeto (dict).")

        if not isinstance(self.data.get("reglas_capturadas", []), list):
            errors.append("'reglas_capturadas' debe ser lista.")

        # Validación ligera de reglas/casos (sin ser estrictos)
        for idx, r in enumerate(self.data.get("reglas_criticas", [])):
            if not isinstance(r, dict):
                errors.append(f"reglas_criticas[{idx}] no es objeto dict.")
                continue
            if not r.get("id"):
                errors.append(f"reglas_criticas[{idx}] no tiene campo 'id'.")
            if not isinstance(r.get("condiciones", []), list):
                errors.append(f"reglas_criticas[{idx}].condiciones debe ser lista.")

        for idx, c in enumerate(self.data.get("casos_prueba", [])):
            if not isinstance(c, dict):
                errors.append(f"casos_prueba[{idx}] no es objeto dict.")
                continue
            if not c.get("id"):
                errors.append(f"casos_prueba[{idx}] no tiene campo 'id'.")
            if not isinstance(c.get("sintomas", []), list):
                errors.append(f"casos_prueba[{idx}].sintomas debe ser lista.")
            if not c.get("diagnostico_esperado"):
                errors.append(f"casos_prueba[{idx}] no tiene 'diagnostico_esperado'.")

        return errors

    # -------------------------
    # Guardado
    # -------------------------
    def save(self, out_path: Optional[str] = None) -> str:
        """
        Guarda el dataset y regresa la ruta donde se guardó.

        - Si out_path no se da, guarda en la ruta original.
        - Si no hay permisos para escribir, intenta rutas alternas.
        """
        # Sincronizar IDs antes de guardar (por si agregaron reglas)
        self._sync_reglas_criticas_ids()

        target = os.path.abspath(out_path) if out_path else self.dataset_file
        try:
            self._ensure_parent_dir(target)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return target
        except PermissionError:
            base, ext = os.path.splitext(self.dataset_file)
            filename_out = os.path.basename(f"{base}_out{ext or '.json'}")

            candidates = [
                os.path.join(os.path.dirname(self.dataset_file), filename_out),
                os.path.join(os.getcwd(), filename_out),
                os.path.join("/tmp", filename_out),
            ]

            last_err: Optional[Exception] = None
            for alt in candidates:
                try:
                    self._ensure_parent_dir(alt)
                    with open(alt, "w", encoding="utf-8") as f:
                        json.dump(self.data, f, ensure_ascii=False, indent=2)
                    print(f"⚠️  No se pudo escribir en '{target}'. Se guardó una copia en: {alt}")
                    return alt
                except Exception as e:
                    last_err = e

            print(f"❌ No se pudo guardar el dataset por permisos. Último error: {last_err}")
            return target

    @staticmethod
    def _ensure_parent_dir(path: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    # -------------------------
    # Accessors cómodos
    # -------------------------
    @property
    def meta(self) -> Dict[str, Any]:
        return dict(self.data.get("meta", {}))

    @property
    def dominio(self) -> str:
        return self.data.get("dominio", "DESCONOCIDO")

    @property
    def vocabulario(self) -> Dict[str, Any]:
        return dict(self.data.get("vocabulario", {}))

    @property
    def reglas_criticas(self) -> List[Dict[str, Any]]:
        return list(self.data.get("reglas_criticas", []))

    @property
    def reglas_criticas_ids(self) -> List[str]:
        # Siempre regresamos la lista sincronizada
        self._sync_reglas_criticas_ids()
        return list(self.data.get("reglas_criticas_ids", []))

    @property
    def casos_prueba(self) -> List[Dict[str, Any]]:
        return list(self.data.get("casos_prueba", []))

    @property
    def escenarios(self) -> List[Dict[str, Any]]:
        return list(self.data.get("escenarios_adquisicion", []))

    @property
    def ontologia(self) -> Dict[str, Any]:
        return dict(self.data.get("ontologia_inicial", {}))

    @property
    def validacion_config(self) -> Dict[str, Any]:
        ont = self.data.get("ontologia_inicial", {})
        if isinstance(ont, dict):
            return dict(ont.get("validacion_config", {}))
        return {}

    @property
    def reporte_config(self) -> Dict[str, Any]:
        return dict(self.data.get("reporte_config", {}))

    @property
    def reglas_capturadas_ids(self) -> List[str]:
        return list(self.data.get("reglas_capturadas", []))

    def marcar_regla_capturada(self, regla_id: str) -> None:
        regla_id = (regla_id or "").strip()
        if not regla_id:
            return
        reglas = self.data.setdefault("reglas_capturadas", [])
        if regla_id not in reglas:
            reglas.append(regla_id)

    def get_regla_por_id(self, regla_id: str) -> Optional[Dict[str, Any]]:
        for r in self.reglas_criticas:
            if r.get("id") == regla_id:
                return r
        return None