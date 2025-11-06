import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

# Agregar path para imports compartidos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from common.config_loader import (
    ConfigSource,
    build_config_from_sources,
    load_from_airflow_connection,
    load_from_airflow_variables,
    load_from_yaml,
    load_from_env,
)

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = BASE_DIR / "settings.yaml"

_ENV_FIELD_MAP: Mapping[str, str] = {
    "username": "USERNAME",
    "password": "PASSWORD",
    "download_path": "DOWNLOAD_PATH",
    "max_iframe_attempts": "MAX_IFRAME_ATTEMPTS",
    "max_status_attempts": "MAX_STATUS_ATTEMPTS",
    "options_to_select": "OPTIONS_TO_SELECT",
    "date_mode": "DATE_MODE",
    "date_from": "DATE_FROM",
    "date_to": "DATE_TO",
    "gde_output_filename": "GDE_OUTPUT_FILENAME",
    "dynamic_checklist_output_filename": "DYNAMIC_CHECKLIST_OUTPUT_FILENAME",
    "export_overwrite_files": "EXPORT_OVERWRITE_FILES",
    "proxy": "PROXY",
    "headless": "HEADLESS",
}

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _default_download_path() -> str:
    if Path("/opt/airflow").exists():
        return "/opt/airflow/proyectos/teleows/temp"
    return str(Path.home() / "Downloads" / "scraper_downloads")


def _load_settings_file() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}

    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover
        # Si PyYAML no está disponible simplemente ignoramos el archivo y
        # continuamos con los valores de entorno.
        return {}

    with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise RuntimeError("El archivo settings.yaml debe contener un mapeo.")

    profile = os.getenv("TELEOWS_ENV", "default")
    section = raw.get(profile, raw)
    if not isinstance(section, dict):
        raise RuntimeError(
            f"La sección '{profile}' de settings.yaml debe ser un objeto con pares clave/valor."
        )

    return dict(section)


def _load_env_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for field, env_var in _ENV_FIELD_MAP.items():
        value = os.getenv(env_var)
        if value is not None:
            overrides[field] = value
    return overrides


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE_VALUES


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_options(value: Any, fallback: List[str]) -> List[str]:
    if value is None:
        return list(fallback)
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or list(fallback)
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or list(fallback)
    return list(fallback)


@dataclass(frozen=True)
class TeleowsSettings:
    """Objeto de configuración consumido por los workflows (inspirado en settings.yaml)."""
    username: str
    password: str
    download_path: str
    max_iframe_attempts: int = 60
    max_status_attempts: int = 60
    options_to_select: List[str] = field(default_factory=lambda: ["CM", "OPM"])
    date_mode: int = 2
    date_from: str = "2025-09-01"
    date_to: str = "2025-09-10"
    gde_output_filename: Optional[str] = None
    dynamic_checklist_output_filename: Optional[str] = None
    export_overwrite_files: bool = True
    proxy: Optional[str] = None
    headless: bool = False

    @classmethod
    def load(cls) -> "TeleowsSettings":
        raw_settings: Dict[str, Any] = {}
        raw_settings.update(_load_settings_file())
        raw_settings.update(_load_env_overrides())
        return _build_settings(raw_settings)

    @classmethod
    def load_with_overrides(cls, overrides: Dict[str, Any]) -> "TeleowsSettings":
        raw_settings: Dict[str, Any] = {}
        raw_settings.update(_load_settings_file())
        raw_settings.update(overrides)
        return _build_settings(raw_settings)

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Any]) -> "TeleowsSettings":
        return _build_settings(dict(mapping))

    @classmethod
    def load_from_airflow(
        cls,
        conn_id: str = "teleows_portal",
        variable_prefix: str = "TELEOWS_",
        postgres_conn_id: Optional[str] = None,
    ) -> "TeleowsSettings":
        """
        Carga configuración con FALLBACK POR CAMPO.

        PRIORIDAD (busca campo por campo en este orden):
        1. Airflow Connection (si el campo existe aquí, úsalo)
        2. Airflow Variables (si no está en Connection, búscalo aquí)
        3. YAML (si no está en Variables, búscalo aquí)
        4. ENV (si no está en YAML, búscalo aquí)
        5. Default (si no está en ninguna fuente)

        Ejemplo: Si 'username' está en Connection pero 'proxy' solo está en YAML,
                 toma 'username' de Connection y 'proxy' de YAML.

        Args:
            conn_id: ID de la conexión en Airflow para credenciales de scraping
            variable_prefix: Prefijo para variables de Airflow
            postgres_conn_id: ID de conexión PostgreSQL (opcional, para contexto)

        Returns:
            TeleowsSettings configurado según prioridades

        Example:
            >>> # En un DAG de Airflow
            >>> settings = TeleowsSettings.load_from_airflow()
        """
        import logging
        logger = logging.getLogger(__name__)

        # Definir fuentes en orden de prioridad (mayor a menor)
        sources = [
            # 1. Airflow Connection (prioridad más alta)
            ConfigSource(
                "Airflow Connection",
                lambda: load_from_airflow_connection(
                    conn_id,
                    extra_fields=list(_ENV_FIELD_MAP.keys())
                )
            ),
            # 2. Airflow Variables
            ConfigSource(
                "Airflow Variables",
                lambda: load_from_airflow_variables(variable_prefix, _ENV_FIELD_MAP)
            ),
            # 3. YAML
            ConfigSource(
                "YAML",
                lambda: load_from_yaml(str(SETTINGS_PATH), env_key=os.getenv("TELEOWS_ENV", "default"))
            ),
            # 4. ENV (menor prioridad)
            ConfigSource(
                "ENV",
                lambda: load_from_env(_ENV_FIELD_MAP)
            ),
        ]

        # Especificación de campos con defaults y transformaciones
        fields_spec = {
            "username": {"default": None, "required": True},
            "password": {"default": None, "required": True},
            "download_path": {"default": _default_download_path()},
            "max_iframe_attempts": {"default": 60, "transform": int},
            "max_status_attempts": {"default": 60, "transform": int},
            "options_to_select": {"default": ["CM", "OPM"], "transform": _as_options},
            "date_mode": {"default": 2, "transform": int},
            "date_from": {"default": "2025-09-01"},
            "date_to": {"default": "2025-09-10"},
            "gde_output_filename": {"default": None},
            "dynamic_checklist_output_filename": {"default": None},
            "export_overwrite_files": {"default": True, "transform": lambda v: _as_bool(v, True)},
            "proxy": {"default": None},
            "headless": {"default": False, "transform": lambda v: _as_bool(v, False)},
        }

        # Construir configuración con fallback por campo
        logger.info("🔧 Cargando configuración con fallback por campo...")
        raw_settings = build_config_from_sources(fields_spec, sources)

        return _build_settings(raw_settings)


