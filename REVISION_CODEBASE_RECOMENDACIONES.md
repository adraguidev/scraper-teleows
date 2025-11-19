# RECOMENDACIONES DE REMEDIO
## Proyecto: scraper-teleows

---

## 1. RESOLVER CREDENCIALES HARDCODEADAS

### Acción Inmediata (CRÍTICA)

#### 1.1 Archivo: `/home/user/scraper-teleows/proyectos/test/scraper.py`
**Problema:** Líneas 28-30
```python
USERNAME = os.getenv("GDE_USER", "t71522450")
PASSWORD = os.getenv("GDE_PASS", "R@fSh@yder199810")
PROXY = "telefonica01.gp.inet:8080"
```

**Solución:**
```python
# NUNCA incluir fallback con credenciales reales
USERNAME = os.getenv("GDE_USER")
PASSWORD = os.getenv("GDE_PASS")
PROXY = os.getenv("PROXY", "")  # Fallback a cadena vacía

# Validar al inicio
if not USERNAME or not PASSWORD:
    raise RuntimeError(
        "GDE_USER y GDE_PASS deben estar definidas en variables de entorno"
    )
```

#### 1.2 Archivo: Todos los `config_*.yaml`
**Problema:** Credenciales en texto plano

**Solución:** Implementar patrón con variables de entorno

```yaml
# config_dev.yaml (RECOMENDADO)
postgress:
  user: "${POSTGRES_USER}"          # Fallback de ENV
  password: "${POSTGRES_PASS}"      # Fallback de ENV
  host: "localhost"                 # OK: localhost
  port: 5432

sftp_energia_c:
  host: "${SFTP_ENERGIA_HOST}"
  port: 22
  username: "${SFTP_ENERGIA_USER}"
  password: "${SFTP_ENERGIA_PASS}"

teleows:
  username: "${TELEOWS_USERNAME}"
  password: "${TELEOWS_PASSWORD}"
  proxy: "${TELEOWS_PROXY}"
```

**Modificar:** `/home/user/scraper-teleows/proyectos/energiafacilities/core/utils.py`

En la función `load_config()`, implementar interpolación de variables:

```python
import os
import re

def interpolate_env_vars(config: dict) -> dict:
    """
    Reemplaza ${VAR_NAME} con valores de variables de entorno.
    """
    config_str = json.dumps(config)
    
    # Reemplazar ${VAR_NAME} con os.getenv("VAR_NAME")
    def replace_env(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            raise ValueError(f"Variable de entorno no definida: {var_name}")
        return value
    
    config_str = re.sub(r'\$\{([A-Z_]+)\}', replace_env, config_str)
    return json.loads(config_str)
```

#### 1.3 Crear `.env.gitignored` con valores seguros para desarrollo

```bash
# En /home/user/scraper-teleows/.env (SERÁ GITIGNORED)
POSTGRES_USER=dev_user
POSTGRES_PASS=dev_password_safe
SFTP_ENERGIA_HOST=test_host
SFTP_ENERGIA_USER=test_user
SFTP_ENERGIA_PASS=test_pass
# ... etc
```

#### 1.4 Actualizar `.gitignore`

```bash
# Agregar/verificar:
.env
.env.local
config/secrets.yaml
config/*.private.yaml
*.credentials.json
```

---

## 2. RESOLVER CÓDIGO DUPLICADO

### 2.1 Centralizar funciones de Selenium

**Crear:** `/home/user/scraper-teleows/proyectos/energiafacilities/common/selenium_helpers.py`

