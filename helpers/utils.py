import os
import shutil

from helpers.logger import LOGGER


def clean_download(*files):
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
                LOGGER.info(f"Removed temporary file: {file}")
        except Exception as e:
            LOGGER.error(f"clean_download error for {file}: {e}")


def clean_temp_files(temp_dir):
    from pathlib import Path
    p = Path(temp_dir)
    if not p.exists():
        return
    try:
        if p.is_file():
            p.unlink()
            LOGGER.info(f"Removed temporary file: {p}")
            return
        shutil.rmtree(p)
        LOGGER.info(f"Removed temporary directory: {p}")
    except Exception as e:
        LOGGER.error(f"clean_temp_files error for {p}: {e}")
