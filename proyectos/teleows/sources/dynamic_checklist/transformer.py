"""
Transformaciones para Dynamic Checklist.

NOTA: Este módulo es opcional. Si no necesitas transformar los datos antes
de cargarlos a RAW, puedes omitir este paso y cargar directamente.

Las transformaciones de negocio se realizan en los Stored Procedures (RAW → ODS).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def transformar_dynamic_checklist(archivo_descargado: PathLike) -> str:
    """
    Placeholder para transformaciones pre-carga del Excel de Dynamic Checklist.

    En la mayoría de los casos, NO NECESITAS TRANSFORMAR los datos aquí.
    Carga directamente a RAW y transforma con Stored Procedures.

    Este método es útil solo si necesitas:
    - Renombrar columnas antes de cargar
    - Eliminar columnas innecesarias
    - Agregar columnas calculadas simples
    - Validar datos antes de cargar

    Args:
        archivo_descargado: Ruta al Excel descargado

    Returns:
        Ruta al archivo (transformado o sin cambios)

    Example:
        >>> from teleows.sources.dynamic_checklist.transformer import transformar_dynamic_checklist
        >>>
        >>> # Caso 1: Sin transformaciones (más común)
        >>> archivo = transformar_dynamic_checklist("./tmp/DynamicChecklist.xlsx")
        >>> # Retorna la misma ruta sin cambios
        >>>
        >>> # Caso 2: Con transformaciones
        >>> # Implementa tu lógica aquí si la necesitas
    """
    path = Path(archivo_descargado)

    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")

    logger.info(f"📄 Transformación Dynamic Checklist: Sin cambios (carga directa a RAW)")
    logger.info(f"   Archivo: {path}")

    # Si necesitas transformar, descomenta y usa este código:
    # try:
    #     # Leer todas las pestañas
    #     excel_file = pd.ExcelFile(path)
    #
    #     # Procesar cada pestaña
    #     with pd.ExcelWriter(path, engine='openpyxl') as writer:
    #         for sheet_name in excel_file.sheet_names:
    #             df = pd.read_excel(excel_file, sheet_name=sheet_name)
    #
    #             # Aplicar transformaciones aquí
    #             # df['nueva_columna'] = df['columna'].apply(lambda x: ...)
    #
    #             df.to_excel(writer, sheet_name=sheet_name, index=False)
    #
    #     logger.info(f"✅ Transformaciones aplicadas a {len(excel_file.sheet_names)} pestañas")
    # except Exception as e:
    #     logger.error(f"❌ Error en transformación: {e}")
    #     raise

    return str(path)
