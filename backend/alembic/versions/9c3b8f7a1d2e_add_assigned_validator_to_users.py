"""add assigned_validator to users

Revision ID: 9c3b8f7a1d2e
Revises: 321332d3af8b
Create Date: 2026-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c3b8f7a1d2e'
down_revision = '321332d3af8b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('assigned_validator', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'assigned_validator')
