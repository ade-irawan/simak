"""Skema awal: menjalankan db/schema.sql (sumber tunggal DDL)

Revision ID: 0001
Revises:
"""

from alembic import op
from app.core.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (get_settings().folder_db / "schema.sql").read_text(encoding="utf-8")
    # Lewat koneksi psycopg mentah tanpa parameter: DDL berisi '%' (format()) dan banyak pernyataan sekaligus.
    op.get_bind().connection.driver_connection.execute(sql)


def downgrade() -> None:
    raise NotImplementedError("Skema awal tidak dapat diturunkan; pulihkan dari cadangan.")
