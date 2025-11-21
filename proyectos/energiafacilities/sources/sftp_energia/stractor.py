from typing import Optional, Dict, Any
from core.base_stractor import BaseExtractorSFTP
from core.utils import load_config, setup_logging
from core.helpers import generar_archivo_especifico

setup_logging(level="INFO")

def extraersftp_energia(specific_file_config: str, periodo: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrae archivo de energía desde SFTP según configuración especificada.

    Args:
        specific_file_config: Clave de configuración del archivo ('specific_filename' o 'specific_filename2')
        periodo: Periodo en formato YYYYMM (opcional, por defecto mes anterior)

    Returns:
        Metadata de la extracción (status, code, etl_msg, ruta)
    """
    config = load_config()
    sftp_config_connect = config.get("sftp_energia_c", {})
    sftp_config_others = config.get("sftp_energia", {})
    Extractor = BaseExtractorSFTP(
        config_connect=sftp_config_connect,
        config_paths=sftp_config_others
    )
    Extractor.validar_conexion()
    Extractor.validate()  # validar datos del sftp
    archivos_atributos = Extractor.listar_archivos_atributos()
    archivoextraer = generar_archivo_especifico(
        lista_archivos=archivos_atributos,
        basearchivo=sftp_config_others[specific_file_config],
        periodo=periodo
    )
    metastraccion = Extractor.extract(specific_file=archivoextraer["nombre"])
    return metastraccion

def extraersftp_energia_PD(periodo: Optional[str] = None) -> str:
    """Extrae archivo de energía PD desde SFTP.

    Returns:
        Ruta local del archivo extraído
    """
    metastraccion = extraersftp_energia("specific_filename", periodo=periodo)
    return metastraccion["ruta"]

def extraersftp_energia_DA(periodo: Optional[str] = None) -> str:
    """Extrae archivo de energía DA desde SFTP.

    Returns:
        Ruta local del archivo extraído
    """
    metastraccion = extraersftp_energia("specific_filename2", periodo=periodo)
    return metastraccion["ruta"]
