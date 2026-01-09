"""
Service functions for interactions with the filesystem.
"""

import stat
from pathlib import Path

from tilemaker.metadata.generation import Layer, layers_from_fits


def safe_read_directory(top_level: Path, search: Path) -> list[Path]:
    """
    Read a directory (if allowed) below the top-level. Returns the paths of
    the children relative to your 'top_level' path.
    """
    if not search.absolute().is_relative_to(top_level.absolute()):
        raise ValueError(f"Requested path {search} not within {top_level}")

    return [
        x.relative_to(top_level) for x in search.iterdir() if not x.name.startswith(".")
    ]


def safe_read_directory_specific_file_types(
    top_level: Path, search: Path, extensions: tuple[str] = ("fits",)
) -> tuple[list[Path], list[Path]]:
    """
    Uses 'safe_read_directory' above to read a directory. Only returns directories
    and files with the provided extension, and checks that they have world-readable
    permissions. Returns two lists, one of files and one of directories.
    """

    potential_listing = safe_read_directory(top_level=top_level, search=search)

    def filter_individual(item: Path) -> bool:
        complete_path = top_level / item
        mode = complete_path.stat().st_mode

        if not stat.S_IROTH & mode:
            return False

        if complete_path.is_dir():
            return True

        for x in extensions:
            if item.name.endswith(x):
                return True

        return False

    files = [x for x in filter(filter_individual, potential_listing) if not x.is_dir()]
    directories = [
        x for x in filter(filter_individual, potential_listing) if x.is_dir()
    ]

    return files, directories


def safe_evaluate(
    top_level: Path, file_path: Path, extensions: tuple[str] = ("fits",)
) -> list[Layer]:
    if not file_path.absolute().is_relative_to(top_level.absolute()):
        raise ValueError(f"Requested path {file_path} not within {top_level}")

    valid_extension = False
    for extension in extensions:
        if file_path.name.endswith(extension):
            valid_extension = True
            break

    if not valid_extension:
        raise ValueError(f"Extension of {file_path} is not valid")

    layers = layers_from_fits(filename=file_path)

    return layers
