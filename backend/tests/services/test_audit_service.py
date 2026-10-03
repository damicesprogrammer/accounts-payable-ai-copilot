from sqlalchemy import func, select

from app.models import LogAuditoria, StatusLog, TipoLog
from app.services.audit_service import AuditService


def test_registrar_log_sem_titulo(db):
    log = AuditService(db).registrar(TipoLog.CADASTRO, "Fornecedor cadastrado")

    assert log.id is not None
    assert log.status == StatusLog.SUCESSO
    assert log.created_at is not None


def test_log_e_descartado_quando_a_transacao_falha(db):
    """Regra 7: o log participa da transação da operação auditada."""
    AuditService(db).registrar(TipoLog.CADASTRO, "operação que vai falhar")
    db.rollback()

    total = db.scalar(select(func.count()).select_from(LogAuditoria))
    assert total == 0
