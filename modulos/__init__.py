"""
Paquete de módulos del Simulador de Ingeniería del Conocimiento.

Estructura (según el enunciado del proyecto):
- dataset_store.py  -> carga/guarda/valida el JSON (base de conocimiento)
- adquisicion.py    -> entrevistas por escenarios (captura de reglas)
- ontologia.py      -> jerarquías/relaciones + validación de coherencia
- motor_inferencia.py -> inferencia basada en reglas + explicación por perfil
- reporte.py        -> cobertura/precisión/estado contra rúbrica
- cli.py            -> menú principal (orquestador)

Nota:
Este archivo ayuda a que Python trate 'modulos' como paquete en cualquier entorno.
"""

__all__ = [
    "dataset_store",
    "adquisicion",
    "ontologia",
    "motor_inferencia",
    "reporte",
    "cli",
]

__version__ = "0.1.0"