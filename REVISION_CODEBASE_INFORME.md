# INFORME DE REVISIÓN EXHAUSTIVA DEL CODEBASE
## Proyecto: scraper-teleows
**Fecha:** 2025-11-19
**Directorio:** `/home/user/scraper-teleows`

---

## RESUMEN EJECUTIVO

Se han encontrado **PROBLEMAS CRÍTICOS Y GRAVES** en el codebase:
- **Credenciales hardcodeadas en archivos YAML de configuración**
- **URLs hardcodeadas** para portales
- **Código duplicado masivo** (funciones copiadas 3+ veces)
- **Números mágicos dispersos** (valores sin constantes)
- **Paths hardcodeados** (rutas absolutas)

---

## 1. CREDENCIALES Y SECRETOS HARDCODEADOS

### CRÍTICO: Credenciales en archivos de configuración YAML

#### `/home/user/scraper-teleows/proyectos/energiafacilities/config/config_dev.yaml`

| Línea | Tipo | Valor Afectado | Recomendación |
|-------|------|----------------|---------------|
| 8-12 | **PostgreSQL (DEV)** | `user: "siom_dev"` `password: "s10m#d3v"` | Mover a variables de entorno o Airflow Connection |
| 18-21 | **SFTP Energía (DEV)** | `username: "ti_etl"` `password: "0p3r4d0r#1"` | Usar .env o Airflow Connections |
| 43-47 | **SFTP DAAS (DEV)** | `username: "usr_app_daas"` `password: "Cv8mY8sK$5"` | Usar .env o Airflow Connections |
| 75-76 | **WebIndra (DEV)** | `USER: "usuario.tdp"` `PASS: "usuario.tdp2021"` | Usar variables de entorno |
| 124-125 | **Teleows Portal (DEV)** | `username: "Integratel_Data"` `password: "Integratel1!TI"` | Usar conexión Airflow o variables |

#### `/home/user/scraper-teleows/proyectos/energiafacilities/config/config_staging.yaml`

| Línea | Tipo | Valor Afectado | Problema |
|-------|------|----------------|----------|
| 8-12 | **PostgreSQL (STAGING)** | `user: "siom_test"` `password: "s10m#tst"` | Credenciales en YAML |
| 18-21 | **SFTP Energía** | `password: "0p3r4d0r#1"` | Misma contraseña que config_dev |
| 43-47 | **SFTP DAAS** | `password: "Cv8mY8sK$5"` | Misma contraseña que config_dev |
| 75-76 | **WebIndra** | `USER: "usuario.tdp"` `PASS: "usuario.tdp2021"` | Credenciales expuestas |
| 124-125 | **Teleows Portal** | `username: "Integratel_Data"` `password: "Integratel1!TI"` | Credenciales expuestas |

#### `/home/user/scraper-teleows/proyectos/energiafacilities/config/config_prod.yaml`

| Línea | Tipo | Valor Afectado | Severidad |
|-------|------|----------------|-----------|
| 18-21 | **SFTP Energía (PROD)** | `password: "0p3r4d0r#1"` | **CRÍTICO** - Credencial prod en YAML |
| 43-47 | **SFTP DAAS (PROD)** | `password: "Cv8mY8sK$5"` | **CRÍTICO** - Credencial prod en YAML |
| 75-76 | **WebIndra (PROD)** | `USER: "usuario.tdp"` `PASS: "usuario.tdp2021"` | **CRÍTICO** - Credencial prod |
| 124-125 | **Teleows Portal (PROD)** | `username: "Integratel_Data"` `password: "Integratel1!TI"` | **CRÍTICO** - Credencial prod |

**Nota:** config_prod.yaml usa `${ENV_MODE}`, `${POSTGRES_USER_PROD}`, etc. para PostgreSQL, pero SFTP y Portal están hardcodeadas.

### Credenciales en scripts de test

#### `/home/user/scraper-teleows/proyectos/test/scraper.py`

```python
Línea 28: USERNAME = os.getenv("GDE_USER", "t71522450")
Línea 29: PASSWORD = os.getenv("GDE_PASS", "R@fSh@yder199810")
Línea 30: PROXY = "telefonica01.gp.inet:8080"  # Proxy hardcoded
```