```python
"""
Utilidades comunes para Selenium reutilizables en todo el proyecto.
Centraliza funciones que aparecen duplicadas en múltiples archivos.
"""

import logging
from typing import List, Tuple, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


def robust_click(driver, element: WebElement) -> bool:
    """
    Intenta hacer click con múltiples estrategias.
    
    Estrategias (en orden):
    1. Click directo
    2. Scroll + click
    3. JavaScript click
    
    Args:
        driver: WebDriver de Selenium
        element: Elemento a clickear
        
    Returns:
        True si el click fue exitoso, False en caso contrario
    """
    try:
        element.click()
        return True
    except Exception:
        pass
    
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        element.click()
        return True
    except Exception:
        pass
    
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        logger.debug("No se pudo hacer click después de intentar 3 estrategias")
        return False


def switch_to_frame_with(
    driver, 
    selector: str,
    by: str = "auto"
) -> bool:
    """
    Cambia al iframe que contiene el selector especificado.
    
    Args:
        driver: WebDriver
        selector: Selector CSS o XPATH (si inicia con //, se asume XPATH)
        by: Tipo de localizador ("auto", "css", "xpath")
        
    Returns:
        True si se encontró y cambió al iframe, False si no
    """
    driver.switch_to.default_content()
    
    # Determinar tipo de localizador
    if by == "auto":
        by = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
    
    # Intentar en main content
    try:
        driver.find_element(by, selector)
        return True
    except Exception:
        pass
    
    # Buscar en iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            driver.find_element(by, selector)
            return True
        except Exception:
            continue
    
    driver.switch_to.default_content()
    return False


def find_first(
    driver,
    selectors: List[str],
    by: str = "auto"
) -> Tuple[Optional[WebElement], Optional[str]]:
    """
    Encuentra el primer elemento que coincida con cualquiera de los selectores.
    
    Args:
        driver: WebDriver
        selectors: Lista de selectores a probar
        by: Tipo de localizador
        
    Returns:
        Tupla (elemento, selector_usado) o (None, None) si no encuentra
    """
    for selector in selectors:
        try:
            locator_type = By.XPATH if selector.startswith("//") else By.CSS_SELECTOR
            element = driver.find_element(locator_type, selector)
            return element, selector
        except Exception:
            continue
    
    return None, None
```

**Actualizar archivos para usar el módulo centralizado:**

1. `/home/user/scraper-teleows/proyectos/energiafacilities/sources/autin_gde/stractor.py`
   - Remover `_robust_click()` y `_switch_to_frame_with()`
   - Agregar importes:
     ```python
     from energiafacilities.common.selenium_helpers import robust_click, switch_to_frame_with
     ```

2. `/home/user/scraper-teleows/proyectos/energiafacilities/clients/date_filter_manager.py`
   - Remover `_robust_click_element()`
   - Usar `robust_click()` del módulo centralizado

3. `/home/user/scraper-teleows/proyectos/test/scraper.py`
   - Remover `robust_click()`, `switch_to_frame_with()`, `find_first()`
   - Importar desde módulo centralizado

### 2.2 Unificar sistema de login

**Modificar:** `/home/user/scraper-teleows/proyectos/test/scraper.py`

Reemplazar `do_login_robusto()` con:

```python
from energiafacilities.clients.auth import AuthManager
from energiafacilities.clients.browser import BrowserManager

# En main():
browser_manager = BrowserManager(
    download_path=ruta_descarga,
    proxy=PROXY,
    headless=False
)
driver, wait = browser_manager.create_driver()

auth = AuthManager(driver, wait_timeout=60)
if not auth.login(USERNAME, PASSWORD):
    raise RuntimeError("Login falló")
```

### 2.3 Unificar configuración de Chrome

**Crear:** `/home/user/scraper-teleows/proyectos/energiafacilities/common/browser_constants.py`

```python
"""
Constantes compartidas para configuración de navegadores.
"""

# Argumentos Chrome estándar
CHROME_HEADLESS_ARGS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
]

# Preferencias de descargas
DEFAULT_DOWNLOAD_PREFS = {
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_settings.popups": 0,
    "profile.default_content_setting_values.automatic_downloads": 1,
}

# Rutas del sistema donde buscar chromedriver
CHROMEDRIVER_PATHS = [
    "/usr/bin/chromedriver",
    "/usr/local/bin/chromedriver",
]

CHROMIUM_PATHS = [
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chrome",
]

# Configuración de idioma
DEFAULT_LANGUAGE = "es-ES"
LANGUAGE_PREFS = {
    "intl.accept_languages": "es-ES,es",
}
```

---

## 3. RESOLVER NÚMEROS MÁGICOS

### 3.1 Crear constantes de timeouts