def _build_settings(raw_settings: Dict[str, Any]) -> TeleowsSettings:
    """Normaliza el diccionario recibido y instancia TeleowsSettings."""
    username = _as_optional_str(raw_settings.get("username"))
    password = _as_optional_str(raw_settings.get("password"))

    if not username or not password:
        raise ValueError(
            "Credenciales no configuradas. Define USERNAME y PASSWORD (ya sea en variables "
            "de entorno, Airflow o settings.yaml)."
        )

    download_path_setting = _as_optional_str(raw_settings.get("download_path")) or _default_download_path()
    download_path = Path(download_path_setting).expanduser()
    try:
        download_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    download_path_str = str(download_path.resolve())

    max_iframe_attempts = _as_int(raw_settings.get("max_iframe_attempts"), 60)
    max_status_attempts = _as_int(raw_settings.get("max_status_attempts"), 60)
    options_to_select = _as_options(raw_settings.get("options_to_select"), ["CM", "OPM"])
    date_mode = _as_int(raw_settings.get("date_mode"), 2)
    date_from = _as_optional_str(raw_settings.get("date_from")) or "2025-09-01"
    date_to = _as_optional_str(raw_settings.get("date_to")) or "2025-09-10"
    gde_output_filename = _as_optional_str(raw_settings.get("gde_output_filename"))
    dynamic_output_filename = _as_optional_str(
        raw_settings.get("dynamic_checklist_output_filename")
    )
    export_overwrite_files = _as_bool(raw_settings.get("export_overwrite_files"), True)
    proxy_value = _as_optional_str(raw_settings.get("proxy"))
    headless_value = _as_bool(raw_settings.get("headless"), False)

    return TeleowsSettings(
        username=username,
        password=password,
        download_path=download_path_str,
        max_iframe_attempts=max_iframe_attempts,
        max_status_attempts=max_status_attempts,
        options_to_select=options_to_select,
        date_mode=date_mode,
        date_from=date_from,
        date_to=date_to,
        gde_output_filename=gde_output_filename,
        dynamic_checklist_output_filename=dynamic_output_filename,
        export_overwrite_files=export_overwrite_files,
        proxy=proxy_value,
        headless=headless_value,
    )


def load_default_settings() -> TeleowsSettings:
    """
    Helper opcional para scripts locales.

    Equivalente a ``TeleowsSettings.load()`` pero mantiene compatibilidad con código
    que antes importaba constantes globales.
    """
    return TeleowsSettings.load()


