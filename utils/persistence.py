import os
import shutil
import tempfile
import logging

logger = logging.getLogger("crinometro")

def atomic_write(filepath: str, content: bytes):
    """Escreve num arquivo de forma atomica usando rename, mantendo backup antigo."""
    bak_path = filepath + ".bak"
    if os.path.exists(filepath):
        try:
            shutil.copy2(filepath, bak_path)
        except Exception as e:
            logger.warning(f"Nao foi possivel criar backup de {filepath}: {e}")
            
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="." + os.path.basename(filepath), suffix=".tmp")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception as e:
        logger.error(f"Erro na escrita atomica para {filepath}: {e}", exc_info=True)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def safe_load(filepath: str, read_mode: str = 'r'):
    """Tenta ler arquivo e seu backup."""
    bak_path = filepath + ".bak"
    try:
        with open(filepath, read_mode, encoding='utf-8' if 'b' not in read_mode else None) as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Erro ao ler {filepath}: {e}. Tentando backup.")
        if os.path.exists(bak_path):
            try:
                with open(bak_path, read_mode, encoding='utf-8' if 'b' not in read_mode else None) as f:
                    return f.read()
            except Exception as e2:
                logger.error(f"Erro ao ler backup {bak_path}: {e2}")
        raise

def quarantine_corrupted(filepath: str):
    """Move arquivo corrompido para quarentena."""
    if not os.path.exists(filepath):
        return
    quarantine_path = filepath + ".corrupted"
    try:
        os.replace(filepath, quarantine_path)
        logger.info(f"Arquivo corrompido movido para quarentena: {quarantine_path}")
    except Exception as e:
        logger.error(f"Erro ao mover arquivo corrompido para quarentena: {e}")

def atomic_write_json(filepath: str, obj):
    import json
    content = json.dumps(obj, indent=4, ensure_ascii=False).encode('utf-8')
    atomic_write(filepath, content)
