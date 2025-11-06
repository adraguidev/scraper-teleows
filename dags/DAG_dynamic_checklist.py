"""
DAG para ejecutar el scraper de Dynamic Checklist (ejecución manual).
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator  # type: ignore

# Asegurar imports de proyecto
sys.path.insert(0, "/opt/airflow/proyectos")

from teleows import TeleowsSettings, extraer_dynamic_checklist

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


def run_dynamic_checklist_scraper() -> str:
    """
    Construye la configuración desde Airflow y ejecuta la extracción Dynamic Checklist.

    Usa TeleowsSettings.load_from_airflow() que implementa el orden correcto:
    1. Variables de entorno (fallback)
    2. settings.yaml (base)
    3. Airflow Variables (TELEOWS_*)
    4. Airflow Connection 'teleows_portal' (prioridad más alta)
    """
    settings = TeleowsSettings.load_from_airflow(conn_id="teleows_portal")
    logger.info("🚀 Iniciando scraper de Dynamic Checklist...")

    try:
        file_path = extraer_dynamic_checklist(settings=settings)
        logger.info("✅ Scraper Dynamic Checklist completado. Archivo: %s", file_path)
        return str(file_path)
    except Exception as exc:
        logger.error("❌ Error en scraper Dynamic Checklist: %s", exc)
        raise


with DAG(
    "dag_dynamic_checklist_teleows",
    default_args=default_args,
    description="Scraper para Dynamic Checklist - Ejecución manual",
    schedule=None,
    catchup=False,
    tags=["scraper", "dynamic-checklist", "integratel", "teleows"],
) as dag:
    scrape_checklist = PythonOperator(
        task_id="scrape_dynamic_checklist",
        python_callable=run_dynamic_checklist_scraper,
        doc_md="""
        ### Scraper Dynamic Checklist

        1. Login al portal Integratel.
        2. Navegación a Dynamic checklist > Sub PM Query.
        3. Aplicación de filtros y disparo de la exportación.
        4. Descarga y retorna la ruta del archivo generado (directo o vía Log Management).
        """,
    )

    scrape_checklist
