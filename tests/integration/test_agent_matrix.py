"""A matriz do agente de IA no desktop real (D1/D2 do spec da aba Agente do Visus
Studio): ler a janela pelo `native snapshot` e agir pelo NÚMERO, como um agente faz.

Calculadora do Windows, acionada pela UIA (Invoke) — sem teclado nem mouse, então
não é `real_input`. Nunca mexe numa Calculadora sua: se já houver uma aberta, pula;
e no fim fecha só o processo que este teste abriu.

    pytest tests/integration/test_agent_matrix.py --integration -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli

pytestmark = pytest.mark.windows_only
runner = CliRunner()

_CALC_PROCESS = "CalculatorApp.exe"


def _calc_pids() -> set[int]:
    import psutil

    return {p.pid for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == _CALC_PROCESS.lower()}


@pytest.fixture
def calculadora():
    """O título da Calculadora que ESTE teste abriu."""
    before = _calc_pids()
    if before:
        pytest.skip("já existe uma Calculadora aberta — não mexo numa janela sua")
    subprocess.Popen(["calc.exe"])  # noqa: S603,S607 — app do próprio Windows
    title = None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and title is None:
        r = runner.invoke(cli, ["window", "list", "--json"])
        if r.exit_code == 0:
            for w in json.loads(r.output):
                t = str(w.get("title") or "")
                if t in ("Calculadora", "Calculator"):
                    title = t
        time.sleep(0.5)
    if title is None:
        pytest.skip("a Calculadora não abriu a tempo")
    time.sleep(1.0)  # a UI do app termina de montar depois da janela existir
    try:
        yield title
    finally:
        import psutil

        mine = []
        for pid in _calc_pids() - before:
            try:
                proc = psutil.Process(pid)
                proc.kill()
                mine.append(proc)
            except psutil.Error:
                pass
        # kill() no Windows é assíncrono: sem esperar, o próximo teste ainda via o
        # processo vivo e pulava por achar que a Calculadora era sua
        psutil.wait_procs(mine, timeout=10)


def test_window_ensure_acha_pelo_titulo_exato(calculadora: str) -> None:
    r = runner.invoke(cli, ["window", "ensure", "--title", calculadora, "--json"])
    assert r.exit_code == 0, r.output


def test_snapshot_numera_os_botoes_da_calculadora(calculadora: str) -> None:
    r = runner.invoke(cli, ["native", "snapshot", "--window", calculadora])
    assert r.exit_code == 0, r.output
    assert r.output.startswith("Window: ")
    assert "#num7Button" in r.output and "#equalButton" in r.output, r.output


def test_calculadora_soma_pelo_numero(calculadora: str) -> None:
    snap = runner.invoke(cli, ["native", "snapshot", "--window", calculadora, "--json"])
    assert snap.exit_code == 0, snap.output
    index = {i["auto_id"]: i["index"] for i in json.loads(snap.output)["items"] if i["auto_id"]}
    for auto_id in ("clearButton", "num7Button", "plusButton", "num8Button", "equalButton"):
        if auto_id not in index:
            continue  # o modo da calculadora pode não ter "C"
        r = runner.invoke(cli, ["native", "click", str(index[auto_id])])
        assert r.exit_code == 0, f"{auto_id}: {r.output}"
    result = runner.invoke(
        cli, ["native", "get-text", "--window", calculadora, "--auto-id", "CalculatorResults"]
    )
    assert result.exit_code == 0, result.output
    assert "15" in result.output, result.output


# --- clicks where they should land: a window that records every click -----------

_APP = Path(__file__).with_name("_click_target_app.py")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _cli(*args: str, config_dir: Path) -> subprocess.CompletedProcess:
    """The CLI as an agent runs it: its own process, read through a pipe."""
    env = dict(os.environ, VISUS_CONFIG=str(config_dir / "config.json"))
    return subprocess.run(
        [sys.executable, "-c", "import sys; from visus.desktop.cli import main; sys.exit(main(sys.argv[1:]))", *args],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=180,
        creationflags=_NO_WINDOW,
    )


@pytest.fixture
def alvo(tmp_path):
    """The click-recording window, opened (and closed) by the test itself."""
    import ctypes

    try:  # this process too: WindowFromPoint / GetCursorPos in physical pixels
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    proc = subprocess.Popen([sys.executable, str(_APP), str(tmp_path)], creationflags=_NO_WINDOW)
    ready = tmp_path / "ready.json"
    deadline = time.monotonic() + 20
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.2)
    if not ready.exists():
        proc.kill()
        pytest.skip("a janela de teste não abriu a tempo")
    time.sleep(0.3)
    info = json.loads(ready.read_text(encoding="utf-8"))
    info["dir"] = tmp_path
    try:
        yield info
    finally:
        proc.kill()
        proc.wait(10)


def _ours(point, pid) -> bool:
    """Is the window under ``point`` the test window? Never click anything else."""
    import win32gui
    import win32process

    hwnd = win32gui.WindowFromPoint(point)
    return bool(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == pid


def _clicks(info, n: int, timeout: float = 6.0) -> list[dict]:
    path = info["dir"] / "clicks.jsonl"
    deadline = time.monotonic() + timeout
    lines: list[str] = []
    while time.monotonic() < deadline:
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        if len(lines) >= n:
            break
        time.sleep(0.1)
    return [json.loads(line) for line in lines]


def _inside(click: dict, box) -> bool:
    x, y, w, h = box
    return x <= click["x"] <= x + w and y <= click["y"] <= y + h


def _empty_spot(info):
    cx, cy, _cw, _ch = info["canvas"]
    return (cx + 150, cy + 150)  # between the words and the buttons


def test_clique_virtual_cai_no_ponto_e_nao_mexe_o_cursor(alvo) -> None:
    import win32api

    point = _empty_spot(alvo)
    if not _ours(point, alvo["pid"]):
        pytest.skip("outra janela cobre a janela de teste")
    before = win32api.GetCursorPos()
    r = _cli("mouse", "click", str(point[0]), str(point[1]), "--virtual", config_dir=alvo["dir"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "virtual mouse" in r.stdout
    clicks = _clicks(alvo, 1)
    assert len(clicks) == 1, "a janela não recebeu o clique virtual"
    assert abs(clicks[0]["x"] - point[0]) <= 1 and abs(clicks[0]["y"] - point[1]) <= 1, clicks[0]
    assert win32api.GetCursorPos() == before, "o clique virtual moveu o cursor"


@pytest.mark.real_input
def test_clique_virtual_e_fisico_caem_no_mesmo_pixel(alvo) -> None:
    """O mouse virtual clica EXATAMENTE onde o físico clicaria."""
    import win32api

    point = _empty_spot(alvo)
    if not _ours(point, alvo["pid"]):
        pytest.skip("outra janela cobre a janela de teste")
    before = win32api.GetCursorPos()
    try:
        virtual = _cli("mouse", "click", str(point[0]), str(point[1]), "--virtual", config_dir=alvo["dir"])
        assert virtual.returncode == 0, virtual.stdout + virtual.stderr
        assert len(_clicks(alvo, 1)) == 1
        physical = _cli("mouse", "click", str(point[0]), str(point[1]), config_dir=alvo["dir"])
        assert physical.returncode == 0, physical.stdout + physical.stderr
        clicks = _clicks(alvo, 2)
    finally:
        win32api.SetCursorPos(before)  # devolve o cursor de quem roda o teste
    assert len(clicks) == 2, clicks
    v, f = clicks
    assert (v["x"], v["y"]) == (f["x"], f["y"]), f"virtual {v} × físico {f}"
    assert abs(v["x"] - point[0]) <= 1 and abs(v["y"] - point[1]) <= 1


def test_ocr_find_all_numera_em_ordem_de_leitura(alvo) -> None:
    pytest.importorskip("rapidocr")
    start = time.monotonic()
    r = _cli("text", "find-all", "Salvar", "--window", alvo["title"], "--no-overlay", "--json",
             "--ocr", "rapidocr", config_dir=alvo["dir"])
    elapsed = time.monotonic() - start
    assert r.returncode == 0, r.stdout + r.stderr
    matches = json.loads(r.stdout)
    assert len(matches) == 2, matches
    centers = [{"x": m["x"] + m["width"] // 2, "y": m["y"] + m["height"] // 2} for m in matches]
    # o da direita está 2 px mais alto e mesmo assim é o #2
    assert _inside(centers[0], alvo["items"]["salvar1"]), (matches, alvo["items"])
    assert _inside(centers[1], alvo["items"]["salvar2"]), (matches, alvo["items"])
    assert r.stderr.strip() == "", f"stderr deveria vir limpo:\n{r.stderr}"
    print(f"\nOCR só na janela: {elapsed:.1f}s")


def test_ocr_click_occurrence_2_virtual(alvo) -> None:
    pytest.importorskip("rapidocr")
    box = alvo["items"]["salvar2"]
    if not _ours((box[0] + box[2] // 2, box[1] + box[3] // 2), alvo["pid"]):
        pytest.skip("outra janela cobre a janela de teste")
    r = _cli("text", "click", "Salvar", "--occurrence", "2", "--window", alvo["title"], "--virtual",
             "--ocr", "rapidocr", config_dir=alvo["dir"])
    assert r.returncode == 0, r.stdout + r.stderr
    clicks = _clicks(alvo, 1)
    assert len(clicks) == 1 and _inside(clicks[0], box), (clicks, box)


def test_imagem_find_all_e_click_occurrence_2_virtual(alvo) -> None:
    pytest.importorskip("cv2")
    b1 = alvo["items"]["botao1"]
    template = alvo["dir"] / "botao.png"
    # the whole button, "OK" included: a template needs texture to have one peak
    shot = _cli("screenshot", str(template), "--region", f"{b1[0]},{b1[1]},{b1[2]},{b1[3]}",
                config_dir=alvo["dir"])
    assert shot.returncode == 0, shot.stdout + shot.stderr
    found = _cli("image", "find-all", str(template), "--window", alvo["title"], "--json", config_dir=alvo["dir"])
    assert found.returncode == 0, found.stdout + found.stderr
    matches = json.loads(found.stdout)
    assert len(matches) == 2, matches
    # o botão da direita está 1 px mais alto e mesmo assim é o #2
    assert matches[0]["x"] < matches[1]["x"], matches
    b2 = alvo["items"]["botao2"]
    if not _ours((b2[0] + b2[2] // 2, b2[1] + b2[3] // 2), alvo["pid"]):
        pytest.skip("outra janela cobre a janela de teste")
    r = _cli("image", "click", str(template), "--occurrence", "2", "--window", alvo["title"], "--virtual",
             config_dir=alvo["dir"])
    assert r.returncode == 0, r.stdout + r.stderr
    clicks = _clicks(alvo, 1)
    assert len(clicks) == 1 and _inside(clicks[0], b2), (clicks, b2)


def test_display_size_igual_ao_print(tmp_path) -> None:
    size = _cli("display-size", "--json", config_dir=tmp_path)
    shot = _cli("screenshot", "--base64", "--json", config_dir=tmp_path)
    assert size.returncode == 0 and shot.returncode == 0, size.stderr + shot.stderr
    s, p = json.loads(size.stdout), json.loads(shot.stdout)
    assert (s["width"], s["height"]) == (p["width"], p["height"])


def test_snapshot_de_janela_que_nao_existe_e_erro(tmp_path) -> None:
    r = _cli("native", "snapshot", "--window", "Janela Que Não Existe Ação", "--timeout", "3", config_dir=tmp_path)
    assert r.returncode == 1
    assert "Janela Que Não Existe Ação" in r.stderr  # e com acentos, pelo pipe
