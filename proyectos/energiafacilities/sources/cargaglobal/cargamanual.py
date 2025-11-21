from core.base_loader import BaseLoaderPostgres
from core.utils import load_config, setup_logging

setup_logging(level="INFO")

def load_clienteslibres(filepath="tmp/global/archivo.xlsx", modo=None, schema=None, table_name=None):
    """
    Carga datos desde un archivo Excel a PostgreSQL.

    Args:
        filepath: Ruta del archivo Excel a cargar
        modo: Modo de carga ('replace', 'append', 'fail')
        schema: Schema de PostgreSQL
        table_name: Nombre de la tabla destino

    Returns:
        Resultado de la carga
    """
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = {}
    Loader = BaseLoaderPostgres(
        config=postgres_config,
        configload=general_config
    )

    carga = Loader.load_data(data=filepath, modo=modo, schema=schema, table_name=table_name)
    return carga


