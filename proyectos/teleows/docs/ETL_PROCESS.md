# Proceso ETL de Teleows

Este documento describe el proceso ETL (Extract, Transform, Load) implementado en Teleows.

## Arquitectura ETL

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   EXTRACT    │────▶│     LOAD     │────▶│  TRANSFORM   │
│  (Scraping)  │     │  (RAW Layer) │     │ (ODS Layer)  │
└──────────────┘     └──────────────┘     └──────────────┘
   Portal Web          PostgreSQL           Stored
   Integratel          raw.*                Procedures
                                            ods.*
```

---

## 📊 GDE (Console GDE)

### Proceso

1. **Extract**: Descarga Excel del portal Integratel
2. **Load**: Carga a `raw.gde_tasks` (todas las columnas VARCHAR)
3. **Transform**: SP `ods.sp_cargar_gde_tasks()` transforma RAW → ODS

### Configuración

```yaml
# settings.yaml
gde:
  schema: "raw"
  table: "gde_tasks"
  if_exists: "replace"
  sp_carga: "ods.sp_cargar_gde_tasks"
```

### Ejecución

```python
# Desde Airflow DAG
from teleows import extraer_gde
from teleows.sources.gde.loader import load_gde
from teleows.sources.gde.run_sp import correr_sp_gde

# 1. Extract
filepath = extraer_gde(settings)

# 2. Load
resultado = load_gde(filepath)

# 3. Transform
resultado = correr_sp_gde()
```

---

## 📋 Dynamic Checklist (47 Pestañas)

### Proceso

1. **Extract**: Descarga Excel con 47 pestañas del portal Integratel
2. **Load**: Carga cada pestaña a su tabla RAW correspondiente (47 tablas)
3. **Transform**: Ejecuta 47 SPs para transformar RAW → ODS

### Configuración

```yaml
# settings.yaml
dynamic_checklist:
  schema: "raw"
  if_exists: "replace"
  sheets:
    - sheet_name: "avr"
      table: "dc_avr"
      sp_carga: "ods.sp_cargar_dc_avr"

    - sheet_name: "clima"
      table: "dc_clima"
      sp_carga: "ods.sp_cargar_dc_clima"

    # ... (47 pestañas en total)
```

### Ejecución

```python
# Desde Airflow DAG
from teleows import extraer_dynamic_checklist
from teleows.sources.dynamic_checklist.loader import load_dynamic_checklist
from teleows.sources.dynamic_checklist.run_sp import correr_sp_dynamic_checklist

# 1. Extract
filepath = extraer_dynamic_checklist(settings)

# 2. Load (todas las pestañas)
resultados = load_dynamic_checklist(filepath)
# Retorna: {"avr": {...}, "clima": {...}, ...}

# 3. Transform (todos los SPs)
resultados = correr_sp_dynamic_checklist()
# Retorna: {"avr": {...}, "clima": {...}, ...}
```

### Cargar Solo Algunas Pestañas

```python
# Load solo algunas pestañas específicas
resultados = load_dynamic_checklist(
    filepath,
    sheets_to_load=["avr", "clima", "ups_bateria_de_ups"]
)

