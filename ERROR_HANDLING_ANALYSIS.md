# Análisis Exhaustivo del Manejo de Errores - scraper-teleows

## Resumen Ejecutivo
Se encontraron **múltiples patrones problemáticos** en el manejo de errores distribuidos en **10+ archivos Python**. Los principales problemas son:
- **9 excepciones vacías con `pass`** (silenciadas)
- **40+ excepciones genéricas** (`Exception`, `BaseException`)
- **Logging inconsistente** en manejo de errores
- **Retornos implícitos de None** en funciones
- **Falta de validación** de inputs en varios módulos

---

## PROBLEMAS CRÍTICOS ENCONTRADOS

### 1. EXCEPCIONES SILENCIADAS CON `pass` (Severidad: ALTA)

#### Archivo: `/home/user/scraper-teleows/proyectos/test/scraper.py`

| Línea | Problema | Impacto | Solución |
|-------|----------|---------|----------|
| 75-76 | `except: pass` en `switch_to_frame_with()` | Silencia errores de búsqueda de elementos. No se sabe si falló. | Log del error y retornar False explícitamente |
| 89-90 | `except: continue` en búsqueda de iframes | Iframes no encontrados sin notificación | Agregar logger.debug() |
| 103-114 | `except: try/except anidados` sin logs | Múltiples reintentos sin visibilidad | Loguear cada intento |
| 128-129 | `except: continue` en find_first() | Selector no encontrado sin registro | Loguear selectores no encontrados |
| 247-248 | `except: pass` en cierre de cookies | Error silenciado | Loguear el cierre de overlays |
| 307-311 | `except: pass` en búsqueda de form | Form no encontrado sin notificación | Loguear intentos fallidos |

**Código problemático (línea 75-76):**
```python
try:
    if css_or_xpath.startswith("//"):
        driver.find_element(By.XPATH, css_or_xpath)
    else:
        driver.find_element(By.CSS_SELECTOR, css_or_xpath)
    return True
except:  # ← PROBLEMA: Excepto desnudo
    pass   # ← PROBLEMA: Silencia el error
```

**Impacto Potencial:**
- Elementos no encontrados sin registro
- Debugging difícil durante fallos
- No se puede auditar qué selectores fallan
- Posible ocultar problemas de cambios en DOM

**Sugerencia de Mejora:**
```python
try:
    locator = (By.XPATH, css_or_xpath) if css_or_xpath.startswith("//") else (By.CSS_SELECTOR, css_or_xpath)
    driver.find_element(*locator)
    return True
except NoSuchElementException:
    logger.debug("Elemento no encontrado con selector: %s", css_or_xpath)
    return False
except Exception as e:
    logger.warning("Error inesperado al buscar elemento: %s", e)
    return False
```

---

### 2. EXCEPCIONES GENÉRICAS SIN CONTEXTO (Severidad: ALTA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/date_filter_manager.py`

**Ubicaciones con `except Exception:`:**
- Línea 166: En búsqueda de "Create time" row
- Línea 182: Al abrir botón "+"
- Línea 210: Fallback de búsqueda de input
- Línea 217: Intento de XPath original
- Línea 237: Cerrar poppers abiertos
- Línea 265-267: Espera de picker visible
- Línea 283-284: Búsqueda de input de fecha
- Línea 334-336: Espera de input de hora
- Línea 359-360: Manejo de excepciones en COMMAND
- Línea 404-405: Búsqueda de botón "Confirmar"
- Línea 446-447: Cierre de poppers

**Línea 166-167 (Ejemplo):**
```python
try:
    all_rows = self.driver.find_elements(By.CSS_SELECTOR, '.el-row.ows_filter_row, .ows_filter_row')
    for row in all_rows:
        row_text = row.text or ""
        if "Create time" in row_text or "Create Time" in row_text:
            create_time_row = row
            break
except Exception:  # ← PROBLEMA: Demasiado genérica
    pass           # ← Silencia el error
```

**Impacto:** 
- No se sabe si falló por timeout, elemento no encontrado, o StaleElement
- Log vacío para debugging
- Difícil reproducir problemas

**Sugerencia:**
```python
try:
    all_rows = self.driver.find_elements(By.CSS_SELECTOR, '.el-row.ows_filter_row, .ows_filter_row')
    for row in all_rows:
        row_text = row.text or ""
        if "Create time" in row_text or "Create Time" in row_text:
            create_time_row = row
            logger.debug("Create time row encontrado")
            break
except TimeoutException:
    logger.warning("Timeout esperando elementos de Create time")
except StaleElementReferenceException:
    logger.warning("Elemento se volvió stale, reintentando...")
except Exception as e:
    logger.error("Error inesperado buscando Create time row: %s", e, exc_info=True)
```