**Problema:** Aunque tiene fallback a variables de entorno, las credenciales por defecto están expuestas.

### Credenciales en ejemplos de código

#### `/home/user/scraper-teleows/proyectos/energiafacilities/core/base_postgress.py`

```python
Líneas 52-58: Ejemplo en docstring con credenciales hardcodeadas
    cfg = {
        "host": "localhost",
        "port": 5432,
        "database": "mi_db",
        "user": "admin",
        "password": "1234"
    }
```

**Problema:** Aunque es ejemplo, establece un mal precedente.

---

## 2. URLs HARDCODEADAS

### Portales web sin parametrizar

#### `/home/user/scraper-teleows/proyectos/test/scraper.py`

```python
Línea 216-218: 
login_url = (
    "https://30c8-mx.teleows.com/dspcas/login?service="
    "https://30c8-mx.teleows.com/portal/web/rest/sso/"
    "index%3Fori_url%3Dhttps%253A%252F%252F30c8-mx.teleows.com%252Fportal-web%252Fportal%252Fhomepage.html"
)
```

**Problema:** URL hardcodeada sin configuración

#### `/home/user/scraper-teleows/proyectos/energiafacilities/clients/auth.py`

```python
Línea 28-32:
LOGIN_URL = (
    "https://30c8-mx.teleows.com/dspcas/login?service="
    "https://30c8-mx.teleows.com/portal/web/rest/sso/"
    "index%3Fori_url%3Dhttps%253A%252F%252F30c8-mx.teleows.com%"
    "252Fportal-web%252Fportal%252Fhomepage.html"
)
```

**Problema:** URL duplicada y hardcodeada como clase variable

#### `/home/user/scraper-teleows/proyectos/energiafacilities/config/config_dev.yaml`
```yaml
Línea 72: BASE_URL: "https://recibosttr.com/sistema"
Línea 80: PROXY: "telefonica01.gp.inet:8080"
Línea 133: proxy: "telefonica01.gp.inet:8080"
```

**Problema:** Proxies hardcodeados en YAML

---

## 3. CÓDIGO DUPLICADO MASIVO

### Función: `robust_click` / `_robust_click`

**Definida en 3 lugares diferentes:**

1. **scraper.py (líneas 96-114)**
   ```python
   def robust_click(driver, elem):
       """Intenta click con varias estrategias."""
   ```

2. **autin_gde/stractor.py (líneas 272-289)**
   ```python
   def _robust_click(driver, elem):
       """Intenta click con varias estrategias (igual que en test.py)."""
   ```

3. **date_filter_manager.py (línea 452)**
   ```python
   def _robust_click_element(self, element: WebElement) -> bool:
       """Intenta click con varias estrategias (igual que robust_click de scraper.py)."""
   ```

**Recomendación:** Extraer a `common/selenium_utils.py` o `clients/selenium_helpers.py`

### Función: `switch_to_frame_with` / `_switch_to_frame_with`

**Definida en 2 lugares:**

1. **scraper.py (líneas 62-93)**
   ```python
   def switch_to_frame_with(driver, css_or_xpath):
   ```

2. **autin_gde/stractor.py (líneas 292-315)**
   ```python
   def _switch_to_frame_with(driver, css_or_xpath: str) -> bool:
   ```

**Nota:** Los comentarios en autin_gde/stractor.py indican explícitamente: "Replica la utilidad usada en test.py"

**Recomendación:** Centralizar en módulo de utilidades compartidas

### Función: `find_first`

**Definida en:**
1. **scraper.py (líneas 117-130)**
   ```python
   def find_first(driver, selectors):
       """Dada una lista de selectores, retorna el primer elemento encontrado."""
   ```

**Ubicación:** No encontrada en otros lugares, pero debería ser reutilizable

### Función: `do_login_robusto` vs `AuthManager.login()`

**Dos implementaciones de login:**

1. **scraper.py (línea 211)**
   ```python
   def do_login_robusto(driver, wait, ruta_descarga):
   ```

2. **clients/auth.py (línea 40)**
   ```python
   def login(self, username: str, password: str) -> bool:
   ```

**Problema:** Lógica de login duplicada. La clase `AuthManager` es la versión mejorada pero scraper.py sigue usando la función antigua.

