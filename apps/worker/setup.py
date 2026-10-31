"""Declare path dependencies as absolute file URLs at build time.

Relative PEP 508 file URLs do not round-trip through packaging, so pip rejects
them. Resolving the sibling packages here keeps `pip install` of this
directory working in a checkout and in the Docker build layout.
"""

from pathlib import Path

from setuptools import setup

_ROOT = Path(__file__).resolve().parent
_SHARED = (_ROOT / "../../packages/shared").resolve()
_DETECTOR = (_ROOT / "../../packages/detector").resolve()


def _file_dep(name: str, path: Path) -> str:
    if not (path / "pyproject.toml").is_file():
        raise RuntimeError(f"{name} is not at {path}")
    return f"{name} @ file://{path.as_posix()}"


setup(
    install_requires=[
        _file_dep("secureai-shared", _SHARED),
        _file_dep("secureai-detector", _DETECTOR),
    ]
)
