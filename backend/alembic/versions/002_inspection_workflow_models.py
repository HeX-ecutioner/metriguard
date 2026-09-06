"""Create inspection workflow entities (PackageImage, Declaration, Violation, InspectionResult)

Revision ID: 002_inspection_workflow_models
Revises: 001_initial_schema
Create Date: 2026-09-06 10:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_inspection_workflow_models'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Update inspections table with newly required domain fields
    if 'inspections' in existing_tables:
        existing_cols = [c['name'] for c in inspector.get_columns('inspections')]
        with op.batch_alter_table('inspections') as batch_op:
            if 'updated_at' not in existing_cols:
                batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))
            if 'product_name' not in existing_cols:
                batch_op.add_column(sa.Column('product_name', sa.String(length=255), nullable=True))
            if 'overall_confidence' not in existing_cols:
                batch_op.add_column(sa.Column('overall_confidence', sa.Float(), nullable=True))
            if 'notes' not in existing_cols:
                batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))

    # 2. Create package_images table
    if 'package_images' not in existing_tables:
        op.create_table(
            'package_images',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('inspection_id', sa.Integer(), sa.ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('file_path', sa.String(length=500), nullable=False),
            sa.Column('original_filename', sa.String(length=255), nullable=False),
            sa.Column('mime_type', sa.String(length=100), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index(op.f('ix_package_images_id'), 'package_images', ['id'], unique=False)
        op.create_index(op.f('ix_package_images_inspection_id'), 'package_images', ['inspection_id'], unique=False)

    # 3. Create declarations table
    if 'declarations' not in existing_tables:
        op.create_table(
            'declarations',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('inspection_id', sa.Integer(), sa.ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('declaration_type', sa.String(length=100), nullable=False),
            sa.Column('extracted_value', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('source_image_id', sa.Integer(), sa.ForeignKey('package_images.id', ondelete='SET NULL'), nullable=True),
            sa.Column('bounding_box', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index(op.f('ix_declarations_id'), 'declarations', ['id'], unique=False)
        op.create_index(op.f('ix_declarations_inspection_id'), 'declarations', ['inspection_id'], unique=False)
        op.create_index(op.f('ix_declarations_declaration_type'), 'declarations', ['declaration_type'], unique=False)
        op.create_index(op.f('ix_declarations_source_image_id'), 'declarations', ['source_image_id'], unique=False)

    # 4. Create violations table
    if 'violations' not in existing_tables:
        op.create_table(
            'violations',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('inspection_id', sa.Integer(), sa.ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('rule_id', sa.String(length=100), nullable=False),
            sa.Column('rule_version', sa.String(length=50), server_default='2011', nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('explanation', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=50), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('evidence_image_id', sa.Integer(), sa.ForeignKey('package_images.id', ondelete='SET NULL'), nullable=True),
            sa.Column('evidence_bounding_box', sa.Text(), nullable=True),
            sa.Column('measured_value', sa.String(length=255), nullable=True),
            sa.Column('expected_value', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index(op.f('ix_violations_id'), 'violations', ['id'], unique=False)
        op.create_index(op.f('ix_violations_inspection_id'), 'violations', ['inspection_id'], unique=False)
        op.create_index(op.f('ix_violations_rule_id'), 'violations', ['rule_id'], unique=False)
        op.create_index(op.f('ix_violations_severity'), 'violations', ['severity'], unique=False)
        op.create_index(op.f('ix_violations_evidence_image_id'), 'violations', ['evidence_image_id'], unique=False)

    # 5. Create inspection_results table
    if 'inspection_results' not in existing_tables:
        op.create_table(
            'inspection_results',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('inspection_id', sa.Integer(), sa.ForeignKey('inspections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('final_status', sa.String(length=50), nullable=False),
            sa.Column('summary', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index(op.f('ix_inspection_results_id'), 'inspection_results', ['id'], unique=False)
        op.create_index(op.f('ix_inspection_results_inspection_id'), 'inspection_results', ['inspection_id'], unique=True)


def downgrade() -> None:
    op.drop_table('inspection_results')
    op.drop_table('violations')
    op.drop_table('declarations')
    op.drop_table('package_images')

    with op.batch_alter_table('inspections') as batch_op:
        batch_op.drop_column('notes')
        batch_op.drop_column('overall_confidence')
        batch_op.drop_column('product_name')
        batch_op.drop_column('updated_at')
