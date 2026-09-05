"""Initial schema with inspections table and image storage path

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-06 01:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'inspections' not in tables:
        op.create_table(
            'inspections',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('status', sa.String(), nullable=True),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('extracted_texts_json', sa.String(), nullable=True),
            sa.Column('violations_json', sa.String(), nullable=True),
            sa.Column('image_path', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        )
        op.create_index(op.f('ix_inspections_id'), 'inspections', ['id'], unique=False)
        op.create_index(op.f('ix_inspections_status'), 'inspections', ['status'], unique=False)
    else:
        # Table exists: ensure image_path column is present
        columns = [col['name'] for col in inspector.get_columns('inspections')]
        if 'image_path' not in columns:
            with op.batch_alter_table('inspections') as batch_op:
                batch_op.add_column(sa.Column('image_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_index(op.f('ix_inspections_status'), table_name='inspections')
    op.drop_index(op.f('ix_inspections_id'), table_name='inspections')
    op.drop_table('inspections')
