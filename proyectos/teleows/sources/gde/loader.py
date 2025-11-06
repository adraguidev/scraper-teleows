from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from teleows.config import load_yaml_config
from teleows.core.base_loader import BaseLoaderPostgres
from teleows.core.utils import load_json_config

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def load_gde(filepath: Optional[PathLike] = None, postgres_conn_id: Optional[str] = "postgres_teleows") -> dict:
    """
    Carga los datos extraídos de GDE hacia PostgreSQL.

    Configuración de PostgreSQL con orden de prioridad:
    1. Airflow Connection (postgres_conn_id) - prioridad más alta
    2. Variables de entorno (${POSTGRES_HOST}, etc.)
    3. settings.yaml (valores por defecto)

    Args:
        filepath: Ruta al archivo Excel descargado. Si no se proporciona,
                 se usa la configuración de settings.yaml
        postgres_conn_id: ID de la conexión PostgreSQL en Airflow.
                         Por defecto "postgres_teleows".
                         Usar None para solo YAML + ENV (desarrollo local)

    Returns:
        Diccionario con el resultado de la carga (status, code, etl_msg)

    Example:
        >>> # En Airflow (usa Connection automáticamente)
        >>> resultado = load_gde("./tmp/Console_GDE_export.xlsx")
        >>> print(resultado['etl_msg'])
        >>>
        >>> # Desarrollo local (sin Airflow)
        >>> resultado = load_gde("./tmp/file.xlsx", postgres_conn_id=None)
    """
    try:
        # Cargar configuraciones (consulta Airflow Connection si está disponible)
        config = load_yaml_config(postgres_conn_id=postgres_conn_id)
        postgres_config = config.get("postgres", {})
        gde_config = config.get("gde", {})

        # Validar que existen las configuraciones necesarias
        if not postgres_config:
            raise ValueError("No se encontró configuración 'postgres' en settings.yaml")
        if not gde_config:
            raise ValueError("No se encontró configuración 'gde' en settings.yaml")

        # Crear instancia del loader
        loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=gde_config
        )

        # Validar conexión
        logger.info("Validando conexión a PostgreSQL...")
        loader.validar_conexion()

        # Cargar mapeo de columnas
        logger.info("Cargando mapeo de columnas...")
        columnas = load_json_config(
            archivo='config/columnas/columns_map.json',
            valor='gde_tasks'
        )

        # Determinar ruta del archivo
        if not filepath:
            local_dir = gde_config.get('local_dir', './tmp')
            filename = gde_config.get('specific_filename', 'Console_GDE_export.xlsx')
            filepath = f"{local_dir}/{filename}"

        filepath_str = str(filepath)
        logger.info(f"Cargando datos desde: {filepath_str}")

        # Verificar datos (sin strictreview para permitir columnas faltantes)
        logger.info("Verificando estructura de datos...")
        loader.verificar_datos(
            data=filepath_str,
            column_mapping=columnas,
            strictreview=False,  # Permite columnas opcionales (fecha_ingesta, archivo_origen)
            numerofilasalto=0
        )

        # Cargar datos
        logger.info("Iniciando carga de datos a PostgreSQL...")
        resultado = loader.load_data(
            data=filepath_str,
            column_mapping=columnas,
            numerofilasalto=0
        )

        logger.info(f"Carga completada exitosamente: {resultado['etl_msg']}")
        return resultado

    except FileNotFoundError as e:
        msg = f"Archivo no encontrado: {e}"
        logger.error(msg)
        raise
    except ValueError as e:
        msg = f"Error de configuración: {e}"
        logger.error(msg)
        raise
    except Exception as e:
        msg = f"Error durante la carga de datos: {e}"
        logger.error(msg)
        raise
