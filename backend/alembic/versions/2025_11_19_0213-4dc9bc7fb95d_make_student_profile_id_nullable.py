"""make_student_profile_id_nullable

Revision ID: 4dc9bc7fb95d
Revises: 888c37d8e867
Create Date: 2025-11-19 02:13:42.699763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4dc9bc7fb95d'
down_revision = '888c37d8e867'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make student_profile_id nullable to support application-first workflow
    # Student profile will be created later when application reaches ENROLLED stage
    op.alter_column('application', 'student_profile_id',
                    existing_type=sa.UUID(),
                    nullable=True)


def downgrade() -> None:
    # Revert to NOT NULL (note: this will fail if there are NULL values)
    op.alter_column('application', 'student_profile_id',
                    existing_type=sa.UUID(),
                    nullable=False)
