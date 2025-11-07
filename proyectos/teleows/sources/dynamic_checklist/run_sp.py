"""
Ejecución de Stored Procedures para Dynamic Checklist.

Transforma los datos de RAW → ODS para todas las pestañas configuradas.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from teleows.config import load_yaml_config
from teleows.core.base_postgres import PostgresConnector

logger = logging.getLogger(__name__)


def correr_sp_dynamic_checklist(
    sheets_to_process: Optional[List[str]] = None,
    postgres_conn_id: Optional[str] = "postgres_teleows"
) -> Dict[str, dict]:
    """
    Ejecuta stored procedures para transformar datos de Dynamic Checklist (RAW → ODS).

    Procesa cada pestaña configurada ejecutando su SP correspondiente.

    Args:
        sheets_to_process: Lista de nombres de pestañas a procesar. Si None, procesa todas.
        postgres_conn_id: ID de conexión PostgreSQL en Airflow

    Returns:
        Diccionario con resultado por cada SP ejecutado:
        {
            "sheet_name": {"status": "success", "code": 200, "etl_msg": "...", "sp_name": "..."},
            ...
        }

    Example:
        >>> # Ejecutar SPs para todas las pestañas
        >>> resultados = correr_sp_dynamic_checklist()
        >>>
        >>> # Ejecutar SPs solo para algunas pestañas
        >>> resultados = correr_sp_dynamic_checklist(
        ...     sheets_to_process=["avr", "clima", "ups_bateria_de_ups"]
        ... )
        >>>
        >>> # Ver resultados
        >>> for sheet, resultado in resultados.items():
        ...     print(f"{sheet}: {resultado['etl_msg']}")
    """
    try:
        # Cargar configuración
        config = load_yaml_config(postgres_conn_id=postgres_conn_id)
        postgres_config = config.get("postgres", {})
        dc_config = config.get("dynamic_checklist", {})

        # Validar configuraciones
        if not postgres_config:
            raise ValueError("No se encontró configuración 'postgres' en settings.yaml")
        if not dc_config:
            raise ValueError("No se encontró configuración 'dynamic_checklist' en settings.yaml")

        # Obtener configuración de pestañas
        sheets_config = dc_config.get("sheets", [])
        if not sheets_config:
            raise ValueError(
                "No se encontró 'sheets' en la configuración de dynamic_checklist"
            )

        # Filtrar pestañas si se especifica
        if sheets_to_process:
            sheets_config = [s for s in sheets_config if s.get("sheet_name") in sheets_to_process]
            if not sheets_config:
                raise ValueError(f"Ninguna de las pestañas especificadas fue encontrada: {sheets_to_process}")

        # Filtrar solo pestañas que tienen SP configurado
        sheets_with_sp = [s for s in sheets_config if s.get("sp_carga")]

        if not sheets_with_sp:
            logger.warning("⚠ No hay stored procedures configurados para ninguna pestaña")
            return {}

        logger.info(f"🔄 Ejecutando Stored Procedures de Dynamic Checklist")
        logger.info(f"   Pestañas con SP: {len(sheets_with_sp)}")

        # Crear conexión a PostgreSQL
        logger.info("🔌 Conectando a PostgreSQL...")
        postgres = PostgresConnector(postgres_config)
        postgres.validar_conexion()

        # Ejecutar SP de cada pestaña
        resultados = {}

        for sheet_cfg in sheets_with_sp:
            sheet_name = sheet_cfg.get("sheet_name")
            sp_name = sheet_cfg.get("sp_carga")

            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"⚙️  Ejecutando SP para: {sheet_name}")
                logger.info(f"   SP: {sp_name}")
                logger.info(f"{'='*60}")

                # Ejecutar SP
                resultado = _execute_single_sp(
                    postgres=postgres,
                    sp_name=sp_name,
                    sheet_name=sheet_name
                )

                resultados[sheet_name] = resultado
                logger.info(f"✅ {sheet_name}: {resultado['etl_msg']}")

            except Exception as e:
                error_msg = f"Error ejecutando SP para '{sheet_name}': {e}"
                logger.error(f"❌ {error_msg}")
                resultados[sheet_name] = {
                    "status": "error",
                    "code": 500,
                    "etl_msg": error_msg,
                    "sp_name": sp_name
                }

        # Cerrar conexión
        postgres.close()

        # Resumen final
        exitosos = sum(1 for r in resultados.values() if r["status"] == "success")
        fallidos = len(resultados) - exitosos

        logger.info(f"\n{'='*60}")
        logger.info(f"⚙️  RESUMEN DE TRANSFORMACIÓN - Dynamic Checklist")
        logger.info(f"{'='*60}")
        logger.info(f"   Total SPs ejecutados: {len(resultados)}")
        logger.info(f"   ✅ Exitosos: {exitosos}")
        logger.info(f"   ❌ Fallidos: {fallidos}")
        logger.info(f"{'='*60}\n")

        return resultados

    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución de SPs: {e}")
        raise


def _execute_single_sp(
    postgres: PostgresConnector,
    sp_name: str,
    sheet_name: str
) -> dict:
    """
    Ejecuta un solo stored procedure y obtiene sus logs.

    Args:
        postgres: Conexión a PostgreSQL
        sp_name: Nombre del SP a ejecutar
        sheet_name: Nombre de la pestaña (para logs)

    Returns:
        Diccionario con resultado de la ejecución
    """
    # Ejecutar SP
    logger.info(f"   ▶ Ejecutando: {sp_name}()")
    postgres.ejecutar(sp_name, tipo='sp')

    # Intentar obtener logs del SP
    try:
        logger.debug(f"   📋 Obteniendo logs de ejecución...")
        log_data = postgres.ejecutar(
            "public.log_sp_ultimo_fn",
            parametros=(f'{sp_name}()',),
            tipo='fn'
        )

        if not log_data.empty:
            estado = log_data['estado'].values[0] if 'estado' in log_data.columns else 'unknown'
            mensaje = log_data['msj_error'].values[0] if 'msj_error' in log_data.columns else 'Sin mensaje'
            registros = log_data['registros_afectados'].values[0] if 'registros_afectados' in log_data.columns else 0

            logger.info(f"   📊 Estado: {estado}")
            logger.info(f"   📝 Registros procesados: {registros:,}")
            if mensaje and mensaje != 'Sin mensaje':
                logger.info(f"   💬 Detalle: {mensaje}")

            return {
                "status": "success" if estado == "success" else "warning",
                "code": 200,
                "etl_msg": f"SP ejecutado: {estado} - {mensaje} ({registros:,} registros)",
                "sp_name": sp_name,
                "registros": int(registros) if registros else 0,
                "log_data": log_data.to_dict('records')
            }

    except Exception as log_error:
        # Si no existe la función de logs, continuar sin error
        logger.debug(f"   ⚠ No se pudo obtener log del SP: {log_error}")

    return {
        "status": "success",
        "code": 200,
        "etl_msg": f"SP '{sp_name}' ejecutado correctamente (sin logs disponibles)",
        "sp_name": sp_name
    }