---

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/sources/autin_gde/stractor.py`

**Múltiples `except Exception:` sin logging:**
- Línea 277, 283, 287, 300, 310, 373, 439, 464, 578

**Línea 277 (Ejemplo):**
```python
try:
    # proceso complejo
    pass
except Exception:  # ← Demasiado genérica, sin logs
    # manejo vago
    pass
```

---

#### Archivo: `/home/user/scraper-teleows/dags/DAG_dynamic_checklist_test_loader.py`

**Línea 111-112:**
```python
except Exception:  # ← Exception genérica
    pass            # ← Silencia completamente
```

**Impacto:**
- Errores de búsqueda de variables no se registran
- Posibles KeyErrors u otros errores silenciados

**Sugerencia:**
```python
try:
    file_path = Variable.get("DYNAMIC_CHECKLIST_TEST_FILE", default=None)
    if file_path:
        logger.info("Usando archivo desde Variable: %s", file_path)
        file_path = str(file_path).strip()
except KeyError:
    logger.debug("Variable DYNAMIC_CHECKLIST_TEST_FILE no existe")
except Exception as e:
    logger.warning("Error obteniendo Variable: %s", e)
```

---

### 3. LOGGING INADECUADO - Excepciones No Registradas (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/filters.py`

**Línea 34-48:**
```python
except Exception:  # ← No hay logging específico
    logger.warning(
        "Texto 'Opciones de filtrado' no encontrado, pero el ícono de filtro sí está presente"
    )
# ...
except Exception as exc:
    # Aquí sí hay logging
    message = f"Error al preparar filtros: {exc}"
    logger.error("%s", message, exc_info=True)
```

**Inconsistencia:** Algunos bloques tienen logging detallado, otros no.

---

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/auth.py`

**Línea 122-123:**
```python
except Exception:
    body_text = ""  # ← Silencia error, no hay logging
```

**Línea 138-139:**
```python
except Exception:
    return False  # ← No hay logging del error
```

**Impacto:** Errores de extracción de mensajes no se registran.

**Sugerencia:**
```python
try:
    body_text = self.driver.execute_script("return document.body.innerText || ''")
except TimeoutException:
    logger.debug("Timeout obteniendo texto del body")
    body_text = ""
except Exception as e:
    logger.debug("Error obteniendo body text: %s", e)
    body_text = ""
```

---

### 4. RETORNOS INCONSISTENTES (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/date_filter_manager.py`

**Línea 166-184:**
```python
def _click_y_setear_fecha_y_hora(self, container_xpath: str, fecha: str, hora: str) -> None:
    # ...
    try:
        all_rows = self.driver.find_elements(By.CSS_SELECTOR, '.el-row.ows_filter_row')
        # ...
    except Exception:
        pass  # ← Retorna implícitamente None
```

**Problema:** La función especifica retorno `-> None`, pero:
- A veces raise RuntimeError
- A veces continúa con lógica
- Inconsistencia en flujo de control

**Línea 452-535:**
```python
def _robust_click_element(self, element: WebElement) -> bool:
    try:
        element.click()
        return True  # ← Path exitoso
    except Exception:
        try:
            # ... intento alternativo
            return True
        except Exception:
            try:
                # ... tercer intento
                return True
            except Exception:
                return False  # ← Único path que retorna False
```

**Mejor patrón:** Usar variable de estado en lugar de retornar en múltiples puntos.

---

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/log_management_manager.py`

**Línea 122-124:**
```python
except Exception:
    # El cierre no es crítico, pero dejamos registro si falla.
    logger.debug("No se pudo cerrar el mensaje", exc_info=True)
    # ← NO hay retorno, método retorna None implícitamente
```

**Línea 171-173:**
```python
except Exception:
    logger.debug("Error al presionar Refresh", exc_info=True)
    # ← Método continúa sin retorna nada
```

**Problema:** No está claro si es intencional retornar None o un error de diseño.

**Sugerencia de tipo hint:**
```python
def close_export_prompt(self) -> bool:
    """Intenta cerrar el modal de advertencia. Retorna True si éxito, False si no."""
    try:
        close_button = self.wait.until(...)
        close_button.click()
        logger.debug("Mensaje de información cerrado")
        return True  # ← Explícito
    except Exception:
        logger.debug("No se pudo cerrar el mensaje", exc_info=True)
        return False  # ← Explícito
```

---

### 5. FALTA DE VALIDACIÓN DE INPUTS (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/clients/auth.py`

**Línea 40-86:**
```python
def login(self, username: str, password: str) -> bool:
    # ← NO VALIDA que username y password no sean vacíos
    try:
        logger.debug("Iniciando proceso de login")
        self.driver.get(self.LOGIN_URL)
        
        username_field = self.wait.until(...)
        username_field.send_keys(username)  # ← Si username es None/vacío, continuará
```

