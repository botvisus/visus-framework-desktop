"""Onde moram os snapshots numerados (``native snapshot``) e como um número volta a eles.

Antes havia UM arquivo global (``last-snapshot.json``): duas abas do agente, ou um
robô e o agente ao mesmo tempo, sobrescreviam o snapshot uma da outra, e
``native click 3`` clicava no item 3 da OUTRA janela. Agora:

* cada snapshot ganha um id curto (``s1a2b3``) e é guardado num arquivo próprio;
* o diretório é por **sessão** -- ``VISUS_DESKTOP_SESSION`` (o Visus Studio põe uma
  por conversa/aba); sem ela, ``default``;
* ``3`` vale o item 3 do último snapshot da sessão; ``s1a2b3:3`` vale o item 3 daquele
  snapshot, mesmo que outro tenha vindo depois.

Ideia do agent-desktop (Vercel Labs, Apache-2.0): refs qualificadas pelo snapshot
(``@<snapshot_id>:eN``) e o armazenamento por sessão (``crates/core/src/refs/``).
"""

from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path
from typing import Any

SESSION_ENV = "VISUS_DESKTOP_SESSION"
MAX_SNAPSHOTS = 32

_SESSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_REF_RE = re.compile(r"^(?:(s[0-9a-f]{6}):)?(\d{1,6})$")


class SnapshotError(Exception):
    """O número não aponta para um snapshot guardado -- a mensagem diz o que fazer."""


def _base_dir() -> Path:
    """Ao lado de ``$VISUS_CONFIG`` quando definido (testes e perfis paralelos), senão
    ``~/.visus/desktop/``."""
    config = os.environ.get("VISUS_CONFIG")
    return Path(config).parent if config else Path.home() / ".visus" / "desktop"


def session_name() -> str:
    name = (os.environ.get(SESSION_ENV) or "").strip()
    return name if _SESSION_RE.match(name) else "default"


def snapshot_dir() -> Path:
    return _base_dir() / "snapshots" / session_name()


def is_ref(value: str) -> bool:
    """``3`` ou ``s1a2b3:3``."""
    return bool(_REF_RE.match(str(value).strip()))


def save_snapshot(snap: dict[str, Any]) -> str:
    """Guarda ``snap`` com um id novo, marca-o como o último da sessão e devolve o id."""
    directory = snapshot_dir()
    directory.mkdir(parents=True, exist_ok=True)
    snapshot_id = "s" + secrets.token_hex(3)
    body = dict(snap, snapshot_id=snapshot_id)
    (directory / f"{snapshot_id}.json").write_text(
        json.dumps(body, ensure_ascii=False), encoding="utf-8"
    )
    (directory / "latest").write_text(snapshot_id, encoding="utf-8")
    _prune(directory, keep=snapshot_id)
    return snapshot_id


def _prune(directory: Path, *, keep: str) -> None:
    files = sorted(directory.glob("s*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[MAX_SNAPSHOTS:]:
        if stale.stem != keep:
            try:
                stale.unlink()
            except OSError:
                pass


def load_ref(ref: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(snapshot, item)`` do número ``ref``, ou ``SnapshotError`` com o próximo passo."""
    match = _REF_RE.match(str(ref).strip())
    if not match:
        raise SnapshotError(
            f"{ref!r} is not a snapshot number -- use the number `native snapshot` printed "
            "(3, or s1a2b3:3)"
        )
    snapshot_id, index = match.group(1), int(match.group(2))
    directory = snapshot_dir()
    if snapshot_id is None:
        try:
            snapshot_id = (directory / "latest").read_text(encoding="utf-8").strip()
        except OSError:
            raise SnapshotError(
                "no snapshot yet — run `native snapshot --window <title>` first, then act by number"
            ) from None
    try:
        snap = json.loads((directory / f"{snapshot_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SnapshotError(
            f"snapshot {snapshot_id} is gone — run `native snapshot` again"
        ) from None
    items = snap.get("items") or []
    if not 0 <= index < len(items):
        raise SnapshotError(
            f"index {index} is not in snapshot {snapshot_id} ({len(items)} items) — "
            "run `native snapshot` again"
        )
    return snap, items[index]
