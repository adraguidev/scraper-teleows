import logging
from core.base_loader import BaseLoaderPostgres
from core.utils import load_config
from core.helpers import traerjson

logger = logging.getLogger(__name__)

def load_sftp_energia(filepath=None, table_name=None):
    """
    Carga datos de SFTP energía a PostgreSQL.

    Args:
        filepath: Ruta del archivo a cargar (opcional)
        table_name: Nombre de la tabla destino ('table_DA' o 'table_PD')

    Returns:
        Resultado de la carga
    """
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get("sftp_energia", {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    Loader.validar_conexion()
    columnas = traerjson(archivo='config/columnas/columns_map.json', valor='tablarecibosenergia')
    filedata = filepath or (general_config['local_dir'] + '/' + general_config['specific_filename'])
    logger.debug(f"Cargando datos desde: {filedata}")
    Loader.verificar_datos(data=filedata, column_mapping=columnas, table_name=general_config[table_name])
    
    carga = Loader.load_data(data=filedata, column_mapping=columnas, table_name=general_config[table_name])
    return carga


def load_sftp_energia_DA(filepath=None):
    """Carga datos de SFTP energía DA a PostgreSQL."""
    return load_sftp_energia(filepath=filepath, table_name='table_DA')

def load_sftp_energia_PD(filepath=None):
    """Carga datos de SFTP energía PD a PostgreSQL."""
    return load_sftp_energia(filepath=filepath, table_name='table_PD')