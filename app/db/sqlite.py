# app/db/sqlite.py
from agno.db.sqlite import AsyncSqliteDb

from app.configs.settings import settings

# Tüm agent'ler için ortak DB
agent_db = AsyncSqliteDb(
    db_file=settings.sqlite_db_file,
)