---

## 4. NÚMEROS MÁGICOS SIN CONSTANTES

### Sleep/Timeout values dispersos

#### scraper.py
```
Línea 33:   max_intentosf = 120
Línea 59:   max_intentosC = 60
Línea 106:  time.sleep(0.2)
Línea 395:  sleep(2)
Línea 401:  sleep(2)
Línea 444:  sleep(1)
Línea 462:  sleep(0.3)
Línea 482:  time.sleep(1)
Línea 551:  time.sleep(0.5)
Línea 561:  time.sleep(1)
Línea 684:  sleep(3)       # Comentado: "Esperar que se actualice la tabla"
Línea 690:  sleep(10)
Línea 718:  sleep(10)
Línea 722:  sleep(10)
Línea 727:  sleep(10)
Línea 768:  timeout = 60   # Comentado: "Esperar máximo 60 segundos"
```

**Problema:** Valores inconsistentes sin explicación clara

#### autin_gde/stractor.py (PARCIALMENTE MEJORADO)
```python
Línea 73-77: DELAY_SHORT = 0.1
Línea 73-77: DELAY_MEDIUM = 0.2
Línea 73-77: DELAY_NORMAL = 0.3
Línea 73-77: DELAY_LONG = 1.0
Línea 73-77: DELAY_VERY_LONG = 2.0
```

**Buena práctica:** Constantes definidas, pero scraper.py no las usa

#### clients/date_filter_manager.py
```
Línea 110:  sleep(1.5)    # Comentado: "Esperar un poco más para que el popper se cierre"
Línea 126:  sleep(0.2)
Línea 136:  sleep(1)      # Comentado: "Igual que scraper.py línea 581"
Línea 235:  sleep(0.3)
Línea 242:  sleep(1)
Línea 267:  sleep(0.1)
```

### WebDriverWait timeouts

```
browser.py línea 28:        wait_timeout: int = 20
auth.py línea 36:           wait_timeout: int = 60
selenium_utils.py línea 38: timeout: int = 8
autin_gde/stractor.py:      wait = WebDriverWait(driver, 15)
autin_gde/stractor.py:      wait = WebDriverWait(driver, 5)
autin_gde/stractor.py:      wait = WebDriverWait(driver, 12)
autin_gde/stractor.py:      wait = WebDriverWait(driver, 3)
```

**Problema:** Valores inconsistentes, algunos duplicados

### Intentos/Retries

```
scraper.py línea 33:  max_intentosf = 120        # Para iframe de filtros
scraper.py línea 59:  max_intentosC = 60         # Para verificar estado
```

**Problema:** Nombres poco claros, no documentados por qué esos valores específicos

---

## 5. PATHS HARDCODEADOS (Rutas Absolutas)

### Paths del sistema

#### scraper.py
```python
Línea 176: if os.path.exists("/usr/bin/chromium")
Línea 183: options.binary_location = "/usr/bin/chromium"
Línea 188: if os.path.exists("/usr/bin/chromedriver")
Línea 191: elif os.path.exists("/usr/local/bin/chromedriver")
```

#### clients/browser.py (CÓDIGO DUPLICADO)
```python
Línea 112: if os.path.exists("/usr/bin/chromium")
Línea 119: options.binary_location = "/usr/bin/chromium"
Línea 123: if os.path.exists("/usr/bin/chromedriver")
Línea 126: elif os.path.exists("/usr/local/bin/chromedriver")
```

### Airflow paths

#### DAGs
```python
DAG_test_scraper.py línea 17:  env_path = Path("/opt/airflow/.env")
DAG_test_scraper.py línea 25:  sys.path.insert(0, "/opt/airflow/proyectos")
DAG_test_scraper.py línea 26:  sys.path.insert(0, "/opt/airflow/proyectos/test")
DAG_test_scraper.py línea 77:  default="/opt/airflow/tmp/test_scraper"
DAG_webindra.py línea 9:       sys.path.insert(0, "/opt/airflow/proyectos/energiafacilities")
DAG_sftp_energia.py línea 9:   sys.path.insert(0, "/opt/airflow/proyectos/energiafacilities")
DAG_clientes_libres.py línea 9-10: sys.path.insert(0, "/opt/airflow/proyectos")
DAG_dynamic_checklist.py línea 16: sys.path.insert(0, "/opt/airflow/proyectos")
```

