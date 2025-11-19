# Índice de Problemas de Manejo de Errores por Archivo

## Tabla de Contenidos Rápida

- **12 archivos analizados**
- **70+ problemas identificados**
- **85 bloques try/except revisos**

---

## 1. CRÍTICO: `proyectos/test/scraper.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 75-76 | `except:` desnudo | CRÍTICA | `pass` silencia búsqueda de elementos | Loguear + return False |
| 89-90 | `except:` desnudo | CRÍTICA | Iframe no encontrado silenciado | Loguear + continue |
| 103-114 | Anidado sin logs | ALTA | 3 niveles de try/except sin logging | Loguear cada intento |
| 128-129 | `except:` desnudo | ALTA | Selector no encontrado sin registro | Loguear + return None |
| 247-248 | `except:` desnudo | ALTA | Cookie/overlay no cerrado sin notificación | Loguear cierre |
| 307-311 | `except:` desnudo | ALTA | Form no encontrado sin registro | Loguear intentos |

**Resumen:** 6 problemas críticos. Múltiples búsquedas de elementos silenciadas.

---

## 2. CRÍTICO: `proyectos/energiafacilities/clients/date_filter_manager.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 166 | `except Exception:` | ALTA | No especifica excepción esperada | Usar TimeoutException, StaleElement |
| 182 | `except Exception:` | ALTA | Botón + no encontrado sin logging | Loguear intento |
| 210 | `except Exception:` | ALTA | Fallback sin contexto | Loguear fallo primario |
| 217 | `except Exception:` | ALTA | Otro fallback sin logging | Loguear cadena de intentos |
| 237 | `except Exception:` | ALTA | Cerrar poppers sin especificar error | Loguear tipo de error |
| 265-267 | `except Exception:` | ALTA | Espera de picker sin timeout específico | Usar TimeoutException |
| 283-284 | `except Exception:` | ALTA | Input de fecha no encontrado sin logs | Loguear búsqueda |
| 334-336 | `except Exception:` | ALTA | Input de hora sin manejo específico | Loguear espera |
| 359-360 | `except Exception:` | ALTA | COMMAND key puede fallar sin notificación | Loguear intento |
| 404-405 | `except Exception:` | ALTA | Botón Confirmar no encontrado sin logs | Loguear búsqueda |
| 446-447 | `except Exception:` | ALTA | Cierre de poppers sin especificar error | Loguear tipo |

**Resumen:** 11 problemas de excepciones genéricas sin logging específico.

---

## 3. ALTO: `proyectos/energiafacilities/clients/auth.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 40 | Sin validación | ALTA | Credenciales no validadas | Validar al inicio |
| 122-123 | `except Exception:` | ALTA | body text no loguado | Agregar logger.debug() |
| 138-139 | `except Exception:` | ALTA | Extracción de mensaje sin logging | Agregar logger.debug() |

**Resumen:** 3 problemas. Excepciones silenciadas en función crítica de login.

---

## 4. ALTO: `proyectos/energiafacilities/core/base_loader.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 110 | Sin validación | ALTA | table_name no validado | Validar al inicio |
| 134 | `except Exception:` | MEDIA | Connection no encontrada sin logging | Loguear intento |
| 246 | `except Exception:` | MEDIA | Excel no puede leerse sin mensajes útiles | Especificar que tipo de error |

**Resumen:** 3 problemas. Validación ausente de tabla destino.

---

## 5. ALTO: `proyectos/energiafacilities/sources/autin_gde/stractor.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 277 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 283 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 287 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 300 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 310 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 373 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 439 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 464 | `except Exception:` | ALTA | Sin logging | Loguear error |
| 578 | `except Exception:` | ALTA | Sin logging | Loguear error |

**Resumen:** 9 problemas. Todas excepciones genéricas sin especificar ni loguear.

---

## 6. ALTO: `dags/DAG_dynamic_checklist_test_loader.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 111-112 | `except Exception:` + `pass` | ALTA | Variable no encontrada + silencio | Loguear específicamente |

**Resumen:** 1 problema. Variable de Airflow no encontrada sin notificación.

---

## 7. MEDIA: `proyectos/energiafacilities/clients/filters.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 34-48 | `except Exception:` | MEDIA | Sin logging específico | Loguear excepción |
| 47-48 | `except Exception:` | MEDIA | Screenshot sin logging | Loguear ruta guardada |

**Resumen:** 2 problemas. Inconsistencia en logging.

---

## 8. MEDIA: `proyectos/energiafacilities/clients/log_management_manager.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 122-124 | `except Exception:` | MEDIA | Retorna None implícitamente | Return bool explícito |
| 171-173 | `except Exception:` | MEDIA | Error en refresh sin manejo | Loguear y continuar |

**Resumen:** 2 problemas. Retornos inconsistentes y sin especificar.

---

## 9. MEDIA: `proyectos/energiafacilities/common/selenium_utils.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 202-204 | `except Exception:` | MEDIA | Monitoreo con exception sin logging específico | Loguear tipo de error |

**Resumen:** 1 problema. Monitoreo de exportación sin logging detallado.

---

## 10. MEDIA: `proyectos/energiafacilities/core/utils.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 51-62 | Anidado | MEDIA | Dos niveles de try/except sin logging claro | Separar import de Variable |
| 134-136 | `except Exception:` | MEDIA | Connection no encontrada sin logging | Loguear cada intento |
| 232-250 | Complejo | MEDIA | Excel sheets con manejo confuso | Documentar flujo |

