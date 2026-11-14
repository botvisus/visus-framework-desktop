"""Checagens antes de mexer no mouse ou no teclado de verdade.

Entrada física (``SendInput``) vai para o que estiver na tela, não para um controle --
diferente do ``Invoke`` do UIA. Quatro perguntas antes de enviar:

* ``uipi_blocks(pid)`` -- o programa roda como administrador e nós não? O Windows (UIPI)
  descarta CALADO o clique e as teclas que sobem esse degrau: o envio "dá certo" e nada
  acontece. Recusar antes vira "não chegou, rode como administrador".
* ``covering_window(hwnd, x, y)`` -- outra janela está por cima do ponto? O clique iria
  para ela (um aviso, um diálogo de outro programa, a bandeja). Menus e popups do PRÓPRIO
  programa contam como dele.
* ``blocked_combo(keys)`` -- o atalho tira o foco da execução ou muda a sessão (Alt+F4,
  Win+L, Alt+Tab...)? Recusado, salvo ``force``.
* ``input_lease()`` -- só um processo por vez mexe no mouse/teclado: dois agentes (ou o
  agente e um robô) digitando juntos misturam as teclas. Trava entre processos, com prazo.

Ideias do agent-desktop (Vercel Labs, Apache-2.0): ``input/elevation.rs`` (o portão de
integridade), o teste de ponto antes do clique físico, ``input/blocked_combo.rs`` (a lista
e a regra do superconjunto de modificadores) e a trava de interação.
"""

from __future__ import annotations

import contextlib
import os
import sys
import time
from pathlib import Path

# --- UIPI ---------------------------------------------------------------------

_TOKEN_QUERY = 0x0008
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_TOKEN_INTEGRITY_LEVEL = 25


def _token_integrity(token) -> int | None:
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
    size = wintypes.DWORD(0)
    advapi32.GetTokenInformation(token, _TOKEN_INTEGRITY_LEVEL, None, 0, ctypes.byref(size))
    if not size.value:
        return None
    buf = ctypes.create_string_buffer(size.value)
    if not advapi32.GetTokenInformation(
        token, _TOKEN_INTEGRITY_LEVEL, buf, size, ctypes.byref(size)
    ):
        return None
    sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]  # TOKEN_MANDATORY_LABEL.Label.Sid
    advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
    count = advapi32.GetSidSubAuthorityCount(ctypes.c_void_p(sid)).contents.value
    if not count:
        return None
    return int(advapi32.GetSidSubAuthority(ctypes.c_void_p(sid), count - 1).contents.value)


def process_integrity(pid: int | None = None) -> int | None:
    """O nível de integridade (RID: 0x2000 médio, 0x3000 alto/admin) de ``pid`` -- ou deste
    processo. None quando não dá para saber (fora do Windows, sem acesso)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        advapi32 = ctypes.windll.advapi32  # type: ignore[attr-defined]
        # tipos explícitos: sem eles o pseudo-handle -1 do processo vira 32 bits no 64
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
        ]
        advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        if pid is None:
            process, owned = kernel32.GetCurrentProcess(), False
        else:
            process = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            owned = True
            if not process:
                return None
        try:
            token = wintypes.HANDLE()
            if not advapi32.OpenProcessToken(process, _TOKEN_QUERY, ctypes.byref(token)):
                return None
            try:
                return _token_integrity(token)
            finally:
                kernel32.CloseHandle(token)
        finally:
            if owned:
                kernel32.CloseHandle(process)
    except Exception:
        return None


def integrity_permits_input(caller: int | None, target: int | None) -> bool:
    """A regra (pura): a entrada só desce ou fica no mesmo nível. Sem saber, permite."""
    return caller is None or target is None or target <= caller


def uipi_blocks(pid: int | None) -> bool:
    """True quando o Windows vai descartar a entrada física para ``pid`` (UIPI)."""
    try:
        target = int(pid) if pid else 0
    except (TypeError, ValueError):
        return False
    if not target:
        return False
    return not integrity_permits_input(process_integrity(), process_integrity(target))


UIPI_REASON = (
    "the program runs as administrator and this one does not -- Windows drops the "
    "mouse/keyboard silently; run visus-desktop as administrator too"
)


def pid_at(x: int, y: int) -> int | None:
    """O processo dono da janela sob o ponto ``(x, y)`` da tela, ou None."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        hit = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        return _root_and_pid(int(hit))[1] if hit else None
    except Exception:
        return None


# --- janela por cima ------------------------------------------------------------

