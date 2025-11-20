"""add_rto_profile_id_to_course_offering

Revision ID: a1b2c3d4e5f6
Revises: fd879e24637f
Create Date: 2025-11-19 06:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fd879e24637f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add rto_profile_id foreign key to course_offering table.
    Each course belongs to an RTO (multi-tenancy support).
    """
    
    # 1. Add rto_profile_id column (nullable initially for data migration)
    op.add_column('course_offering', 
                  sa.Column('rto_profile_id', UUID(as_uuid=True), nullable=True))
    
    # 2. Set default RTO profile ID for existing courses
    # Assuming Churchill RTO profile ID: 00000000-0000-0000-0000-000000000001
    op.execute("""
        UPDATE course_offering 
        SET rto_profile_id = '00000000-0000-0000-0000-000000000001'
        WHERE rto_profile_id IS NULL
    """)
    
    # 3. Make column non-nullable after migration
    op.alter_column('course_offering', 'rto_profile_id', nullable=False)
    
    # 4. Add foreign key constraint
    op.create_foreign_key(
        'fk_course_offering_rto_profile',
        'course_offering', 'rto_profile',
        ['rto_profile_id'], ['id']
    )
    
    # 5. Add index for performance
    op.create_index('ix_course_offering_rto_profile_id', 
                    'course_offering', ['rto_profile_id'])


def downgrade() -> None:
    """
    Remove rto_profile_id from course_offering table.
    """
    
    # 1. Drop index
    op.drop_index('ix_course_offering_rto_profile_id', table_name='course_offering')
    
    # 2. Drop foreign key
    op.drop_constraint('fk_course_offering_rto_profile', 'course_offering', type_='foreignkey')
    
    # 3. Drop column
    op.drop_column('course_offering', 'rto_profile_id')
