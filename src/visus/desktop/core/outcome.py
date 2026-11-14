"""O que uma ação nativa diz sobre a entrega: chegou ou não chegou ao app.

A distinção que importa para um agente não é sucesso x falha, é **entregue x não
entregue**: uma ação que não chegou ao app pode ser repetida à vontade; uma que pode
ter chegado não -- repetir pode clicar, salvar ou enviar duas vezes. ``retry_safe``
diz isso de uma vez, para o agente nunca ter de adivinhar pelo texto do erro.

* ``not_delivered`` -- nada foi enviado ao app (janela sumiu, controle mudou, app
  travado antes do envio). Repetir é seguro.
* ``delivered`` -- enviado, mas o efeito não foi conferido (um clique: nada para reler).
* ``verified`` -- enviado e o estado relido bate com o pedido.
* ``uncertain`` -- pode ter chegado (o tempo acabou depois do envio, erro no meio).
  Leia o estado antes de decidir.

Ideia trazida do agent-desktop (Vercel Labs, Apache-2.0): ``DeliverySemantics`` em
``crates/core/src/actions/delivery_semantics.rs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NOT_DELIVERED = "not_delivered"
DELIVERED = "delivered"
VERIFIED = "verified"
UNCERTAIN = "uncertain"


@dataclass
class ActionOutcome:
    """Resultado de uma ação nativa: ``ok`` + como ela chegou (ou não) ao app."""

    ok: bool
    delivery: str
    reason: str = ""
    method: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Verdadeiro quando deu certo -- ``if native_toggle(...):`` e o relatório do
        ``rpa()`` (um resultado falso para o robô) funcionam como com os ``bool``."""
        return self.ok

    @property
    def retry_safe(self) -> bool:
        """Só o que não foi entregue pode ser repetido sem risco de duplicar."""
        return self.delivery == NOT_DELIVERED

    @classmethod
    def not_sent(cls, reason: str, **details: Any) -> ActionOutcome:
        return cls(ok=False, delivery=NOT_DELIVERED, reason=reason, details=details)

    @classmethod
    def sent(cls, method: str, *, verified: bool | None = None, **details: Any) -> ActionOutcome:
        """Enviado por ``method``. ``verified`` True = relido e confere; False = relido e
        NÃO confere (falha depois de entregar); None = nada para reler."""
        if verified is False:
            return cls(
                ok=False, delivery=UNCERTAIN, method=method,
                reason="sent, but the control did not change as asked", details=details,
            )
        return cls(
            ok=True, delivery=VERIFIED if verified else DELIVERED, method=method, details=details
        )

    @classmethod
    def maybe_sent(cls, reason: str, method: str = "", **details: Any) -> ActionOutcome:
        return cls(ok=False, delivery=UNCERTAIN, reason=reason, method=method, details=details)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "delivery": self.delivery,
            "retry_safe": self.retry_safe,
        }
        if self.method:
            out["method"] = self.method
        if self.reason:
            out["reason"] = self.reason
        out.update(self.details)
        return out

    def human(self, success: str) -> str:
        """Uma linha para quem lê (o agente): o que aconteceu e se pode repetir."""
        if self.ok:
            how = f" ({self.method})" if self.method else ""
            check = ", checked" if self.delivery == VERIFIED else ""
            return f"{success}{how}{check}"
        if self.retry_safe:
            return f"not sent: {self.reason} -- nothing reached the app, safe to retry"
        return (
            f"{self.reason} -- it MAY have reached the app: read the state "
            "(native get-state / snapshot) before trying again"
        )
