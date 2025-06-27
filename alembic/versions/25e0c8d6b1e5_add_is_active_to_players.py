"""add is_active to players

Revision ID: 25e0c8d6b1e5
Revises: c484b9b6d5cd
Create Date: 2025-05-25 12:29:09.171687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '25e0c8d6b1e5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ajouter la colonne sans contrainte NOT NULL
    op.add_column('players', sa.Column('is_active', sa.Boolean(), nullable=True))
    
    # 2. Mettre à jour toutes les lignes existantes
    op.execute("UPDATE players SET is_active = true")
    
    # 3. Modifier la colonne pour ajouter NOT NULL
    op.alter_column('players', 'is_active', nullable=False,
                   server_default=sa.text('true'))


def downgrade() -> None:
    op.drop_column('players', 'is_active')