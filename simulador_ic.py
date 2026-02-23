#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SIMULADOR — INGENIERÍA DEL CONOCIMIENTO
Diagnóstico de averías en coches eléctricos (baterías de estado sólido)

Entrypoint del proyecto (main).
- Resuelve rutas de forma robusta (para trabajo en GitHub y ejecución desde cualquier carpeta).
- Permite elegir dataset por argumento.
- Inicia la CLI (menú con módulos 1..4) alineada a los ejemplos del profesor.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional


def _base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _default_dataset_path() -> str:
    # Por defecto, el JSON vive en el mismo directorio que este archivo.
    # Si tu repo lo guarda en /data o similar, aquí lo ajustas.
    base = _base_dir()
    candidate = os.path.join(base, "dataset_conocimiento2026.json")
    return candidate


def _ensure_imports() -> None:
    """
    Asegura que Python encuentre la carpeta del proyecto para importar 'modulos.*'
    aunque se ejecute desde otra ruta.
    """
    base = _base_dir()
    if base not in sys.path:
        sys.path.insert(0, base)


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simulador_ic.py",
        description="Simulador de Ingeniería del Conocimiento (CLI) — Diagnóstico EV (SSB).",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=_default_dataset_path(),
        help="Ruta al archivo dataset_conocimiento2026.json (por defecto el del repo).",
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Fuerza modo STUB (solo interfaz), útil si faltan módulos o estás depurando imports.",
    )
    return parser.parse_args(argv)


def _pretty_fail(msg: str) -> None:
    line = "=" * 70
    print("\n" + line)
    print(" ERROR DE INICIO")
    print(line)
    print(msg)
    print(line)


def main(argv: Optional[list] = None) -> int:
    _ensure_imports()
    args = _parse_args(argv)

    dataset_path = os.path.abspath(args.dataset)

    # Validación temprana de dataset (existencia)
    if not os.path.exists(dataset_path):
        _pretty_fail(
            f"No se encontró el dataset JSON.\n\n"
            f"Ruta recibida:\n- {dataset_path}\n\n"
            f"Sugerencias:\n"
            f"- Verifica que exista 'dataset_conocimiento2026.json' en el repo.\n"
            f"- O ejecuta: python simulador_ic.py --dataset RUTA/AL/JSON\n"
        )
        return 1

    # Importar CLI
    try:
        from modulos.cli import CLI
    except Exception as e:
        _pretty_fail(
            "No se pudo importar la CLI (modulos/cli.py).\n\n"
            f"Detalle:\n- {e}\n\n"
            "Sugerencias:\n"
            "- Verifica que exista la carpeta 'modulos' y el archivo 'cli.py'.\n"
            "- Verifica que no haya errores de sintaxis en los módulos.\n"
            "- Si estás a mitad de integración, corre en modo STUB:\n"
            "  python simulador_ic.py --stub\n"
        )
        return 2

    # Ejecutar CLI
    try:
        app = CLI(dataset_path=dataset_path, modo_stub=args.stub)
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupción por teclado. Saliendo...")
        return 0
    except Exception as e:
        _pretty_fail(
            "Ocurrió un error durante la ejecución.\n\n"
            f"Detalle:\n- {e}\n\n"
            "Sugerencias:\n"
            "- Corre nuevamente para reproducir.\n"
            "- Revisa primero: DatasetStore.validate_basic_schema() en el inicio.\n"
            "- Si falla por JSON, corrige el dataset.\n"
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())