**Crear:** `/home/user/scraper-teleows/proyectos/energiafacilities/common/timing_constants.py`

```python
"""
Constantes de timing para waits, sleeps y timeouts.
Centralizado para fácil ajuste en producción.
"""

# === DELAYS PARA UI (segundos) ===
# Basados en patrones observados en autin_gde/stractor.py

DELAY_SHORT = 0.1          # Eventos de UI inmediatos (clicks, inputs)
DELAY_MEDIUM = 0.2         # Cambios de estado de elementos
DELAY_NORMAL = 0.3         # Transiciones de UI estándar
DELAY_LONG = 1.0           # Transiciones completas (modales, nav)
DELAY_VERY_LONG = 2.0      # Operaciones con procesamiento backend

# === WAITS EXPLÍCITOS (segundos) ===
WAIT_SHORT = 3             # Elemento debería estar disponible rápido
WAIT_NORMAL = 8            # Wait estándar para elementos visibles
WAIT_LONG = 15             # Operaciones que tardan más
WAIT_VERY_LONG = 30        # Casos especiales, operaciones largas
WAIT_EXTENDED = 60         # Login, carga de página, etc.

# === TIMEOUTS ESPECÍFICOS ===
LOGIN_TIMEOUT = 60         # Timeout para login
STATUS_POLL_TIMEOUT = 300  # Timeout para monitoreo de estado (5 min)
DOWNLOAD_TIMEOUT = 300     # Timeout para descargas (5 min)
IFRAME_LOAD_TIMEOUT = 60   # Timeout para carga de iframes

# === REINTENTOS ===
MAX_IFRAME_ATTEMPTS = 60   # Intentos para encontrar iframe
MAX_STATUS_ATTEMPTS = 60   # Intentos para verificar estado de exportación
MAX_RETRIES = 3            # Reintentos genéricos
```

**Actualizar archivos:**

1. `/home/user/scraper-teleows/proyectos/test/scraper.py`
   ```python
   from energiafacilities.common.timing_constants import *
   
   # Reemplazar:
   # max_intentosf = 120 → MAX_IFRAME_ATTEMPTS
   # max_intentosC = 60 → MAX_STATUS_ATTEMPTS
   # sleep(1) → sleep(DELAY_LONG)
   # sleep(0.5) → sleep(DELAY_MEDIUM)
   ```

2. `/home/user/scraper-teleows/proyectos/energiafacilities/sources/autin_gde/stractor.py`
   ```python
   from energiafacilities.common.timing_constants import (
       DELAY_SHORT, DELAY_MEDIUM, DELAY_NORMAL, DELAY_LONG, DELAY_VERY_LONG
   )
   
   # Reemplazar constantes locales con las importadas
   ```

3. `/home/user/scraper-teleows/proyectos/energiafacilities/clients/date_filter_manager.py`
   ```python
   from energiafacilities.common.timing_constants import DELAY_*
   ```

### 3.2 Documentar intentos mágicos

```python
# ANTES (sin sentido)
max_intentosf = 120

# DESPUÉS (claro y documentado)
MAX_IFRAME_ATTEMPTS = 60  # 60 intentos * 2s = 2 minutos máximo para encontrar iframe
MAX_STATUS_ATTEMPTS = 60  # 60 intentos * 5s = 5 minutos para exportación
```

---

## 4. RESOLVER PATHS HARDCODEADOS

### 4.1 Centralizar detección de rutas

**Crear:** `/home/user/scraper-teleows/proyectos/energiafacilities/core/path_config.py`

