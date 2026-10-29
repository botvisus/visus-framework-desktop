"""Metadados de pacote que quebram instalações sem nenhuma mudança neste repositório.

- `mcp_server.py` importa `mcp.server.fastmcp`, que o mcp 2.0 removeu: sem teto,
  `pip install "visus-desktop[mcp]"` passa a instalar um servidor que morre no import
  (o visus-web já sofreu exatamente isso).
- O mcp exige Python 3.10+, e o projeto declara 3.8+: sem um marcador de versão no
  extra, o `uv` nem resolve o ambiente de desenvolvimento.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = pytest.importorskip("tomli")

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _extra(name: str) -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return list(data["project"]["optional-dependencies"][name])


def test_mcp_tem_teto_abaixo_do_2() -> None:
    (req,) = [r for r in _extra("mcp") if r.startswith("mcp")]
    assert re.search(r"<\s*2(\b|\.)", req), f"mcp sem teto <2: {req!r}"


def test_mcp_so_entra_em_python_310_ou_mais() -> None:
    (req,) = [r for r in _extra("mcp") if r.startswith("mcp")]
    assert "python_version" in req and "3.10" in req, f"extra mcp sem marcador de Python: {req!r}"
