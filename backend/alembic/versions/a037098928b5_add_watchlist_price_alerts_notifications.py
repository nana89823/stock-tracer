"""add_watchlist_price_alerts_notifications

Revision ID: a037098928b5
Revises: 11acbb22d68f
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a037098928b5'
down_revision: Union[str, None] = '11acbb22d68f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # watchlists
    op.create_table('watchlists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.String(length=20), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.stock_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'stock_id', name='uq_watchlist_user_stock'),
    )
    op.create_index('ix_watchlist_user_id', 'watchlists', ['user_id'], unique=False)

    # price_alerts
    op.create_table('price_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stock_id', sa.String(length=20), nullable=False),
        sa.Column('condition_type', sa.String(length=10), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('is_triggered', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.stock_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_price_alerts_user_active', 'price_alerts', ['user_id', 'is_active'], unique=False)

    # notifications
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['alert_id'], ['price_alerts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_read', 'notifications', ['user_id', 'is_read'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_read', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_price_alerts_user_active', table_name='price_alerts')
    op.drop_table('price_alerts')
    op.drop_index('ix_watchlist_user_id', table_name='watchlists')
    op.drop_table('watchlists')
