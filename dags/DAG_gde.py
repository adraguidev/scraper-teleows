"""
DAG para ejecutar el scraper de GDE (ejecución manual).

Proceso ETL completo:
1. Extract: Descarga Excel de GDE desde portal Integratel
2. Load: Carga datos a PostgreSQL RAW (raw.gde_tasks)
3. Transform: Ejecuta SP para transformar datos (RAW → ODS)
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator  # type: ignore

# Asegurar imports de proyecto
sys.path.insert(0, "/opt/airflow/proyectos")

from teleows import TeleowsSettings, extraer_gde
from teleows.sources.gde.loader import load_gde
from teleows.sources.gde.run_sp import correr_sp_gde

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


def run_extract_gde() -> str:
    """
    PASO 1: Extract - Scraping del portal Integratel.

    Descarga el Excel de GDE desde el portal.
    """
    settings = TeleowsSettings.load_from_airflow(conn_id="teleows_portal")
    logger.info("🚀 [EXTRACT] Iniciando scraper de GDE...")

    try:
        file_path = extraer_gde(settings=settings)
        logger.info(f"✅ [EXTRACT] Archivo descargado: {file_path}")
        return str(file_path)
    except Exception as exc:
        logger.error(f"❌ [EXTRACT] Error: {exc}")
        raise


def run_load_gde(**context) -> dict:
    """
    PASO 2: Load - Carga a PostgreSQL RAW.

    Carga el Excel a la tabla raw.gde_tasks.
    """
    # Obtener ruta del archivo desde el task anterior
    ti = context['ti']
    file_path = ti.xcom_pull(task_ids='extract_gde')

    logger.info(f"📊 [LOAD] Cargando GDE a PostgreSQL...")
    logger.info(f"   Archivo: {file_path}")

    try:
        resultado = load_gde(
            filepath=file_path,
            postgres_conn_id="postgres_teleows"
        )

        logger.info(f"✅ [LOAD] Carga completada: {resultado['etl_msg']}")
        return resultado

    except Exception as exc:
        logger.error(f"❌ [LOAD] Error: {exc}")
        raise


def run_transform_gde(**context) -> dict:
    """
    PASO 3: Transform - Ejecución de Stored Procedure (RAW → ODS).

    Ejecuta el SP configurado para transformar los datos de RAW a ODS.
    """
    logger.info("⚙️  [TRANSFORM] Ejecutando Stored Procedure...")

    try:
        resultado = correr_sp_gde()

        logger.info(f"✅ [TRANSFORM] Transformación completada: {resultado['etl_msg']}")
        return resultado

    except Exception as exc:
        logger.error(f"❌ [TRANSFORM] Error: {exc}")
        raise


with DAG(
    "dag_gde_teleows",
    default_args=default_args,
    description="ETL completo para GDE - Ejecución manual",
    schedule=None,
    catchup=False,
    tags=["scraper", "gde", "integratel", "teleows", "etl"],
) as dag:

    # PASO 1: Extract
    extract = PythonOperator(
        task_id="extract_gde",
        python_callable=run_extract_gde,
        doc_md="""
        ### Extract - Web Scraping

        1. Login al portal Integratel
        2. Aplicación de filtros (CM, OPM, último mes)
        3. Exportación del reporte Console GDE
        4. Descarga del archivo Excel
        """,
    )

    # PASO 2: Load
    load = PythonOperator(
        task_id="load_to_raw",
        python_callable=run_load_gde,
        doc_md="""
        ### Load - Carga a PostgreSQL RAW

        Carga el Excel a la tabla raw.gde_tasks.
        Todas las columnas se cargan como VARCHAR en RAW.
        """,
    )

    # PASO 3: Transform
    transform = PythonOperator(
        task_id="transform_raw_to_ods",
        python_callable=run_transform_gde,
        doc_md="""
        ### Transform - Stored Procedure (RAW → ODS)

        Ejecuta ods.sp_cargar_gde_tasks() para:
        - Conversión de tipos de datos
        - Limpieza y validación
        - Transformaciones de negocio
        - Carga a tabla ODS
        """,
    )

    # Flujo ETL
    extract >> load >> transform
