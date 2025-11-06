"""
Sistema de carga de configuración con fallback por campo para todos los proyectos.

PRIORIDAD (de mayor a menor):
1. Airflow Connections (si existe el campo aquí, úsalo)
2. Airflow Variables (si no está en Connection, búscalo aquí)
3. YAML (si no está en Variables, búscalo aquí)
4. ENV (si no está en YAML, búscalo aquí)
5. Default (valor por defecto si no está en ninguna fuente)

Cada campo se busca independientemente siguiendo este orden.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class ConfigSource:
    """Representa una fuente de configuración con un nombre y método de acceso."""

    def __init__(self, name: str, loader: Callable[[], Dict[str, Any]]):
        """
        Args:
            name: Nombre descriptivo de la fuente (ej: "Airflow Connection")
            loader: Función que retorna un diccionario con la configuración
        """
        self.name = name
        self.loader = loader
        self._cache: Optional[Dict[str, Any]] = None

    def get(self, field: str) -> Optional[Any]:
        """
        Obtiene un valor de la fuente.

        Args:
            field: Nombre del campo a buscar

        Returns:
            El valor del campo o None si no existe
        """
        if self._cache is None:
            try:
                self._cache = self.loader()
                logger.debug(f"✓ {self.name} cargado con {len(self._cache)} campos")
            except Exception as exc:
                logger.debug(f"⚠ {self.name} no disponible: {exc}")
                self._cache = {}

        value = self._cache.get(field)
        if value is not None:
            logger.debug(f"  → Campo '{field}' encontrado en {self.name}: {type(value).__name__}")
        return value

    def get_all(self) -> Dict[str, Any]:
        """Retorna todos los valores de esta fuente."""
        if self._cache is None:
            self.get("_dummy_")  # Forzar carga
        return self._cache or {}


def get_field_with_fallback(
    field: str,
    sources: List[ConfigSource],
    default: Any = None,
    transform: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """
    Busca un campo en múltiples fuentes con fallback.

    Args:
        field: Nombre del campo a buscar
        sources: Lista de fuentes ordenadas por prioridad (mayor a menor)
        default: Valor por defecto si no se encuentra en ninguna fuente
        transform: Función opcional para transformar el valor encontrado

    Returns:
        El primer valor no-None encontrado (o default)

    Example:
        >>> sources = [airflow_conn, airflow_vars, yaml, env]
        >>> username = get_field_with_fallback("username", sources, default="admin")
    """
    for source in sources:
        value = source.get(field)
        if value is not None:
            if transform:
                try:
                    return transform(value)
                except Exception as exc:
                    logger.warning(f"Error transformando '{field}' de {source.name}: {exc}")
                    continue
            return value

    logger.debug(f"  → Campo '{field}' no encontrado, usando default: {default}")
    return default


def build_config_from_sources(
    fields: Dict[str, Dict[str, Any]],
    sources: List[ConfigSource],
) -> Dict[str, Any]:
    """
    Construye un diccionario de configuración buscando campos en múltiples fuentes.

    Args:
        fields: Diccionario con especificación de campos:
                {
                    "field_name": {
                        "default": valor_por_defecto,
                        "transform": funcion_transformacion,  # opcional
                        "required": True/False,  # opcional
                    }
                }
        sources: Lista de fuentes ordenadas por prioridad

    Returns:
        Diccionario con la configuración construida

    Raises:
        ValueError: Si un campo required no se encuentra

    Example:
        >>> fields = {
        ...     "username": {"default": None, "required": True},
        ...     "port": {"default": 5432, "transform": int},
        ...     "headless": {"default": False, "transform": lambda v: str(v).lower() in ['true', '1']},
        ... }
        >>> config = build_config_from_sources(fields, sources)
    """
    config = {}

    for field_name, field_spec in fields.items():
        default = field_spec.get("default")
        transform = field_spec.get("transform")
        required = field_spec.get("required", False)

        value = get_field_with_fallback(field_name, sources, default=default, transform=transform)

        if required and value is None:
            raise ValueError(
                f"Campo requerido '{field_name}' no encontrado en ninguna fuente de configuración"
            )

        config[field_name] = value

    return config


# ================================================================================
# Loaders específicos para diferentes fuentes
# ================================================================================


def load_from_airflow_connection(conn_id: str, extra_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Carga configuración desde Airflow Connection.

    Args:
        conn_id: ID de la conexión en Airflow
        extra_fields: Lista de campos adicionales a extraer de 'extra_dejson'

    Returns:
        Diccionario con campos de la conexión

    Example:
        >>> config = load_from_airflow_connection("teleows_portal", ["proxy", "headless"])
        >>> # {'username': '...', 'password': '...', 'proxy': '...', 'headless': '...'}
    """
    try:
        from airflow.sdk.bases.hook import BaseHook

        conn = BaseHook.get_connection(conn_id)
        config = {}

        # Campos estándar
        if conn.login:
            config["username"] = conn.login
            config["user"] = conn.login
        if conn.password:
            config["password"] = conn.password
        if conn.host:
            config["host"] = conn.host
        if conn.port:
            config["port"] = conn.port
        if conn.schema:
            config["database"] = conn.schema
            config["schema"] = conn.schema

        # Campos extras
        extras = getattr(conn, "extra_dejson", {}) or {}
        if isinstance(extras, dict) and extra_fields:
            for field in extra_fields:
                value = extras.get(field)
                if value is not None:
                    config[field] = value

        logger.info(f"✓ Airflow Connection '{conn_id}' cargado: {list(config.keys())}")
        return config

    except ImportError:
        logger.debug("Airflow no disponible")
        return {}
    except Exception as exc:
        logger.debug(f"No se pudo cargar Connection '{conn_id}': {exc}")
        return {}


