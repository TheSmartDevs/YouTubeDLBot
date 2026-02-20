import os

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
    if p.exists():
        for f in p.iterdir():
            if f.is_file():
                clean_download(str(f))
