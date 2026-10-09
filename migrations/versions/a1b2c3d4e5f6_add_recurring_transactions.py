"""add recurring_transactions table

Revision ID: a1b2c3d4e5f6
Revises: 8178de17f2e3
Create Date: 2026-10-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8178de17f2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('recurring_transactions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=10), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('note', sa.String(length=255), nullable=True),
    sa.Column('frequency', sa.String(length=10), nullable=False),
    sa.Column('next_date', sa.Date(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_recurring_transactions_user_id'), ['user_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_recurring_transactions_next_date'), ['next_date'], unique=False)


def downgrade():
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recurring_transactions_next_date'))
        batch_op.drop_index(batch_op.f('ix_recurring_transactions_user_id'))

    op.drop_table('recurring_transactions')
