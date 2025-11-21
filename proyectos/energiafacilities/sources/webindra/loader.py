from typing import Optional, Dict, Any
from core.base_loader import BaseLoaderPostgres
from core.utils import load_config
from core.helpers import traerjson

def load_indra(filepath: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga datos de WebIndra a PostgreSQL.

    Args:
        filepath: Ruta del archivo a cargar (opcional)

    Returns:
        Resultado de la carga con status, code y etl_msg
    """
    config = load_config()
    postgres_config = config.get("postgress", {})
    general_config = config.get("webindra_energia", {})
    Loader = BaseLoaderPostgres(
            config=postgres_config,
            configload=general_config
        )

    Loader.validar_conexion()
    columnas = traerjson(archivo='config/columnas/columns_map.json', valor='tablareciboswebindra')

    Loader.verificar_datos(
        data=general_config['local_dir'] + '/' + general_config['specific_filename'],
        column_mapping=columnas,
        strictreview=False,
        numerofilasalto=2
    )

    if not filepath:
        filepath = general_config['local_dir'] + '/' + general_config['specific_filename']
    carga = Loader.load_data(data=filepath, column_mapping=columnas, numerofilasalto=2)
    return carga




