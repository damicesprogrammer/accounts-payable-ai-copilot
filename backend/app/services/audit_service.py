from sqlalchemy.orm import Session

from app.models import LogAuditoria, StatusLog, TipoLog
from app.repositories.log_repository import LogRepository


class AuditService:
    """Registra a trilha de auditoria de negócio (regra 7).

    Nunca faz commit: o log entra na MESMA transação da operação auditada.
    Se a operação falhar e sofrer rollback, o log também é descartado — assim a
    auditoria nunca registra algo que não aconteceu.
    """

    def __init__(self, db: Session) -> None:
        self.repo = LogRepository(db)

    def registrar(
        self,
        tipo: TipoLog,
        mensagem: str,
        *,
        titulo_id: int | None = None,
        status: StatusLog = StatusLog.SUCESSO,
    ) -> LogAuditoria:
        return self.repo.add(
            LogAuditoria(titulo_id=titulo_id, tipo=tipo, status=status, mensagem=mensagem)
        )
