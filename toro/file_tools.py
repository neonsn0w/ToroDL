import re
from pathlib import Path

from typing import Union, List, Any

import shutil

import os


def cleanup():
    """Removes files left from the last time that the bot was executed."""
    if os.path.exists("../media-downloads"):
        shutil.rmtree("../media-downloads")

    if os.path.exists("../yt-dlp-downloads"):
        shutil.rmtree("../yt-dlp-downloads")


def get_natural_sort_key(s: Union[str, Path]) -> List[Any]:
    target = s.name if isinstance(s, Path) else s

    parts = re.split(r'(\d+)', target)

    def convert_part(part):
        return int(part) if part.isdigit() else part

    return [convert_part(p) for p in parts]


def naturally_sort_filenames(filenames: List[Union[str, Path]]) -> List[Union[str, Path]]:
    return sorted(filenames, key=get_natural_sort_key)


def is_file_smaller_than_50mb(file_path: str) -> bool:
    return os.path.getsize(file_path) < 50 * 1024 * 1024


def is_arr_smaller_than_50mb(files) -> bool:
    for f in files:
        if not is_file_smaller_than_50mb(f):
            return False

    return True


def chunk_list(data: list, size: int):
    """Yield successive n-sized chunks from a list."""
    for i in range(0, len(data), size):
        yield data[i:i + size]
