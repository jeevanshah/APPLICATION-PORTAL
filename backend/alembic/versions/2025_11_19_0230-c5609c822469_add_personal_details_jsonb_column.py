"""add_personal_details_jsonb_column

Revision ID: c5609c822469
Revises: 4dc9bc7fb95d
Create Date: 2025-11-19 02:30:03.526099

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5609c822469'
down_revision = '4dc9bc7fb95d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add personal_details JSONB column to match other step columns
    op.add_column('application', sa.Column('personal_details', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create GIN index for fast JSONB queries
    op.create_index('ix_application_personal_details', 'application', ['personal_details'], postgresql_using='gin')
    
    # Migrate existing data from form_metadata.personal_details to new column
    op.execute("""
        UPDATE application 
        SET personal_details = form_metadata->'personal_details'
        WHERE form_metadata ? 'personal_details'
    """)
    
    # Remove personal_details from form_metadata (keep only metadata tracking fields)
    op.execute("""
        UPDATE application 
        SET form_metadata = form_metadata - 'personal_details'
        WHERE form_metadata ? 'personal_details'
    """)


def downgrade() -> None:
    # Move data back to form_metadata before dropping column
    op.execute("""
        UPDATE application 
        SET form_metadata = jsonb_set(
            COALESCE(form_metadata, '{}'::jsonb),
            '{personal_details}',
            personal_details
        )
        WHERE personal_details IS NOT NULL
    """)
    
    # Drop index and column
    op.drop_index('ix_application_personal_details', table_name='application')
    op.drop_column('application', 'personal_details')
