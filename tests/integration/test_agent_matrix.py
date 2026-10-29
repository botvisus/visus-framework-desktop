"""A matriz do agente de IA no desktop real (D1/D2 do spec da aba Agente do Visus
Studio): ler a janela pelo `native snapshot` e agir pelo NÚMERO, como um agente faz.

Calculadora do Windows, acionada pela UIA (Invoke) — sem teclado nem mouse, então
não é `real_input`. Nunca mexe numa Calculadora sua: se já houver uma aberta, pula;
e no fim fecha só o processo que este teste abriu.

    pytest tests/integration/test_agent_matrix.py --integration -v
"""

from __future__ import annotations

import json
import subprocess
import time

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