**Problema:** Paths hardcodeados en múltiples DAGs, difícil de cambiar si la estructura cambia

#### helpers.py
```python
Línea 279-280: default_download_path()
    if Path("/opt/airflow").exists():
        return "/opt/airflow/proyectos/energiafacilities/temp"
    return str(Path.home() / "Downloads" / "scraper_downloads")
```

**Problema:** Path de Airflow hardcodeado

---

## 6. PATRONES Y SELECTORES DUPLICADOS

### XPaths hardcodeados

#### scraper.py
```python
Línea 447: '//*[@id="allTask_tab"]/form/div[2]/div/div/div[2]/button[2]'
Línea 459: f"//li[contains(@class, 'el-select-dropdown__item') and @title='{opcion}']"
```

#### autin_gde/stractor.py (CÓDIGO DUPLICADO)
```python
Línea 330: '//*[@id="allTask_tab"]/form/div[2]/div/div/div[2]/button[2]'  # IDÉNTICO
Línea 348: f"//li[contains(@class, 'el-select-dropdown__item') and @title='{option}']"
```

**Problema:** XPaths idénticos en dos archivos, cambiados solo nombres de variables

### Constants mejor organizadas

#### dynamic_checklist_constants.py (BUEN EJEMPLO)
```python
Línea 58-63: XPaths definidos como constantes
    XPATH_SPLITBUTTON_BY_TEXT = "//span[@class='sdm_splitbutton_text' and contains(text(),'{text}')]"
    XPATH_PAGINATION_TOTAL = "//span[@class='el-pagination__total' and contains(text(),'Total')]"
    XPATH_LOADING_MASK = "//div[contains(@class,'el-loading-mask')]"
```

**Recomendación:** Crear similar para GDE (gde_constants.py)

---

## 7. CONFIGURACIÓN Y VARIABLES DE ENTORNO

### Falta de abstracción en config

#### Configuración tiene hardcodes
```yaml
config_dev.yaml:  proxy: "telefonica01.gp.inet:8080"
config_staging.yaml: proxy: "telefonica01.gp.inet:8080"  
config_prod.yaml: proxy: "telefonica01.gp.inet:8080"
```

**Problema:** Mismo proxy en todos los ambientes, debería estar centralizado

#### Falta consistencia en nombres
```yaml
teleows:
  proxy: "..."
webindra_energia:
  PROXY: "..."
sftp_energia_c:
  (sin proxy, se asume de env)
```

**Problema:** Nombres inconsistentes para misma configuración

---

## 8. DUPLICACIÓN EN MANAGERS

### BrowserManager duplica código de scraper.py

El archivo `clients/browser.py` tiene la función `setup_chrome_options()` que es casi idéntica a la configuración en `scraper.py` (líneas 142-164).

```python
# Ambos hacen:
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--lang=es-ES")
prefs["intl.accept_languages"] = "es-ES,es"
# ... etc
```

Los comentarios en browser.py indican:
```python
# Configurar EXACTAMENTE igual que scraper.py líneas 152-157
# SOLO --lang=es-ES (igual que scraper.py línea 152)
# Configurar EXACTAMENTE igual que scraper.py línea 157
```

---

## RESUMEN DE PROBLEMAS POR SEVERIDAD

### CRÍTICO (Seguridad)
1. Credenciales hardcodeadas en YAML (config_dev.yaml, config_staging.yaml, config_prod.yaml)
2. Contraseñas en scraper.py como fallback (línea 29)
3. URLs de portales expuestas sin configuración

### ALTO (Código Quality)
1. Código duplicado en 3+ lugares (robust_click, switch_to_frame_with)
2. Paths hardcodeados en múltiples DAGs
3. Números mágicos dispersos sin constantes

### MEDIO (Mantenibilidad)
1. Inconsistencia en nombres de configuración
2. XPaths duplicados entre archivos
3. Dos sistemas de login (function vs class)

### BAJO (Best Practices)
1. Ejemplos de código con credenciales mock
2. Comentarios que dicen "igual que scraper.py línea XXX"