def _root_and_pid(hwnd: int) -> tuple[int, int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    user32.GetAncestor.restype = wintypes.HWND
    root = user32.GetAncestor(ctypes.c_void_p(int(hwnd)), 2) or hwnd  # GA_ROOT
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(ctypes.c_void_p(int(root)), ctypes.byref(pid))
    return int(root), int(pid.value)


def covering_window(hwnd: int | None, x: int, y: int) -> str | None:
    """O título da janela de OUTRO programa que está sobre o ponto ``(x, y)`` da janela
    ``hwnd`` -- None quando o ponto é da janela (ou de um popup/menu do mesmo programa) ou
    quando não dá para saber."""
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.IsWindow(ctypes.c_void_p(int(hwnd))):
            return None  # sem janela para comparar: não dá para saber, segue
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        hit = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hit:
            return None
        hit_root, hit_pid = _root_and_pid(int(hit))
        own_root, own_pid = _root_and_pid(int(hwnd))
        if hit_root == own_root or hit_pid == own_pid:
            return None
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(ctypes.c_void_p(hit_root), buf, 256)
        return buf.value or "another window"
    except Exception:
        return None


# --- atalhos perigosos -------------------------------------------------------------

# tiram o foco da execução ou mudam a sessão (Ctrl+Alt+Del não: o SendInput nem consegue)
BLOCKED_COMBOS = (
    "alt+f4",
    "win+l",
    "win+d",
    "alt+tab",
    "win+r",
    "win+x",
    "win+e",
    "ctrl+shift+esc",
)
_MOD_ALIASES = {
    "control": "ctrl", "ctl": "ctrl", "windows": "win", "super": "win", "meta": "win",
    "cmd": "win", "command": "win", "lwin": "win", "rwin": "win", "option": "alt",
    "menu": "alt",
}
_KEY_ALIASES = {"escape": "esc", "return": "enter", "del": "delete"}
_MODS = {"ctrl", "alt", "shift", "win"}


def _canonical(combo: str) -> tuple[frozenset[str], str] | None:
    parts = [p.strip().lower().replace(" ", "") for p in combo.split("+")]
    if not parts or not all(parts):
        return None
    mods = {_MOD_ALIASES.get(p, p) for p in parts[:-1]}
    key = _MOD_ALIASES.get(parts[-1], parts[-1])
    key = _KEY_ALIASES.get(key, key)
    return frozenset(mods), key


def blocked_combo(keys: str) -> str | None:
    """O atalho perigoso contido em ``keys`` (``"Alt+F4"``, ``"Ctrl, Alt+Tab"``...), ou None.

    Os modificadores de ``keys`` só precisam CONTER os do atalho: Alt+Shift+Tab troca de
    janela como o Alt+Tab, e uma comparação exata deixaria passar."""
    for step in str(keys or "").split(","):
        found = _canonical(step)
        if found is None:
            continue
        mods, key = found
        for entry in BLOCKED_COMBOS:
            blocked_mods, blocked_key = _canonical(entry)  # type: ignore[misc]
            if key == blocked_key and blocked_mods <= mods:
                return entry
    return None


# --- uma entrada física por vez ---------------------------------------------------

LEASE_TIMEOUT = 15.0


class InputBusy(Exception):
    """Outro processo está usando o mouse/teclado e não soltou dentro do prazo."""


def _lease_path() -> Path:
    config = os.environ.get("VISUS_CONFIG")
    base = Path(config).parent if config else Path.home() / ".visus" / "desktop"
    return base / "input.lock"


@contextlib.contextmanager
def input_lease(timeout: float = LEASE_TIMEOUT):
    """Segura o mouse/teclado para este processo enquanto o bloco roda (trava de arquivo
    entre processos; reentrante na mesma thread não é necessário: cada ação física pega
    e solta). ``InputBusy`` quando outro não solta em ``timeout`` s."""
    path = _lease_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(path, "a+b")  # noqa: SIM115 - fechado no finally
    except OSError:
        yield  # sem onde travar: segue sem a trava (proteção, não portão)
        return
    deadline = time.monotonic() + max(0.0, timeout)
    locked = False
    try:
        while True:
            try:
                _lock(handle)
                locked = True
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise InputBusy(
                        "another visus process is using the mouse/keyboard -- try again "
                        "when it finishes"
                    ) from None
                time.sleep(0.05)
        yield
    finally:
        if locked:
            with contextlib.suppress(OSError):
                _unlock(handle)
        handle.close()


def _lock(handle) -> None:
    handle.seek(0)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle) -> None:
    handle.seek(0)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