def load_from_airflow_variables(prefix: str, field_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Carga configuración desde Airflow Variables.

    Args:
        prefix: Prefijo de las variables (ej: "TELEOWS_")
        field_map: Mapeo de nombre_campo → nombre_variable_env
                   {"username": "USERNAME", "password": "PASSWORD"}

    Returns:
        Diccionario con valores de variables

    Example:
        >>> config = load_from_airflow_variables("TELEOWS_", {"username": "USERNAME"})
        >>> # Busca variable "TELEOWS_USERNAME"
    """
    try:
        from airflow.sdk import Variable

        config = {}
        for field_name, env_name in field_map.items():
            var_name = f"{prefix}{env_name}"
            try:
                value = Variable.get(var_name)
                if value is not None:
                    config[field_name] = value
            except (KeyError, Exception):
                continue

        logger.debug(f"✓ Airflow Variables cargadas ({prefix}*): {list(config.keys())}")
        return config

    except ImportError:
        logger.debug("Airflow no disponible")
        return {}


def load_from_yaml(yaml_path: str, env_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga configuración desde archivo YAML (con soporte para variables de entorno).

    Args:
        yaml_path: Ruta al archivo YAML
        env_key: Clave opcional para extraer una sección específica

    Returns:
        Diccionario con configuración del YAML

    Example:
        >>> config = load_from_yaml("settings.yaml", env_key="default")
    """
    try:
        if not os.path.exists(yaml_path):
            logger.debug(f"YAML no encontrado: {yaml_path}")
            return {}

        import yaml

        with open(yaml_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        if env_key and isinstance(raw, dict):
            config = raw.get(env_key, raw)
        else:
            config = raw

        # Reemplazar ${VAR} con valores de entorno
        config = _replace_env_variables(config)

        logger.debug(f"✓ YAML cargado: {len(config)} campos desde {yaml_path}")
        return config if isinstance(config, dict) else {}

    except Exception as exc:
        logger.debug(f"Error cargando YAML: {exc}")
        return {}


def load_from_env(field_map: Dict[str, str]) -> Dict[str, Any]:
    """
    Carga configuración desde variables de entorno.

    Args:
        field_map: Mapeo de nombre_campo → nombre_variable_env

    Returns:
        Diccionario con valores de ENV

    Example:
        >>> config = load_from_env({"username": "USERNAME", "password": "PASSWORD"})
    """
    config = {}
    for field_name, env_name in field_map.items():
        value = os.getenv(env_name)
        if value is not None:
            config[field_name] = value

    logger.debug(f"✓ ENV cargado: {list(config.keys())}")
    return config


def _replace_env_variables(config: Any) -> Any:
    """
    Reemplaza ${VAR} con valores de entorno recursivamente.

    Args:
        config: Configuración (dict, list o string)

    Returns:
        Configuración con variables reemplazadas
    """
    if isinstance(config, dict):
        return {k: _replace_env_variables(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_variables(item) for item in config]
    elif isinstance(config, str):
        if config.startswith("${") and config.endswith("}"):
            var_name = config[2:-1]
            return os.getenv(var_name, config)
        return config
    return config


# ================================================================================
# Helper para proyectos que usan EnvYAML (energiafacilities, enervision)
# ================================================================================


def load_config_with_postgres_fallback(
    config_path: str,
    postgres_conn_id: Optional[str] = "postgres_default",
    postgres_field_names: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Carga configuración desde YAML (con EnvYAML) y aplica fallback para PostgreSQL.

    PRIORIDAD para campos de PostgreSQL:
    1. Airflow Connection (si existe)
    2. YAML con variables ${...} reemplazadas por ENV

    Args:
        config_path: Ruta al archivo YAML de configuración
        postgres_conn_id: ID de la conexión PostgreSQL en Airflow
        postgres_field_names: Mapeo de nombres de campos de Airflow → YAML
                              Default: {"user": "user", "password": "password", ...}

    Returns:
        Diccionario completo de configuración con PostgreSQL actualizado

    Example:
        >>> from pathlib import Path
        >>> config_path = Path(__file__).parent / "config" / "config_dev.yaml"
        >>> config = load_config_with_postgres_fallback(str(config_path))
    """
    # Mapeo por defecto
    if postgres_field_names is None:
        postgres_field_names = {
            "host": "host",
            "port": "port",
            "user": "user",
            "password": "password",
            "database": "database",
        }

    # Cargar configuración base desde YAML (con EnvYAML si está disponible)
    try:
        from envyaml import EnvYAML  # type: ignore
        config = dict(EnvYAML(config_path, strict=False))
        logger.debug(f"✓ Config cargado con EnvYAML desde {config_path}")
    except ImportError:
        # Fallback a YAML normal con reemplazo manual
        config = load_from_yaml(config_path)
        logger.debug(f"✓ Config cargado con PyYAML desde {config_path}")

    # Aplicar fallback por campo para PostgreSQL
    if postgres_conn_id:
        postgres_from_yaml = config.get("postgres", {})

        # Fuentes en orden de prioridad
        sources = [
            # 1. Airflow Connection (prioridad más alta)
            ConfigSource(
                f"Airflow Connection ({postgres_conn_id})",
                lambda: load_from_airflow_connection(postgres_conn_id)
            ),
            # 2. YAML+ENV
            ConfigSource(
                "YAML+ENV",
                lambda: postgres_from_yaml
            ),
        ]

        # Construir config PostgreSQL con fallback
        postgres_config = {}
        for airflow_field, yaml_field in postgres_field_names.items():
            for source in sources:
                # Buscar con nombre de campo de Airflow
                value = source.get(airflow_field)
                if value is not None:
                    postgres_config[yaml_field] = value
                    break
            else:
                # Si no se encuentra, mantener valor del YAML
                if yaml_field in postgres_from_yaml:
                    postgres_config[yaml_field] = postgres_from_yaml[yaml_field]

        if postgres_config:
            config["postgres"] = postgres_config
            logger.info(f"✓ PostgreSQL configurado con fallback desde {postgres_conn_id}")

    return config