```python
"""
Detección y configuración centralizada de rutas.
"""

import os
from pathlib import Path

# === DETECCIÓN DE ENTORNO ===

def is_airflow_environment() -> bool:
    """Detecta si estamos en Airflow."""
    return Path("/opt/airflow").exists()

def is_docker_environment() -> bool:
    """Detecta si estamos en Docker."""
    return Path("/.dockerenv").exists()

def get_chromedriver_path() -> str:
    """
    Busca chromedriver en ubicaciones estándar.
    
    Orden de búsqueda:
    1. Variable de entorno CHROMEDRIVER_PATH
    2. /usr/bin/chromedriver (Docker estándar)
    3. /usr/local/bin/chromedriver (macOS brew)
    4. PATH del sistema
    
    Raises:
        RuntimeError si no encuentra chromedriver
    """
    # Desde variable de entorno
    if env_path := os.getenv("CHROMEDRIVER_PATH"):
        if Path(env_path).exists():
            return env_path
    
    # Ubicaciones estándar
    standard_paths = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
    ]
    
    for path in standard_paths:
        if Path(path).exists():
            return path
    
    # PATH del sistema
    import shutil
    if path := shutil.which("chromedriver"):
        return path
    
    raise RuntimeError(
        "ChromeDriver no encontrado. "
        "Define CHROMEDRIVER_PATH o instala chromedriver en PATH"
    )

def get_chromium_binary_path() -> Optional[str]:
    """
    Busca binario de Chromium en ubicaciones estándar.
    
    Returns:
        Ruta al binario o None si no encuentra
    """
    paths = [
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chrome",
    ]
    
    for path in paths:
        if Path(path).exists():
            return path
    
    return None

def get_airflow_base_path() -> Path:
    """
    Retorna la ruta base de Airflow.
    
    Variables de entorno (en orden de prioridad):
    1. AIRFLOW_BASE_PATH
    2. AIRFLOW_HOME
    3. /opt/airflow (default)
    """
    if base := os.getenv("AIRFLOW_BASE_PATH"):
        return Path(base)
    if home := os.getenv("AIRFLOW_HOME"):
        return Path(home)
    return Path("/opt/airflow")

def get_download_path() -> Path:
    """
    Retorna ruta de descargas según el entorno.
    
    Variables de entorno:
    1. DOWNLOAD_PATH (específica)
    2. En Airflow: AIRFLOW_BASE/tmp/teleows
    3. En local: ~/Downloads/scraper_downloads
    """
    # Override explícito
    if custom := os.getenv("DOWNLOAD_PATH"):
        return Path(custom)
    
    # Entorno específico
    if is_airflow_environment():
        base = get_airflow_base_path()
        return base / "tmp" / "teleows"
    
    # Local
    return Path.home() / "Downloads" / "scraper_downloads"

def get_project_root() -> Path:
    """Retorna raíz del proyecto."""
    current = Path(__file__).resolve()
    # Subir desde: core/path_config.py → core → energiafacilities → proyectos → ROOT
    return current.parents[3]

def get_env_file_path() -> Optional[Path]:
    """
    Busca archivo .env en ubicaciones estándar.
    
    Orden:
    1. DOTENV_PATH (variable de entorno)
    2. /opt/airflow/.env (Airflow)
    3. /home/user/scraper-teleows/.env (dev)
    4. Raíz del proyecto/.env
    """
    if env_path := os.getenv("DOTENV_PATH"):
        path = Path(env_path)
        if path.exists():
            return path
    
    candidates = [
        Path("/opt/airflow") / ".env",
        get_project_root() / ".env",
    ]
    
    for path in candidates:
        if path.exists():
            return path
    
    return None
```

**Usar en DAGs:**

```python
# DAG_test_scraper.py
from energiafacilities.core.path_config import (
    get_env_file_path,
    get_project_root,
    get_download_path,
)
from dotenv import load_dotenv

# Reemplazar paths hardcodeados
env_path = get_env_file_path()
if env_path:
    load_dotenv(env_path, override=False)

sys.path.insert(0, str(get_project_root() / "proyectos"))
sys.path.insert(0, str(get_project_root() / "proyectos" / "test"))

download_path = Variable.get(
    "TEST_SCRAPER_DOWNLOAD_PATH",
    default=str(get_download_path())
)
```

### 4.2 Actualizar helpers.py

```python
# ANTES
def default_download_path() -> str:
    if Path("/opt/airflow").exists():
        return "/opt/airflow/proyectos/energiafacilities/temp"
    return str(Path.home() / "Downloads" / "scraper_downloads")

# DESPUÉS
from energiafacilities.core.path_config import get_download_path

def default_download_path() -> str:
    return str(get_download_path())
```

---

## 5. RESOLVER URLs HARDCODEADAS

