"""Seed Churchill RTO profile

Revision ID: 98fd831bc63e
Revises: 1205e3db7232
Create Date: 2025-11-14 06:07:11.006801

"""
from datetime import datetime
import json
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98fd831bc63e'
down_revision = '1205e3db7232'
branch_labels = None
depends_on = None


CHURCHILL_ID = UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    """Insert Churchill Education RTO profile if it does not already exist."""
    conn = op.get_bind()
    now = datetime.utcnow()

    params = {
        "id": CHURCHILL_ID,
        "name": "Churchill Education",
        "abn": "12345678901",
        "cricos": "03089G",
        "email": "info@churchilleducation.edu.au",
        "phone": "+61 7 1234 5678",
        "address": json.dumps({
            "street": "1 Innovation Way",
            "city": "North Lakes",
            "state": "QLD",
            "postcode": "4509",
            "country": "Australia",
        }),
        "logo_url": None,
        "brand_settings": json.dumps({
            "primary_color": "#0F4C81",
            "secondary_color": "#F8B400",
            "font_family": "Inter, 'Segoe UI', sans-serif",
        }),
        "business_settings": json.dumps({
            "default_commission_rate": 0.15,
            "features_enabled": ["document_ai", "gs_assessment", "timeline_feed"],
        }),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    conn.execute(
        sa.text(
            """
            INSERT INTO rto_profile (
                id,
                name,
                abn,
                cricos_code,
                contact_email,
                contact_phone,
                address,
                logo_url,
                brand_settings,
                business_settings,
                is_active,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :name,
                :abn,
                :cricos,
                :email,
                :phone,
                :address,
                :logo_url,
                :brand_settings,
                :business_settings,
                :is_active,
                :created_at,
                :updated_at
            )
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                abn = EXCLUDED.abn,
                cricos_code = EXCLUDED.cricos_code,
                contact_email = EXCLUDED.contact_email,
                contact_phone = EXCLUDED.contact_phone,
                address = EXCLUDED.address,
                logo_url = EXCLUDED.logo_url,
                brand_settings = EXCLUDED.brand_settings,
                business_settings = EXCLUDED.business_settings,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at;
            """
        ),
        params,
    )


def downgrade() -> None:
    """Remove Churchill Education RTO profile."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM rto_profile WHERE id = :id"),
        {"id": CHURCHILL_ID},
    )
