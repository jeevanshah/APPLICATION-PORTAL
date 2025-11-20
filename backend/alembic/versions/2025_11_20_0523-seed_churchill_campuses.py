"""seed_churchill_campuses

Revision ID: seed_campuses_001
Revises: 12be2d72ba43
Create Date: 2025-11-20 05:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = 'seed_campuses_001'
down_revision = '12be2d72ba43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get Churchill RTO ID
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT id FROM rto_profile WHERE name = 'Churchill Education' LIMIT 1")
    )
    churchill_rto = result.fetchone()
    
    if not churchill_rto:
        print("Warning: Churchill Education RTO not found, skipping campus seeding")
        return
    
    rto_id = churchill_rto[0]
    
    # Seed campuses
    campuses = [
        {
            'id': uuid4(),
            'rto_profile_id': rto_id,
            'name': 'Sydney Campus',
            'code': 'SYD',
            'contact_email': 'admissions@churchill.nsw.edu.au',
            'contact_phone': '0288562997',
            'address': {
                'street': 'Level 1 & 7, 16-18 Wentworth Street',
                'city': 'Parramatta',
                'state': 'NSW',
                'postcode': '2150',
                'country': 'Australia'
            },
            'max_students': 500,
            'is_active': True
        },
        {
            'id': uuid4(),
            'rto_profile_id': rto_id,
            'name': 'Melbourne Campus',
            'code': 'MEL',
            'contact_email': 'admissions@churchill.nsw.edu.au',
            'contact_phone': '0288562997',
            'address': {
                'street': 'Level 8, 85 Queen Street',
                'city': 'Melbourne',
                'state': 'VIC',
                'postcode': '3000',
                'country': 'Australia'
            },
            'max_students': 400,
            'is_active': True
        }
    ]
    
    # Insert campuses
    campus_table = sa.table(
        'campus',
        sa.column('id', UUID),
        sa.column('rto_profile_id', UUID),
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('contact_email', sa.String),
        sa.column('contact_phone', sa.String),
        sa.column('address', JSONB),
        sa.column('max_students', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime)
    )
    
    from datetime import datetime
    for campus in campuses:
        op.execute(
            campus_table.insert().values(
                **campus,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
    
    print(f"✓ Seeded {len(campuses)} campuses for Churchill Education")


def downgrade() -> None:
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT id FROM rto_profile WHERE name = 'Churchill Education' LIMIT 1")
    )
    churchill_rto = result.fetchone()
    
    if churchill_rto:
        rto_id = churchill_rto[0]
        connection.execute(
            sa.text("DELETE FROM campus WHERE rto_profile_id = :rto_id"),
            {'rto_id': rto_id}
        )
