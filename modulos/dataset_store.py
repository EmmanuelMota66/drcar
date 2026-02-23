import json
import os
from typing import Any, Dict, List, Optional


class DatasetStore:
    """
    Carga y guarda el dataset JSON.
    También mantiene 'reglas_capturadas' (lista de ids) para persistir
    qué reglas fueron adquiridas en entrevistas.
    """

    def __init__(self, dataset_file: str):
        self.dataset_file = dataset_file
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.dataset_file):
            raise FileNotFoundError(f"No se encontró el dataset: {self.dataset_file}")

        with open(self.dataset_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Normalizar campos opcionales
        self.data.setdefault("reglas_capturadas", [])
        self.data.setdefault("reglas_criticas", [])
        self.data.setdefault("casos_prueba", [])
        self.data.setdefault("escenarios_adquisicion", [])
        self.data.setdefault("ontologia_inicial", {})
        self.data.setdefault("reporte_config", {})

    def save(self) -> None:
        with open(self.dataset_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # --------- Accessors cómodos ---------
    @property
    def dominio(self) -> str:
        return self.data.get("dominio", "DESCONOCIDO")

    @property
    def reglas_criticas(self) -> List[Dict[str, Any]]:
        return list(self.data.get("reglas_criticas", []))

    @property
    def reglas_criticas_ids(self) -> List[str]:
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
        return dict(ont.get("validacion_config", {}))

    @property
    def reporte_config(self) -> Dict[str, Any]:
        return dict(self.data.get("reporte_config", {}))

    @property
    def reglas_capturadas_ids(self) -> List[str]:
        return list(self.data.get("reglas_capturadas", []))

    def marcar_regla_capturada(self, regla_id: str) -> None:
        reglas = self.data.setdefault("reglas_capturadas", [])
        if regla_id not in reglas:
            reglas.append(regla_id)

    def get_regla_por_id(self, regla_id: str) -> Optional[Dict[str, Any]]:
        for r in self.reglas_criticas:
            if r.get("id") == regla_id:
                return r
        return None