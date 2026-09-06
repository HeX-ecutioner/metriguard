"""Enforce one image per inspection via unique constraint on package_images.inspection_id

Revision ID: 003_one_image_per_inspection
Revises: 002_inspection_workflow_models
Create Date: 2026-09-06 21:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_one_image_per_inspection'
down_revision: Union[str, None] = '002_inspection_workflow_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'package_images' in existing_tables:
        # 1. Preserve existing history: For any legacy duplicate images attached to the
        # same inspection session, create a dedicated inspection record so NO data is lost.
        duplicates = conn.execute(sa.text("""
            SELECT inspection_id, id FROM package_images
            ORDER BY inspection_id, id
        """)).fetchall()

        seen_inspections = set()
        for insp_id, img_id in duplicates:
            if insp_id not in seen_inspections:
                seen_inspections.add(insp_id)
            else:
                # Fetch parent inspection metadata
                parent_insp = conn.execute(sa.text("""
                    SELECT status, product_name, overall_confidence, notes
                    FROM inspections WHERE id = :id
                """), {"id": insp_id}).fetchone()

                conn.execute(sa.text("""
                    INSERT INTO inspections (status, product_name, overall_confidence, notes, created_at, updated_at)
                    VALUES (:status, :product_name, :overall_confidence, :notes, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {
                    "status": parent_insp[0] if parent_insp else "COMPLETED",
                    "product_name": parent_insp[1] if parent_insp else None,
                    "overall_confidence": parent_insp[2] if parent_insp else None,
                    "notes": (parent_insp[3] or "") + " (Preserved historical session)",
                })
                new_insp_id = conn.execute(sa.text("SELECT last_insert_rowid()")).scalar()

                # Reassign image to the new inspection session
                conn.execute(sa.text("""
                    UPDATE package_images SET inspection_id = :new_id WHERE id = :img_id
                """), {"new_id": new_insp_id, "img_id": img_id})

                # Reassign declarations originating from this image
                conn.execute(sa.text("""
                    UPDATE declarations SET inspection_id = :new_id WHERE source_image_id = :img_id
                """), {"new_id": new_insp_id, "img_id": img_id})

                # Reassign violations originating from this image
                conn.execute(sa.text("""
                    UPDATE violations SET inspection_id = :new_id WHERE evidence_image_id = :img_id
                """), {"new_id": new_insp_id, "img_id": img_id})

        # 2. Now that every package_image is mapped to a unique inspection_id, enforce unique index
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('package_images')]
        with op.batch_alter_table('package_images') as batch_op:
            if 'ix_package_images_inspection_id' in existing_indexes:
                batch_op.drop_index('ix_package_images_inspection_id')
            batch_op.create_index('ix_package_images_inspection_id', ['inspection_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'package_images' in existing_tables:
        with op.batch_alter_table('package_images') as batch_op:
            batch_op.drop_index('ix_package_images_inspection_id')
            batch_op.create_index('ix_package_images_inspection_id', ['inspection_id'], unique=False)
