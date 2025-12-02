"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


CallStatus = sa.Enum(
    'IN_QUEUE', 'MISSED', 'CONNECTED', 'FAILED', 'NOT_INTERESTED',
    name='callstatus'
)

def upgrade() -> None:
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
    op.create_index(op.f('ix_admin_users_username'), 'admin_users', ['username'], unique=True)

    op.create_table(
        'dialer_batches',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('requested_size', sa.Integer(), nullable=False),
        sa.Column('returned_size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'schedule_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('skip_holidays', sa.Boolean(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'schedule_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedule_windows_day_of_week'), 'schedule_windows', ['day_of_week'], unique=False)

    op.create_table(
        'phone_numbers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('status', CallStatus, nullable=False, server_default='IN_QUEUE'),
        sa.Column('total_attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status_change_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_batch_id', sa.String(length=64), nullable=True),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index(op.f('ix_phone_numbers_id'), 'phone_numbers', ['id'], unique=False)
    op.create_index(op.f('ix_phone_numbers_phone_number'), 'phone_numbers', ['phone_number'], unique=True)

    op.create_table(
        'call_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['phone_number_id'], ['phone_numbers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_call_attempts_phone_number_id'), 'call_attempts', ['phone_number_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_call_attempts_phone_number_id'), table_name='call_attempts')
    op.drop_table('call_attempts')
    op.drop_index(op.f('ix_phone_numbers_phone_number'), table_name='phone_numbers')
    op.drop_index(op.f('ix_phone_numbers_id'), table_name='phone_numbers')
    op.drop_table('phone_numbers')
    op.drop_index(op.f('ix_schedule_windows_day_of_week'), table_name='schedule_windows')
    op.drop_table('schedule_windows')
    op.drop_table('schedule_configs')
    op.drop_table('dialer_batches')
    op.drop_index(op.f('ix_admin_users_username'), table_name='admin_users')
    op.drop_index(op.f('ix_admin_users_id'), table_name='admin_users')
    op.drop_table('admin_users')
    op.execute('DROP TYPE callstatus')
