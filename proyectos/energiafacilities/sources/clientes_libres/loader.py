from typing import Optional, Dict, Any
from core.base_loader import BaseLoaderPostgres
from core.utils import load_config

def load_clienteslibres(filepath: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga datos de clientes libres a PostgreSQL.

    Args:
        filepath: Ruta del archivo a cargar (opcional)

    Returns:
        Resultado de la carga con status, code y etl_msg
    """
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get("clientes_libres", {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    Loader.validar_conexion()
    Loader.verificar_datos(data=general_config['local_destination_dir'], table_name=general_config.get('table'))

    if not filepath:
        filepath = general_config['local_destination_dir']
    carga = Loader.load_data(data=filepath, table_name=general_config.get('table'))
    return carga

