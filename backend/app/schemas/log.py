from datetime import datetime

from app.models import StatusLog, TipoLog
from app.schemas.common import ReadSchema


class LogRead(ReadSchema):
    id: int
    titulo_id: int | None
    tipo: TipoLog
    status: StatusLog
    mensagem: str
    created_at: datetime
