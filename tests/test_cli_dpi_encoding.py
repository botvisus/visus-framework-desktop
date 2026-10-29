"""O processo da CLI como um agente de IA o usa: cada comando é um processo novo,
lido por um pipe.

- DPI: num Windows com escala ≠ 100%, um processo que não se declara "DPI aware"
  recebe coordenadas virtualizadas. O print (mss) sai em pixels físicos e um
  `mouse click` noutro processo caía no lugar errado. Todo comando agora se declara
  per-monitor aware antes de tocar a tela — pixel do print = pixel do mouse.
- UTF-8: lido por um pipe, o Python usa o codepage do Windows e "ação" chegava como lixo.
- O print para a IA: o modelo paga a imagem pela RESOLUÇÃO, não pelos bytes —
  `--max-width` encolhe (e diz a escala para voltar às coordenadas da tela); o
  `--jpeg` é o formato que o orquestrador guarda (numa tela de UI plana ele sai
  quase do tamanho do PNG, medido: 155 KB × 153 KB).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import types

import pytest
from click.testing import CliRunner
from PIL import Image

from visus.desktop import cli as cli_module
from visus.desktop.cli import cli

runner = CliRunner()


@pytest.mark.skipif(sys.platform != "win32", reason="DPI awareness é do Windows")
def test_prepare_process_marca_dpi_por_monitor(monkeypatch: pytest.MonkeyPatch) -> None:
    import ctypes

    calls: list[int] = []
    fake = types.SimpleNamespace(
        shcore=types.SimpleNamespace(SetProcessDpiAwareness=lambda v: calls.append(v) or 0),
        user32=types.SimpleNamespace(SetProcessDPIAware=lambda: calls.append(-1) or 1),
    )
    monkeypatch.setattr(ctypes, "windll", fake, raising=False)
    cli_module._prepare_process()
    assert calls == [2], "PROCESS_PER_MONITOR_DPI_AWARE (2) primeiro"


def test_main_prepara_o_processo_antes_de_qualquer_comando(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr(cli_module, "_prepare_process", lambda: called.append(True))
    assert cli_module.main(["keys"]) == 0
    assert called == [True]


def test_saida_utf8_mesmo_em_pipe(tmp_path) -> None:
    pytest.importorskip("rapidocr")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env["VISUS_CONFIG"] = str(tmp_path / "c.json")
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; from visus.desktop.cli import main; sys.exit(main(['text','find','ação','--region','0,0,4,4','--ocr','rapidocr']))"],
        cwd=str(tmp_path),
        capture_output=True,
        env=env,
        timeout=120,
    )
    out = (proc.stdout + proc.stderr).decode("utf-8")
    assert proc.returncode != 0
    assert "ação" in out, out


def _fake_capture(*_a: object, **_k: object) -> Image.Image:
    return Image.new("RGB", (40, 20), (200, 30, 90))


def test_screenshot_jpeg_base64_para_a_ia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("visus.desktop.core.screen.capture_screen", _fake_capture)
    r = runner.invoke(cli, ["screenshot", "--base64", "--jpeg", "--quality", "70", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["mime_type"] == "image/jpeg"
    assert (data["width"], data["height"]) == (40, 20)
    assert base64.b64decode(data["data_base64"])[:3] == b"\xff\xd8\xff"


def test_screenshot_base64_continua_png_por_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("visus.desktop.core.screen.capture_screen", _fake_capture)
    r = runner.invoke(cli, ["screenshot", "--base64", "--json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["mime_type"] == "image/png"


def test_screenshot_max_width_encolhe_e_informa_a_escala(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "visus.desktop.core.screen.capture_screen", lambda *a, **k: Image.new("RGB", (1920, 1080))
    )
    r = runner.invoke(cli, ["screenshot", "--base64", "--jpeg", "--max-width", "1280", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert (data["width"], data["height"]) == (1280, 720)
    assert data["scale"] == pytest.approx(1280 / 1920)


def test_screenshot_sem_max_width_escala_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("visus.desktop.core.screen.capture_screen", _fake_capture)
    r = runner.invoke(cli, ["screenshot", "--base64", "--max-width", "1280", "--json"])
    assert json.loads(r.output)["scale"] == 1.0
