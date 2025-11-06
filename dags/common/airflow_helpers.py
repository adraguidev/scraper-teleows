"""
Utilidades compartidas para carga de configuración desde Airflow.

Este módulo centraliza la lógica de carga de configuración desde:
1. Airflow Connections (prioridad más alta)
2. Airflow Variables
3. Variables de entorno (fallback)

Evita duplicación de código entre DAGs.
"""

import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

# Campos válidos para TeleowsSettings
SETTINGS_FIELDS: Set[str] = {
    "username",
    "password",
    "download_path",
    "max_iframe_attempts",
    "max_status_attempts",
    "options_to_select",
    "date_mode",
    "date_from",
    "date_to",
    "gde_output_filename",
    "dynamic_checklist_output_filename",
    "export_overwrite_files",
    "proxy",
    "headless",
}


def load_connection_overrides(conn_id: str) -> Dict[str, Any]:
    """
    Carga configuración desde Airflow Connection.

    Args:
        conn_id: ID de la conexión en Airflow (ej: 'teleows_portal')

    Returns:
        Diccionario con overrides desde la conexión
    """
    if not conn_id:
        return {}

    try:
        from airflow.sdk.bases.hook import BaseHook
    except ImportError:
        logger.warning("⚠ Airflow no disponible, no se pueden cargar Connections")
        return {}

    try:
        conn = BaseHook.get_connection(conn_id)
    except Exception as exc:
        logger.warning("⚠ No se pudo obtener la conexión '%s': %s", conn_id, exc)
        return {}

    overrides: Dict[str, Any] = {}

    # Credenciales básicas
    if conn.login:
        overrides["username"] = conn.login
    if conn.password:
        overrides["password"] = conn.password

    # Extras (configuraciones adicionales en JSON)
    extras = getattr(conn, "extra_dejson", {}) or {}
    if isinstance(extras, dict):
        for field in SETTINGS_FIELDS:
            value = extras.get(field)
            if value is not None:
                overrides[field] = value

    logger.debug("✓ Cargados %d overrides desde Connection '%s'", len(overrides), conn_id)
    return overrides


def load_variable_overrides(prefix: str = "TELEOWS_") -> Dict[str, Any]:
    """
    Carga configuración desde Airflow Variables.

    Args:
        prefix: Prefijo para las variables (ej: 'TELEOWS_')

    Returns:
        Diccionario con overrides desde variables
    """
    if not prefix:
        return {}

    try:
        from airflow.sdk import Variable
    except ImportError:
        logger.warning("⚠ Airflow no disponible, no se pueden cargar Variables")
        return {}

    overrides: Dict[str, Any] = {}

    for field in SETTINGS_FIELDS:
        var_name = f"{prefix}{field.upper()}"
        try:
            value = Variable.get(var_name)
            overrides[field] = value
        except KeyError:
            continue
        except Exception as exc:
            logger.debug("⚠ No se pudo leer la Variable '%s': %s", var_name, exc)
            continue

    logger.debug("✓ Cargados %d overrides desde Variables (prefix=%s)", len(overrides), prefix)
    return overrides


def load_postgres_connection_config(conn_id: str = "postgres_teleows") -> Dict[str, Any]:
    """
    Carga configuración de PostgreSQL desde Airflow Connection.

    Args:
        conn_id: ID de la conexión PostgreSQL en Airflow

    Returns:
        Diccionario con config de PostgreSQL para BaseLoaderPostgres/PostgresConnector

    Example:
        >>> config = load_postgres_connection_config("postgres_teleows")
        >>> # {"host": "...", "port": 5432, "database": "...", "user": "...", "password": "..."}
    """
    if not conn_id:
        logger.warning("⚠ No se especificó conn_id para PostgreSQL")
        return {}

    try:
        from airflow.sdk.bases.hook import BaseHook
    except ImportError:
        logger.warning("⚠ Airflow no disponible, no se puede cargar Connection PostgreSQL")
        return {}

    try:
        conn = BaseHook.get_connection(conn_id)
    except Exception as exc:
        logger.warning("⚠ No se pudo obtener la conexión PostgreSQL '%s': %s", conn_id, exc)
        return {}

    config = {
        "host": conn.host or "localhost",
        "port": conn.port or 5432,
        "database": conn.schema or "postgres",
        "user": conn.login or "postgres",
        "password": conn.password or "",
    }

    logger.info("✓ Configuración PostgreSQL cargada desde Connection '%s'", conn_id)
    return config
