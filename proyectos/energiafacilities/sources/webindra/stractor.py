import time
import hashlib
import logging
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
import urllib3

from core.utils import load_config, default_download_path

# Desactivar warnings de SSL cuando se usa verify=False (necesario para proxies corporativos)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


# ===========================
# FUNCIONES AUXILIARES
# ===========================

def prepare_period(n_months: int) -> tuple[int, int]:
    """Devuelve epoch (inicio, fin) UTC de los últimos n meses completos."""
    def month_start(dt): return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    def add_months(dt, n):
        y, m = divmod(dt.month - 1 + n, 12)
        return dt.replace(year=dt.year + y, month=m + 1)

    now = datetime.now(timezone.utc)
    this_month = month_start(now)
    start = add_months(this_month, -n_months)
    return int(start.timestamp()), int(this_month.timestamp())


def detect_csrf(html: str) -> dict:
    """Busca campos CSRF/token en el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return {
        inp.get("name"): inp.get("value") or ""
        for inp in soup.find_all("input", {"type": "hidden"})
        if "csrf" in (inp.get("name") or "").lower() or "token" in (inp.get("name") or "").lower()
    }


def sha12(data: bytes) -> str:
    """Hash corto para el nombre del archivo."""
    return hashlib.sha256(data).hexdigest()[:12]


# ===========================
# SCRAPER PRINCIPAL (REFACTORIZADO)
# ===========================

def run_scraper(cfg: dict) -> str:
    """
    Flujo principal de scraping: conectividad → login → descarga → guardado.

    Refactorizado en funciones auxiliares para mejor legibilidad:
    - _configure_session(): Configura sesión HTTP con headers
    - _configure_proxy(): Configura proxy si está disponible
    - _verify_connectivity(): Verifica conectividad con servidor
    - _perform_login(): Realiza login con detección CSRF
    - _download_file(): Descarga archivo con reintentos
    - _save_file(): Guarda archivo en sistema de archivos

    Args:
        cfg: Diccionario de configuración con BASE_URL, USER, PASS, etc.

    Returns:
        Ruta del archivo guardado

    Raises:
        ConnectionError: Si falla la conectividad
        RuntimeError: Si falla el login
        Exception: Si falla descarga o guardado
    """
    session = _configure_session(cfg)
    proxies = _configure_proxy(cfg)

    # Verificar conectividad
    _verify_connectivity(session, cfg, proxies)

    # Login
    _perform_login(session, cfg, proxies)

    # Descargar archivo
    data = _download_file(session, cfg, proxies)

    # Guardar archivo
    file_path = _save_file(data, cfg)

    return file_path


def _configure_session(cfg: dict) -> requests.Session:
    """Configura la sesión HTTP con headers apropiados."""
    session = requests.Session()

    # Cargar headers de configuración
    headers = cfg.get("HEADERS") or cfg.get("headers") or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive"
    }

    # Parsear si es string JSON
    if isinstance(headers, str):
        try:
            headers = json.loads(headers)
        except json.JSONDecodeError:
            logger.warning("No se pudo parsear HEADERS como JSON, usando valor por defecto")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Connection": "keep-alive"
            }

    session.headers.update(headers)
    return session


def _configure_proxy(cfg: dict) -> dict | None:
    """Configura el proxy si está disponible en la configuración."""
    proxy = cfg.get("PROXY") or cfg.get("proxy") or os.getenv("PROXY")

    if not proxy:
        logger.warning("⚠️  Proxy NO configurado - las peticiones se harán directamente")
        return None

    proxy_url = proxy if "://" in proxy else f"http://{proxy}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    logger.info(f"✅ Proxy ACTIVO: {proxy_url}")
    return proxies


def _verify_connectivity(session: requests.Session, cfg: dict, proxies: dict | None) -> None:
    """Verifica conectividad con el servidor."""
    try:
        logger.debug(f"Verificando conectividad con {cfg['BASE_URL']}")
        resp = session.head(cfg["BASE_URL"], timeout=10, proxies=proxies, verify=False)
        if resp.status_code >= 400:
            raise ConnectionError(f"Conectividad fallida (HTTP {resp.status_code})")
        logger.debug("Conectividad verificada correctamente")
    except Exception as e:
        logger.error(f"Error de conexión a {cfg['BASE_URL']}: {e}")
        raise


def _perform_login(session: requests.Session, cfg: dict, proxies: dict | None) -> None:
    """Realiza el login con detección de CSRF."""
    try:
        login_url = f"{cfg['BASE_URL'].rstrip('/')}{cfg['LOGIN_PATH']}"
        logger.debug(f"Iniciando sesión en {login_url}")

        # Obtener página de login
        r = session.get(login_url, timeout=cfg["TIMEOUT"], proxies=proxies, verify=False)
        r.raise_for_status()

        # Detectar y agregar tokens CSRF
        csrf = detect_csrf(r.text)
        payload = {"username": cfg["USER"], "password": cfg["PASS"], **csrf}

        # Enviar credenciales
        r2 = session.post(
            login_url,
            data=payload,
            allow_redirects=True,
            timeout=cfg["TIMEOUT"],
            proxies=proxies,
            verify=False
        )
        r2.raise_for_status()

        # Verificar cookie de sesión
        if not any(c.name == "ci_session" for c in session.cookies):
            raise RuntimeError("Login fallido: no se estableció cookie de sesión")

        logger.debug("Login exitoso")

    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise


def _download_file(session: requests.Session, cfg: dict, proxies: dict | None) -> bytes:
    """Descarga el archivo con reintentos exponenciales."""
    start, end = prepare_period(cfg["PERIOD_MONTHS"])
    url = f"{cfg['BASE_URL'].rstrip('/')}{cfg['EXPORT_TMPL'].format(start=start, end=end)}"

    max_retries = cfg.get("MAX_RETRIES", 3)

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug(f"Descargando archivo (intento {attempt}) desde {url}")
            r = session.get(url, timeout=cfg["TIMEOUT"], stream=True, proxies=proxies, verify=False)
            r.raise_for_status()

            data = b"".join(r.iter_content(chunk_size=1024 * 512))
            if not data:
                raise ValueError("Archivo descargado vacío")

            logger.debug(f"Descarga exitosa ({len(data)/1024:.1f} KB)")
            return data

        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Descarga fallida tras {attempt} intentos: {e}")
                raise

            backoff = min(30, 2 ** attempt)
            logger.warning(f"Error descarga ({attempt}): {e}. Reintentando en {backoff}s...")
            time.sleep(backoff)

    raise RuntimeError("Descarga fallida")  # Fallback (nunca debería llegar aquí)


def _save_file(data: bytes, cfg: dict) -> str:
    """Guarda el archivo descargado en el sistema de archivos."""
    try:
        # Determinar carpeta de destino
        local_dir = cfg.get("local_dir") or default_download_path()
        folder = Path(local_dir)
        folder.mkdir(parents=True, exist_ok=True)

        # Determinar nombre del archivo
        if "specific_filename" in cfg and cfg["specific_filename"]:
            name = cfg["specific_filename"]
            if not name.lower().endswith(".xlsx"):
                name += ".xlsx"
        else:
            name = f"recibos_{datetime.now().strftime('%Y%m%d')}_{sha12(data)}.xlsx"

        # Guardar archivo
        path = folder / name
        path.write_bytes(data)

        logger.debug(f"Archivo guardado correctamente: {path}")
        return str(path)

    except Exception as e:
        logger.error(f"Error al guardar archivo: {e}")
        raise


# ===========================
# USO
# ===========================

def stractor_indra() -> Path | None:
    """Ejecuta el scraper de WebIndra y retorna la ruta del archivo descargado."""
    config = load_config()
    configwebindra = config.get("webindra_energia", {})
    try:
        path = run_scraper(configwebindra)
        logger.info(f"Proceso finalizado correctamente: {path}")
        return path
    except Exception as e:
        logger.error(f"Proceso fallido: {e}")
        raise
