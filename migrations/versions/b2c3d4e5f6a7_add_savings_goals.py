"""add savings_goals table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('savings_goals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('target_amount', sa.Float(), nullable=False),
    sa.Column('current_amount', sa.Float(), nullable=False, server_default='0'),
    sa.Column('target_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'name', name='uq_goal_user_name')
    )
    with op.batch_alter_table('savings_goals', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_savings_goals_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('savings_goals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_savings_goals_user_id'))
    op.drop_table('savings_goals')
