"""
Loader para Dynamic Checklist con soporte para múltiples pestañas.

Cada pestaña del Excel se carga a su propia tabla RAW en PostgreSQL.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from teleows.config import load_yaml_config
from teleows.core.base_loader import BaseLoaderPostgres
from teleows.core.utils import load_json_config

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def load_dynamic_checklist(
    filepath: Optional[PathLike] = None,
    postgres_conn_id: Optional[str] = "postgres_teleows",
    sheets_to_load: Optional[List[str]] = None
) -> Dict[str, dict]:
    """
    Carga todas las pestañas del Excel de Dynamic Checklist a PostgreSQL.

    Proceso por pestaña:
    1. Lee la configuración de la pestaña desde settings.yaml
    2. Carga el mapeo de columnas desde columns_map.json (si existe)
    3. Carga los datos a la tabla RAW correspondiente

    Args:
        filepath: Ruta al archivo Excel. Si None, usa la ruta de settings.yaml
        postgres_conn_id: ID de conexión PostgreSQL en Airflow
        sheets_to_load: Lista de nombres de pestañas a cargar. Si None, carga todas.

    Returns:
        Diccionario con resultado por cada pestaña:
        {
            "sheet_name": {"status": "success", "code": 200, "etl_msg": "...", "rows": 100},
            ...
        }

    Example:
        >>> # Cargar todas las pestañas
        >>> resultados = load_dynamic_checklist("./tmp/DynamicChecklist_SubPM.xlsx")
        >>>
        >>> # Cargar solo algunas pestañas
        >>> resultados = load_dynamic_checklist(
        ...     "./tmp/file.xlsx",
        ...     sheets_to_load=["avr", "clima", "ups_bateria_de_ups"]
        ... )
        >>>
        >>> # Ver resultados
        >>> for sheet, resultado in resultados.items():
        ...     print(f"{sheet}: {resultado['etl_msg']}")
    """
    try:
        # Cargar configuración
        config = load_yaml_config(postgres_conn_id=postgres_conn_id)
        postgres_config = config.get("postgres", {})
        dc_config = config.get("dynamic_checklist", {})

        # Validar configuraciones
        if not postgres_config:
            raise ValueError("No se encontró configuración 'postgres' en settings.yaml")
        if not dc_config:
            raise ValueError("No se encontró configuración 'dynamic_checklist' en settings.yaml")

        # Obtener configuración de pestañas
        sheets_config = dc_config.get("sheets", [])
        if not sheets_config:
            raise ValueError(
                "No se encontró 'sheets' en la configuración de dynamic_checklist. "
                "Debes definir las pestañas a procesar en settings.yaml"
            )

        # Filtrar pestañas si se especifica
        if sheets_to_load:
            sheets_config = [s for s in sheets_config if s.get("sheet_name") in sheets_to_load]
            if not sheets_config:
                raise ValueError(f"Ninguna de las pestañas especificadas fue encontrada: {sheets_to_load}")

        # Determinar ruta del archivo
        if not filepath:
            local_dir = dc_config.get("local_dir", "./tmp")
            filename = dc_config.get("specific_filename", "DynamicChecklist_SubPM.xlsx")
            filepath = Path(local_dir) / filename
        else:
            filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        logger.info(f"📊 Cargando Dynamic Checklist desde: {filepath}")
        logger.info(f"   Pestañas a procesar: {len(sheets_config)}")

        # Procesar cada pestaña
        resultados = {}
        total_rows = 0

        for sheet_cfg in sheets_config:
            sheet_name = sheet_cfg.get("sheet_name")
            table_name = sheet_cfg.get("table")

            if not sheet_name or not table_name:
                logger.warning(f"⚠ Configuración incompleta para pestaña, omitiendo: {sheet_cfg}")
                continue

            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Procesando pestaña: {sheet_name} → raw.{table_name}")
                logger.info(f"{'='*60}")

                # Cargar datos de la pestaña
                resultado = _load_single_sheet(
                    filepath=filepath,
                    sheet_name=sheet_name,
                    table_name=table_name,
                    postgres_config=postgres_config,
                    sheet_config=sheet_cfg,
                    global_config=dc_config
                )

                resultados[sheet_name] = resultado
                total_rows += resultado.get("rows", 0)

                logger.info(f"✅ {sheet_name}: {resultado['etl_msg']}")

            except Exception as e:
                error_msg = f"Error procesando pestaña '{sheet_name}': {e}"
                logger.error(f"❌ {error_msg}")
                resultados[sheet_name] = {
                    "status": "error",
                    "code": 500,
                    "etl_msg": error_msg,
                    "rows": 0
                }

        # Resumen final
        exitosas = sum(1 for r in resultados.values() if r["status"] == "success")
        fallidas = len(resultados) - exitosas

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 RESUMEN DE CARGA - Dynamic Checklist")
        logger.info(f"{'='*60}")
        logger.info(f"   Total pestañas procesadas: {len(resultados)}")
        logger.info(f"   ✅ Exitosas: {exitosas}")
        logger.info(f"   ❌ Fallidas: {fallidas}")
        logger.info(f"   📝 Total filas cargadas: {total_rows:,}")
        logger.info(f"{'='*60}\n")

        return resultados

    except FileNotFoundError as e:
        logger.error(f"❌ Archivo no encontrado: {e}")
        raise
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Error durante la carga: {e}")
        raise


def _load_single_sheet(
    filepath: Path,
    sheet_name: str,
    table_name: str,
    postgres_config: dict,
    sheet_config: dict,
    global_config: dict
) -> dict:
    """
    Carga una sola pestaña del Excel a PostgreSQL.

    Args:
        filepath: Ruta al archivo Excel
        sheet_name: Nombre de la pestaña
        table_name: Nombre de la tabla destino (sin schema)
        postgres_config: Configuración de PostgreSQL
        sheet_config: Configuración específica de la pestaña
        global_config: Configuración global de dynamic_checklist

    Returns:
        Diccionario con resultado de la carga
    """
    # Configuración de carga
    configload = {
        "schema": global_config.get("schema", "raw"),
        "table": table_name,
        "if_exists": sheet_config.get("if_exists", global_config.get("if_exists", "replace")),
        "chunksize": global_config.get("chunksize", 10000),
    }

    # Crear loader
    loader = BaseLoaderPostgres(config=postgres_config, configload=configload)

    # Validar conexión
    loader.validar_conexion()

    # Intentar cargar mapeo de columnas
    column_mapping = None
    try:
        columns_map = load_json_config(
            archivo='config/columnas/columns_map.json',
            valor=table_name
        )
        column_mapping = columns_map
        logger.debug(f"   ✓ Mapeo de columnas cargado para '{table_name}'")
    except (FileNotFoundError, KeyError):
        logger.debug(f"   ℹ No hay mapeo de columnas para '{table_name}', usando nombres originales")

    # Leer pestaña del Excel
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        rows_count = len(df)
        logger.info(f"   📊 Datos leídos: {rows_count:,} filas, {len(df.columns)} columnas")

        if df.empty:
            logger.warning(f"   ⚠ Pestaña '{sheet_name}' está vacía, omitiendo carga")
            return {
                "status": "warning",
                "code": 200,
                "etl_msg": f"Pestaña vacía, no se cargaron datos",
                "rows": 0
            }

    except ValueError as e:
        # Pestaña no existe en el Excel
        raise ValueError(f"Pestaña '{sheet_name}' no encontrada en el archivo Excel") from e

    # Verificar datos (sin strictreview para permitir columnas opcionales)
    if column_mapping:
        logger.info(f"   🔍 Verificando estructura de datos...")
        loader.verificar_datos(
            data=df,
            column_mapping=column_mapping,
            strictreview=False
        )

    # Cargar datos
    logger.info(f"   📤 Cargando a PostgreSQL: {configload['schema']}.{table_name}...")
    resultado = loader.load_data(
        data=df,
        column_mapping=column_mapping
    )

    resultado["rows"] = rows_count
    return resultado