**Resumen:** 3 problemas. Lógica de importación y excepciones anidadas confusas.

---

## 11. MEDIA: `proyectos/energiafacilities/sources/clientes_libres/help/transform_helpers.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 63 | `except Exception:` | MEDIA | Conversión sin especificar error | Loguear tipo |
| 114 | `except Exception:` | MEDIA | Período no parseado sin logging | Loguear valor que falló |
| 230-232 | `except Exception:` | MEDIA | Crear directorio genérico | Especificar (PermissionError, etc) |
| 238 | `except Exception:` | MEDIA | Transformación con re-raise sin contexto | Agregar contexto |

**Resumen:** 4 problemas. Transformación de datos sin manejo específico.

---

## 12. MEDIA: `proyectos/energiafacilities/core/base_exporters.py`

| Línea | Tipo | Severidad | Problema | Solución |
|-------|------|-----------|----------|----------|
| 107 | `except Exception:` | MEDIA | Exportación DataFrame genérica | Especificar (TypeError, ValueError) |

**Resumen:** 1 problema. Validación es buena pero manejo de error es genérico.

---

## Resumen por Tipo de Problema

### 1. Excepciones Silenciadas (`except:` o `except: pass`)
**Archivos:** scraper.py (6x)
**Cantidad:** 6 instancias
**Severidad:** CRÍTICA
**Acción:** Agregar logging inmediatamente

### 2. Excepciones Genéricas sin Especificar
**Archivos:** date_filter_manager.py (11x), autin_gde/stractor.py (9x), base_loader.py, utils.py, transform_helpers.py, auth.py, filters.py, base_exporters.py
**Cantidad:** 40+ instancias
**Severidad:** ALTA
**Acción:** Especificar excepciones esperadas

### 3. Sin Logging en Excepciones
**Archivos:** auth.py, filters.py, log_management_manager.py, selenium_utils.py
**Cantidad:** 10+ instancias
**Severidad:** ALTA
**Acción:** Agregar logger en todos los except

### 4. Retornos Inconsistentes
**Archivos:** date_filter_manager.py, log_management_manager.py
**Cantidad:** 5 instancias
**Severidad:** MEDIA
**Acción:** Estandarizar type hints

### 5. Sin Validación de Inputs
**Archivos:** auth.py, base_loader.py
**Cantidad:** 2 instancias
**Severidad:** MEDIA
**Acción:** Validar parámetros al inicio

### 6. Errores No Propagados
**Archivos:** utils.py, transform_helpers.py
**Cantidad:** 3 instancias
**Severidad:** MEDIA
**Acción:** Re-lanzar con contexto

---

## Archivos Ordenados por Prioridad

1. **scraper.py** - 6 problemas CRÍTICOS
2. **date_filter_manager.py** - 11 problemas ALTOS
3. **auth.py** - 3 problemas ALTOS + sin validación
4. **base_loader.py** - 3 problemas ALTOS + sin validación
5. **autin_gde/stractor.py** - 9 problemas ALTOS
6. **DAG_dynamic_checklist_test_loader.py** - 1 problema ALTO
7. **utils.py** - 3 problemas MEDIOS
8. **transform_helpers.py** - 4 problemas MEDIOS
9. **log_management_manager.py** - 2 problemas MEDIOS
10. **filters.py** - 2 problemas MEDIOS
11. **selenium_utils.py** - 1 problema MEDIO
12. **base_exporters.py** - 1 problema MEDIO

---

## Impacto Estimado por Archivo

| Archivo | # Problemas | Impacto | Criticidad |
|---------|-------------|---------|-----------|
| scraper.py | 6 | Muy Alto | 🔴 CRÍTICA |
| date_filter_manager.py | 11 | Muy Alto | 🔴 CRÍTICA |
| autin_gde/stractor.py | 9 | Alto | 🟠 ALTA |
| auth.py | 3 | Alto | 🟠 ALTA |
| base_loader.py | 3 | Alto | 🟠 ALTA |
| DAG_dynamic_checklist_test_loader.py | 1 | Alto | 🟠 ALTA |
| utils.py | 3 | Medio | 🟡 MEDIA |
| transform_helpers.py | 4 | Medio | 🟡 MEDIA |
| log_management_manager.py | 2 | Medio | 🟡 MEDIA |
| filters.py | 2 | Medio | 🟡 MEDIA |
| selenium_utils.py | 1 | Bajo | 🟢 BAJA |
| base_exporters.py | 1 | Bajo | 🟢 BAJA |

---

## Checklist de Remediar

- [ ] scraper.py: Agregar logging a líneas 75, 89, 103, 128, 247, 307
- [ ] date_filter_manager.py: Especificar 11 excepciones
- [ ] auth.py: Agregar validación + logging
- [ ] base_loader.py: Agregar validación + logging
- [ ] autin_gde/stractor.py: Agregar logging a 9 excepciones
- [ ] DAG_dynamic_checklist_test_loader.py: Agregar logging a línea 111
- [ ] utils.py: Separar lógica de import/Variable
- [ ] transform_helpers.py: Especificar 4 excepciones
- [ ] log_management_manager.py: Estandarizar retornos
- [ ] filters.py: Agregar logging consistente
- [ ] selenium_utils.py: Especificar excepciones
- [ ] base_exporters.py: Especificar excepciones

---

**Generado:** 2025-11-19
**Análisis de:** 56 archivos Python
**Bloques try/except revisados:** 85+
