"""
DAG para ejecutar el scraper de Dynamic Checklist (ejecución manual).

Proceso ETL completo:
1. Extract: Descarga Excel con 47 pestañas desde portal Integratel
2. Load: Carga cada pestaña a su tabla RAW en PostgreSQL
3. Transform: Ejecuta SPs para transformar datos (RAW → ODS)
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator  # type: ignore

# Asegurar imports de proyecto
sys.path.insert(0, "/opt/airflow/proyectos")

from teleows import TeleowsSettings, extraer_dynamic_checklist
from teleows.sources.dynamic_checklist.loader import load_dynamic_checklist
from teleows.sources.dynamic_checklist.run_sp import correr_sp_dynamic_checklist

logger = logging.getLogger(__name__)

default_args = {
    "owner": "adragui",
    "depends_on_past": False,
    "start_date": datetime(2024, 10, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def run_extract_dynamic_checklist() -> str:
    """
    PASO 1: Extract - Scraping del portal Integratel.

    Descarga el Excel con 47 pestañas desde el portal.
    """
    settings = TeleowsSettings.load_from_airflow(conn_id="teleows_portal")
    logger.info("🚀 [EXTRACT] Iniciando scraper de Dynamic Checklist...")

    try:
        file_path = extraer_dynamic_checklist(settings=settings)
        logger.info(f"✅ [EXTRACT] Archivo descargado: {file_path}")
        return str(file_path)
    except Exception as exc:
        logger.error(f"❌ [EXTRACT] Error: {exc}")
        raise


def run_load_dynamic_checklist(**context) -> dict:
    """
    PASO 2: Load - Carga de 47 pestañas a PostgreSQL RAW.

    Cada pestaña del Excel se carga a su propia tabla RAW.
    """
    # Obtener ruta del archivo desde el task anterior
    ti = context['ti']
    file_path = ti.xcom_pull(task_ids='extract_dynamic_checklist')

    logger.info(f"📊 [LOAD] Cargando 47 pestañas a PostgreSQL...")
    logger.info(f"   Archivo: {file_path}")

    try:
        resultados = load_dynamic_checklist(
            filepath=file_path,
            postgres_conn_id="postgres_teleows"
        )

        # Log resumen
        exitosas = sum(1 for r in resultados.values() if r["status"] == "success")
        total_rows = sum(r.get("rows", 0) for r in resultados.values())

        logger.info(f"✅ [LOAD] Carga completada:")
        logger.info(f"   Pestañas procesadas: {len(resultados)}")
        logger.info(f"   Exitosas: {exitosas}")
        logger.info(f"   Total filas: {total_rows:,}")

        return resultados

    except Exception as exc:
        logger.error(f"❌ [LOAD] Error: {exc}")
        raise


def run_transform_dynamic_checklist(**context) -> dict:
    """
    PASO 3: Transform - Ejecución de Stored Procedures (RAW → ODS).

    Ejecuta los SPs configurados para transformar los datos de RAW a ODS.
    """
    logger.info("⚙️  [TRANSFORM] Ejecutando Stored Procedures...")

    try:
        resultados = correr_sp_dynamic_checklist(
            postgres_conn_id="postgres_teleows"
        )

        # Log resumen
        exitosos = sum(1 for r in resultados.values() if r["status"] == "success")

        logger.info(f"✅ [TRANSFORM] Transformación completada:")
        logger.info(f"   SPs ejecutados: {len(resultados)}")
        logger.info(f"   Exitosos: {exitosos}")

        return resultados

    except Exception as exc:
        logger.error(f"❌ [TRANSFORM] Error: {exc}")
        raise


with DAG(
    "dag_dynamic_checklist_teleows",
    default_args=default_args,
    description="ETL completo para Dynamic Checklist (47 pestañas) - Ejecución manual",
    schedule=None,
    catchup=False,
    tags=["scraper", "dynamic-checklist", "integratel", "teleows", "etl"],
) as dag:

    # PASO 1: Extract
    extract = PythonOperator(
        task_id="extract_dynamic_checklist",
        python_callable=run_extract_dynamic_checklist,
        doc_md="""
        ### Extract - Web Scraping

        1. Login al portal Integratel
        2. Navegación a Dynamic checklist → Sub PM Query
        3. Aplicación de filtros y exportación
        4. Descarga del Excel con 47 pestañas
        """,
    )

    # PASO 2: Load
    load = PythonOperator(
        task_id="load_to_raw",
        python_callable=run_load_dynamic_checklist,
        doc_md="""
        ### Load - Carga a PostgreSQL RAW

        Carga cada una de las 47 pestañas del Excel a su tabla RAW correspondiente:
        - raw.dc_avr
        - raw.dc_clima
        - raw.dc_ups_bateria_ups
        - ... (47 tablas en total)

        Todas las columnas se cargan como VARCHAR en RAW.
        """,
    )

    # PASO 3: Transform
    transform = PythonOperator(
        task_id="transform_raw_to_ods",
        python_callable=run_transform_dynamic_checklist,
        doc_md="""
        ### Transform - Stored Procedures (RAW → ODS)

        Ejecuta los SPs configurados para cada pestaña:
        - Conversión de tipos de datos
        - Limpieza y validación
        - Transformaciones de negocio
        - Carga a tablas ODS
        """,
    )

    # Flujo ETL
    extract >> load >> transform