# Transform solo algunas pestañas
resultados = correr_sp_dynamic_checklist(
    sheets_to_process=["avr", "clima"]
)
```

---

## 🗂️ Estructura de Carpetas

```
proyectos/teleows/
├── sources/
│   ├── gde/
│   │   ├── stractor.py       # Extract
│   │   ├── loader.py          # Load
│   │   ├── run_sp.py          # Transform
│   │   └── transformer.py     # (Opcional)
│   │
│   └── dynamic_checklist/
│       ├── stractor.py        # Extract
│       ├── loader.py          # Load (multi-pestaña)
│       ├── run_sp.py          # Transform (multi-SP)
│       └── transformer.py     # (Opcional)
│
├── config/
│   └── columnas/
│       └── columns_map.json   # Mapeo de columnas Excel → PostgreSQL
│
└── settings.yaml              # Configuración de tablas, SPs, etc.
```

---

## 📝 Mapeo de Columnas

El mapeo de columnas se define en `config/columnas/columns_map.json`:

```json
{
  "gde_tasks": {
    "task_id": "Task Id",
    "remedy_id": "Remedy ID",
    "create_time": "Createtime",
    ...
  },
  "dc_avr": {
    "campo_bd": "Campo Excel",
    ...
  }
}
```

**Nota:** Si no existe mapeo para una tabla, se usan los nombres de columna originales del Excel.

---

## 🗄️ Capas de Datos

### RAW Layer (`raw.*`)

- **Propósito**: Capa de ingesta inicial
- **Características**:
  - Todas las columnas como VARCHAR
  - Datos sin transformar (tal cual vienen del Excel)
  - Permite auditoría y reprocesamiento
  - Estrategia: `replace` (se reemplaza en cada carga)

### ODS Layer (`ods.*`)

- **Propósito**: Capa de datos operacionales
- **Características**:
  - Tipos de datos correctos (INT, DATE, DECIMAL, etc.)
  - Datos limpios y validados
  - Transformaciones de negocio aplicadas
  - Generado por Stored Procedures

---

## ⚙️ Stored Procedures

Los SPs siguen este patrón:

```sql
CREATE OR REPLACE PROCEDURE ods.sp_cargar_gde_tasks()
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Limpiar tabla ODS
    TRUNCATE ods.gde_tasks;

    -- 2. Insertar desde RAW con transformaciones
    INSERT INTO ods.gde_tasks (
        task_id,
        remedy_id,
        create_time,
        ...
    )
    SELECT
        task_id::INTEGER,
        remedy_id,
        TO_TIMESTAMP(create_time, 'DD/MM/YYYY HH24:MI:SS'),
        ...
    FROM raw.gde_tasks
    WHERE ... -- Filtros y validaciones
    ;

    -- 3. Registrar en log
    INSERT INTO public.sp_execution_log ...

    COMMIT;
END;
$$;
```

---

## 🔄 Flujo Completo en Airflow

```python
# DAG con ETL completo
with DAG("dag_gde_teleows", ...) as dag:

    # PASO 1: Extract
    extract = PythonOperator(
        task_id="extract_gde",
        python_callable=run_extract_gde,
    )

    # PASO 2: Load
    load = PythonOperator(
        task_id="load_to_raw",
        python_callable=run_load_gde,
    )

    # PASO 3: Transform
    transform = PythonOperator(
        task_id="transform_raw_to_ods",
        python_callable=run_transform_gde,
    )

    # Flujo
    extract >> load >> transform
```

---

## 📋 Checklist para Agregar Nueva Fuente

1. ✅ Crear carpeta en `sources/nueva_fuente/`
2. ✅ Implementar `stractor.py` (extract)
3. ✅ Implementar `loader.py` (load)
4. ✅ Implementar `run_sp.py` (transform)
5. ✅ Agregar configuración en `settings.yaml`
6. ✅ Agregar mapeo de columnas en `columns_map.json` (opcional)
7. ✅ Crear tablas RAW en PostgreSQL
8. ✅ Crear Stored Procedures en PostgreSQL
9. ✅ Crear DAG en `dags/DAG_nueva_fuente.py`
10. ✅ Probar proceso completo

---

## 🆘 Troubleshooting

### Error: "No se encontró configuración 'sheets' en dynamic_checklist"
- **Solución**: Asegúrate de tener la sección `sheets` en `settings.yaml`

### Error: "Pestaña 'xxx' no encontrada en el archivo Excel"
- **Solución**: Verifica que `sheet_name` en `settings.yaml` coincida exactamente con el nombre en Excel

### Error: "No se pudo cargar Connection 'postgres_teleows'"
- **Solución**: Configura la conexión en Airflow UI o usa `postgres_conn_id=None` para desarrollo local

### Pestaña vacía no carga
- **Comportamiento esperado**: Las pestañas vacías se omiten automáticamente con un warning

---

## 📚 Referencias

- [AIRFLOW_INTEGRATION.md](./AIRFLOW_INTEGRATION.md) - Integración con Airflow
- [columns_map.json](../config/columnas/columns_map.json) - Mapeo de columnas
- [settings.yaml](../settings.yaml) - Configuración completa
