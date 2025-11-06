"""
DAG para ejecutar el scraper de GDE (ejecución manual).
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator  # type: ignore

# Asegurar imports de proyecto
sys.path.insert(0, "/opt/airflow/proyectos")

from teleows import TeleowsSettings, extraer_gde

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


def run_gde_scraper() -> str:
    """
    Construye la configuración desde Airflow y ejecuta la extracción GDE.

    Usa TeleowsSettings.load_from_airflow() que implementa el orden correcto:
    1. Variables de entorno (fallback)
    2. settings.yaml (base)
    3. Airflow Variables (TELEOWS_*)
    4. Airflow Connection 'teleows_portal' (prioridad más alta)
    """
    settings = TeleowsSettings.load_from_airflow(conn_id="teleows_portal")
    logger.info("🚀 Iniciando scraper de GDE...")

    try:
        file_path = extraer_gde(settings=settings)
        logger.info("✅ Scraper GDE completado. Archivo: %s", file_path)
        return str(file_path)
    except Exception as exc:
        logger.error("❌ Error en scraper GDE: %s", exc)
        raise


with DAG(
    "dag_gde_teleows",
    default_args=default_args,
    description="Scraper para reporte GDE - Ejecución manual",
    schedule=None,
    catchup=False,
    tags=["scraper", "gde", "integratel", "teleows"],
) as dag:
    scrape_gde = PythonOperator(
        task_id="scrape_gde_report",
        python_callable=run_gde_scraper,
        doc_md="""
        ### Scraper GDE

        1. Login al portal Integratel.
        2. Aplicación de filtros (CM, OPM, último mes).
        3. Exportación del reporte Console GDE.
        4. Descarga y retorna la ruta del archivo.
        """,
    )

    scrape_gde
