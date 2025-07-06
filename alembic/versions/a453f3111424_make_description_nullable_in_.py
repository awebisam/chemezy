"""Make description nullable in ReactionCache

Revision ID: a453f3111424
Revises: c4f6ee7355e7
Create Date: 2025-07-08 18:41:36.396159

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'a453f3111424'
down_revision = 'c4f6ee7355e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('reaction_cache', schema=None) as batch_op:
        batch_op.alter_column('description',
                   existing_type=sa.VARCHAR(),
                   nullable=True,
                   existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('reaction_cache', schema=None) as batch_op:
        batch_op.alter_column('description',
                   existing_type=sa.VARCHAR(),
                   nullable=False,
                   existing_nullable=True)