**Sugerencia:**
```python
def login(self, username: str, password: str) -> bool:
    if not username or not password:
        raise ValueError("username y password no pueden estar vacíos")
    
    if not isinstance(username, str) or not isinstance(password, str):
        raise TypeError("username y password deben ser strings")
    
    try:
        # ... resto del código
```

---

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/core/base_loader.py`

**Línea 110:**
```python
def verificar_datos(self, data: Any, column_mapping: Optional[Dict[str, str]] = None, 
                    sheet_name: str = 0, strictreview=True, numerofilasalto: int =0, 
                    table_name:str =None):
    # ← NO VALIDA que table_name sea proporcionado cuando es necesario
    
    # Línea 174:
    cur.execute(..., (self._cfgload.schema, table_name or self._cfgload.table))
    # ← Si table_name es None Y self._cfgload.table no existe, falla sin mensaje claro
```

**Sugerencia:**
```python
def verificar_datos(self, data: Any, table_name: str | None = None, ...):
    # Validar parámetros requeridos
    if table_name is None:
        table_name = getattr(self._cfgload, 'table', None)
    
    if not table_name:
        raise ValueError("table_name es requerido (ni en parámetro ni en config)")
    
    if not isinstance(data, (pd.DataFrame, str)):
        raise TypeError("data debe ser DataFrame, ruta Excel o CSV")
```

---

### 6. ERRORES NO PROPAGADOS (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/core/utils.py`

**Línea 134-136:**
```python
except Exception:
    # Si no existe esta Connection, intentar la siguiente
    continue  # ← Silencia excepciones legítimas
```

**Línea 232-250:**
```python
except ValueError as e:
    # Si falla por nombre de hoja, listar las hojas disponibles
    if "Worksheet named" in str(e) or "not found" in str(e).lower():
        try:
            # ... intentar leer hojas
            logger.error(error_msg)
            raise ValueError(error_msg) from e  # ← RE-LANZA con contexto
        except Exception:
            # Si no podemos leer el Excel, lanzar el error original
            raise  # ← Re-lanza implícitamente
    else:
        raise
```

**Problema:** En línea 246-248, hay inconsistencia:
```python
except Exception:
    # Si no podemos leer el Excel, lanzar el error original
    raise  # ← ¿Pero cuál? ¿El original o el de lectura?
```

**Mejor pattern:**
```python
original_error = None
try:
    # ...
    xl_file = pd.ExcelFile(data, engine='openpyxl')
except Exception as original_error:
    logger.error("No se pudo leer hojas del Excel", exc_info=True)
    raise ValueError(f"No se pudo leer archivo Excel {data}") from original_error
```

---

### 7. EXCEPCIONES GENÉRICAS EN FUNCIONES CRÍTICAS (Severidad: ALTA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/sources/clientes_libres/help/transform_helpers.py`

**Línea 63, 114, 238:**
```python
try:
    # ... transformación
except Exception:  # ← Línea 238: Demasiado genérica
    logger.exception("Error crítico durante la transformación del Excel.")
    raise  # ← Al menos re-lanza, pero sin contexto específico
```

**Línea 230-232:**
```python
except Exception as e:
    logger.error(f"No se pudo crear el directorio {pathcrear}: {e}")
    raise  # ← Re-lanza genérica
```

**Mejor sería:**
```python
except PermissionError:
    logger.error(f"Permiso denegado para crear {pathcrear}")
    raise
except FileExistsError:
    logger.warning(f"Directorio ya existe: {pathcrear}")
except OSError as e:
    logger.error(f"Error del SO creando directorio: {e}")
    raise
```

---

### 8. TIPOS NO VALIDADOS (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/core/base_exporters.py`

**Línea 63-87:**
```python
def export_dataframe(
    self,
    df: pd.DataFrame,
    destination_path: str,
    index: bool = False,
    target_tz: str = "America/Lima"
) -> str:
    try:
        # Validaciones (BIEN)
        if not isinstance(df, pd.DataFrame):
            logger.error("El parámetro 'df' no es un DataFrame.")
            raise TypeError("El parámetro 'df' debe ser un DataFrame")

        # ...
        # PERO Línea 136-138: No hay validación del resultado
        except Exception as e:
            logger.error(f" Error exportando DataFrame: {e}", exc_info=True)
            raise  # ← Re-lanza OK
```

**Mejora:** Validar destination_path tiene extensión válida ANTES de intentar.

---

### 9. INCONSISTENCIA EN MANEJO AIRFLOW (Severidad: MEDIA)

#### Archivo: `/home/user/scraper-teleows/proyectos/energiafacilities/core/utils.py`