# ================================================================================
# Funciones adicionales para carga de configuraciones (ETL/Loader)
# ================================================================================

def _replace_env_variables(config: Any) -> Any:
    """
    Reemplaza variables de entorno en el formato ${VAR_NAME} recursivamente.

    Args:
        config: Diccionario, lista o string de configuración

    Returns:
        Configuración con variables reemplazadas
    """
    if isinstance(config, dict):
        return {k: _replace_env_variables(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_variables(item) for item in config]
    elif isinstance(config, str):
        # Buscar patrón ${VAR_NAME}
        if config.startswith("${") and config.endswith("}"):
            var_name = config[2:-1]
            value = os.getenv(var_name)
            if value is None:
                import logging
                logging.getLogger(__name__).warning(f"Variable de entorno '{var_name}' no definida")
                return config
            return value
        return config
    else:
        return config


def load_yaml_config(
    env: Optional[str] = None,
    postgres_conn_id: Optional[str] = "postgres_teleows"
) -> Dict[str, Any]:
    """
    Carga configuración completa desde settings.yaml con FALLBACK POR CAMPO.

    PRIORIDAD para configuración PostgreSQL (campo por campo):
    1. Airflow Connection (si un campo existe aquí, úsalo)
    2. Variables de entorno (${POSTGRES_HOST}, etc.)
    3. YAML (valores por defecto)

    Retorna TODO el contenido del YAML, útil para loaders que necesitan
    acceder a secciones adicionales como 'postgres', 'gde', etc.

    Args:
        env: Perfil de entorno a cargar (default, production, etc.)
             Si no se especifica, usa TELEOWS_ENV o 'default'
        postgres_conn_id: ID de la conexión PostgreSQL en Airflow.
                         Si es None, no se consulta Airflow

    Returns:
        Diccionario con la configuración completa

    Example:
        >>> # En Airflow (usa Connection con fallback a YAML/ENV por campo)
        >>> config = load_yaml_config()
        >>> postgres_config = config.get('postgres', {})
        >>>
        >>> # Fuera de Airflow (solo YAML + ENV)
        >>> config = load_yaml_config(postgres_conn_id=None)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        env_profile = env or os.getenv("TELEOWS_ENV", "default")

        # Cargar configuración base desde YAML
        if not SETTINGS_PATH.exists():
            logger.warning(f"No existe settings.yaml en {SETTINGS_PATH}, usando valores por defecto")
            config = {}
        else:
            try:
                import yaml
            except ImportError:
                raise ImportError("PyYAML es requerido. Instala con: pip install pyyaml")

            with SETTINGS_PATH.open('r', encoding='utf-8') as file:
                raw_config = yaml.safe_load(file) or {}

            if not isinstance(raw_config, dict):
                raise RuntimeError("El archivo settings.yaml debe contener un mapeo.")

            # Obtener la sección del perfil
            config = raw_config.get(env_profile, raw_config)

            if not isinstance(config, dict):
                raise RuntimeError(
                    f"La sección '{env_profile}' de settings.yaml debe ser un objeto con pares clave/valor."
                )

            # Reemplazar variables de entorno ${VAR}
            config = _replace_env_variables(config)

        # Aplicar fallback por campo para PostgreSQL
        if postgres_conn_id:
            postgres_fields = ["host", "port", "database", "user", "password"]

            # Definir fuentes en orden de prioridad
            sources = [
                # 1. Airflow Connection (prioridad más alta)
                ConfigSource(
                    f"Airflow Connection ({postgres_conn_id})",
                    lambda: load_from_airflow_connection(postgres_conn_id)
                ),
                # 2. YAML+ENV (ya procesado con _replace_env_variables)
                ConfigSource(
                    "YAML+ENV",
                    lambda: config.get("postgres", {})
                ),
            ]

            # Construir configuración PostgreSQL con fallback por campo
            postgres_from_yaml_env = config.get("postgres", {})
            postgres_config = {}

            for field in postgres_fields:
                # Buscar en cada fuente hasta encontrar el campo
                for source in sources:
                    value = source.get(field)
                    if value is not None:
                        postgres_config[field] = value
                        break
                else:
                    # Si no se encuentra, usar valor por defecto del YAML
                    if field in postgres_from_yaml_env:
                        postgres_config[field] = postgres_from_yaml_env[field]

            if postgres_config:
                config["postgres"] = postgres_config
                logger.info(f"✓ PostgreSQL configurado con fallback por campo desde {postgres_conn_id}")

        logger.debug(f"Configuración cargada desde perfil '{env_profile}'")
        return config

    except Exception as e:
        logger.error(f"Error al cargar configuración: {e}")
        raise