### 5.1 Centralizar URLs de portales

**Crear:** `/home/user/scraper-teleows/proyectos/energiafacilities/common/portal_constants.py`

```python
"""
URLs de portales y endpoints.
"""

import os

# === PORTALES TELEOWS ===

# Base del portal (de variable de entorno o valor por defecto)
TELEOWS_BASE_URL = os.getenv(
    "TELEOWS_BASE_URL",
    "https://30c8-mx.teleows.com"
)

# Endpoints
TELEOWS_LOGIN_PATH = "/dspcas/login"
TELEOWS_SSO_PATH = "/portal/web/rest/sso/"
TELEOWS_HOMEPAGE = "/portal-web/portal/homepage.html"

def build_login_url(base_url: str = TELEOWS_BASE_URL) -> str:
    """
    Construye URL de login dinámica.
    
    Args:
        base_url: URL base del portal (default: TELEOWS_BASE_URL)
        
    Returns:
        URL completa de login con parámetros SSO
    """
    service_url = f"{base_url}{TELEOWS_SSO_PATH}index%3Fori_url%3D{base_url}{TELEOWS_HOMEPAGE}"
    login_url = f"{base_url}{TELEOWS_LOGIN_PATH}?service={service_url}"
    return login_url

# === WEBINDRA ===
WEBINDRA_BASE_URL = os.getenv(
    "WEBINDRA_BASE_URL",
    "https://recibosttr.com/sistema"
)

# === PROXIES ===
DEFAULT_PROXY = os.getenv("PROXY", "")

# Proxies por entorno (si es necesario)
PROXIES_BY_ENV = {
    "dev": os.getenv("PROXY_DEV", DEFAULT_PROXY),
    "staging": os.getenv("PROXY_STAGING", DEFAULT_PROXY),
    "prod": os.getenv("PROXY_PROD", DEFAULT_PROXY),
}
```

**Actualizar `clients/auth.py`:**

```python
from energiafacilities.common.portal_constants import build_login_url

class AuthManager:
    LOGIN_URL = build_login_url()  # Dinámico
    
    # O mejor aún:
    def __init__(self, driver, wait_timeout: int = 60) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)
        self.login_url = build_login_url()  # Por instancia
```

---

## 6. PLAN DE IMPLEMENTACIÓN (Prioridades)

### FASE 1: SEGURIDAD CRÍTICA (Inmediato)
1. Remover credenciales de archivos YAML
2. Crear `.env` con variables seguras
3. Actualizar `.gitignore`
4. Implementar interpolación de variables en `load_config()`

**Tiempo estimado:** 2-4 horas

### FASE 2: DUPLICACIÓN DE CÓDIGO (1-2 días)
1. Crear módulo `selenium_helpers.py`
2. Crear módulo `browser_constants.py`
3. Centralizar funciones de Selenium
4. Unificar sistema de login

**Tiempo estimado:** 4-6 horas

### FASE 3: CONFIGURACIÓN Y RUTAS (1-2 días)
1. Crear módulo `timing_constants.py`
2. Crear módulo `path_config.py`
3. Actualizar DAGs para usar nuevas rutas
4. Crear módulo `portal_constants.py`

**Tiempo estimado:** 4-6 horas

### FASE 4: TESTING Y VALIDACIÓN (1-2 días)
1. Ejecutar todos los DAGs
2. Verificar que los scrapers funcionan
3. Validar que no hay credenciales expuestas
4. Documentar cambios

**Tiempo estimado:** 4-8 horas

---

## CHECKLIST DE REVISIÓN POST-REMEDIACIÓN

- [ ] No hay credenciales en archivos .py o .yaml
- [ ] No hay URLs hardcodeadas fuera de constantes
- [ ] Funciones duplicadas fueron centralizadas
- [ ] Números mágicos tienen constantes documentadas
- [ ] Paths se obtienen dinámicamente
- [ ] Todos los DAGs usan variables de entorno
- [ ] `.gitignore` incluye archivos sensibles
- [ ] Ejemplo de `.env` comentado existe (sin datos reales)
- [ ] Tests pasan sin modificación
- [ ] Documentación actualizada