**Línea 49-62:**
```python
def _get_env_from_airflow() -> Optional[str]:
    if not _is_airflow_available():
        return None
    
    try:
        from airflow.sdk import Variable
        try:
            env = Variable.get("ENV_MODE")
            if env:
                logger.debug(f"ENV_MODE obtenido desde Airflow Variable: {env}")
                return env
        except KeyError:  # ← BIEN: Captura KeyError específico
            logger.debug("Variable ENV_MODE no existe en Airflow")
    except Exception as exc:  # ← GENÉRICA: Para el import
        logger.debug(f"No se pudo obtener ENV_MODE desde Airflow: {exc}")
    
    return None
```

**Mejor:**
```python
try:
    from airflow.sdk import Variable
except ImportError:
    logger.debug("Airflow SDK no disponible")
    return None

try:
    env = Variable.get("ENV_MODE")
    if env:
        logger.debug(f"ENV_MODE: {env}")
        return env
except KeyError:
    logger.debug("Variable ENV_MODE no existe")
except Exception as e:
    logger.warning(f"Error obteniendo ENV_MODE: {e}")

return None
```

---

## TABLA RESUMEN: PROBLEMAS POR SEVERIDAD

| Severidad | Tipo | Cantidad | Archivos | Acción |
|-----------|------|----------|----------|--------|
| **CRÍTICA** | `except: pass` | 6 | scraper.py | Agregar logging inmediato |
| **ALTA** | `except Exception:` genérica | 40+ | 8 archivos | Especificar excepciones esperadas |
| **ALTA** | Excepciones silenciadas | 15+ | auth.py, filters.py, log_management.py | Agregar logger en todos los except |
| **MEDIA** | Retornos inconsistentes | 8 | date_filter_manager.py, base_loader.py | Estandarizar con type hints |
| **MEDIA** | Falta validación inputs | 5 | auth.py, base_loader.py | Validar al inicio de funciones |
| **MEDIA** | Errores no propagados | 4 | utils.py, transform_helpers.py | Re-lanzar con contexto |
| **BAJA** | Logging redundante | 2 | filters.py | Consolidar messages |

---

## RECOMENDACIONES GLOBALES

### 1. Crear base exception classes
```python
# core/exceptions.py
class TeleowsError(Exception):
    """Base para todas las excepciones del proyecto."""
    pass

class FrameNotFoundError(TeleowsError):
    """Iframe no encontrado en el DOM."""
    pass

class FilterApplicationError(TeleowsError):
    """Error al aplicar filtros."""
    pass

class LoginError(TeleowsError):
    """Error durante autenticación."""
    pass
```

### 2. Standarizar logging en excepciones
```python
# Pattern: SIEMPRE loguear excepciones
try:
    # ... código
except SpecificException as e:
    logger.warning("Mensaje específico del error", exc_info=True)
    raise  # o manejar según el caso
except Exception as e:
    logger.error("Error inesperado", exc_info=True)
    raise
```

### 3. Validar inputs temprano
```python
# En cada función con parámetros externos:
def process(data: Any, table_name: str | None = None):
    # Validar inmediatamente
    if not data:
        raise ValueError("data no puede ser vacío")
    if table_name is not None and not isinstance(table_name, str):
        raise TypeError("table_name debe ser string")
```

### 4. Documentar políticas de error
Agregar docstring con excepciones esperadas:
```python
def login(self, username: str, password: str) -> bool:
    """
    Realiza login al portal.
    
    Args:
        username: Credencial de usuario
        password: Credencial de acceso
        
    Returns:
        True si login exitoso, False en caso contrario
        
    Raises:
        ValueError: Si username/password están vacíos
        RuntimeError: Si la autenticación falla después de reintentos
    """
```

---

## ARCHIVOS A PRIORIZAR

1. **`proyectos/test/scraper.py`** - Múltiples `except: pass` críticos
2. **`proyectos/energiafacilities/clients/date_filter_manager.py`** - 11+ excepciones genéricas
3. **`proyectos/energiafacilities/clients/auth.py`** - Excepciones silenciadas en login
4. **`proyectos/energiafacilities/core/base_loader.py`** - Falta validación de inputs
5. **`proyectos/energiafacilities/sources/autin_gde/stractor.py`** - Múltiples excepciones no registradas

---

## CHECKLIST PARA REMEDIAR

- [ ] Agregar logging a todos los `except:` y `except Exception:`
- [ ] Especificar tipos de excepción en lugar de genéricos
- [ ] Remover todos los `except: pass` desnudos
- [ ] Agregar validación de inputs en funciones públicas
- [ ] Documentar política de excepciones con Raises en docstrings
- [ ] Crear base exception class para el proyecto
- [ ] Estandarizar type hints para retornos (especialmente None)
- [ ] Agregar tests de manejo de errores
- [ ] Revisar logs en QA para excepciones inesperadas

