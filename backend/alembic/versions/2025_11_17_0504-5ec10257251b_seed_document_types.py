"""seed_document_types

Revision ID: 5ec10257251b
Revises: 98fd831bc63e
Create Date: 2025-11-17 05:04:11.587481

"""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '5ec10257251b'
down_revision = '98fd831bc63e'
branch_labels = None
depends_on = None


# Predefined UUIDs for common document types
DOC_TYPE_IDS = {
    'PASSPORT': '10000000-0000-0000-0000-000000000001',
    'TRANSCRIPT_SLC': '10000000-0000-0000-0000-000000000002',
    'TRANSCRIPT_HSC': '10000000-0000-0000-0000-000000000003',
    'ENGLISH_TEST': '10000000-0000-0000-0000-000000000004',
    'ID_CARD': '10000000-0000-0000-0000-000000000005',
    'BIRTH_CERTIFICATE': '10000000-0000-0000-0000-000000000006',
    'PREVIOUS_VISA': '10000000-0000-0000-0000-000000000007',
    'HEALTH_COVER': '10000000-0000-0000-0000-000000000008',
    'FINANCIAL_PROOF': '10000000-0000-0000-0000-000000000009',
    'RELATION_PROOF': '10000000-0000-0000-0000-000000000010',
    'TAX_INCOME': '10000000-0000-0000-0000-000000000011',
    'BUSINESS_INCOME': '10000000-0000-0000-0000-000000000012',
    'OTHER': '10000000-0000-0000-0000-000000000013',
}


def upgrade() -> None:
    """Seed common document types."""
    
    document_type_table = sa.table(
        'document_type',
        sa.column('id', sa.UUID),
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('stage', sa.String),
        sa.column('is_mandatory', sa.Boolean),
        sa.column('ocr_model_ref', sa.String),
        sa.column('display_order', sa.Integer),
    )
    
    document_types = [
        {
            'id': DOC_TYPE_IDS['PASSPORT'],
            'code': 'PASSPORT',
            'name': 'Passport',
            'stage': 'DRAFT',
            'is_mandatory': True,
            'ocr_model_ref': 'passport_ocr',
            'display_order': 1,
        },
        {
            'id': DOC_TYPE_IDS['TRANSCRIPT_SLC'],
            'code': 'TRANSCRIPT_SLC',
            'name': 'SLC Transcript',
            'stage': 'DRAFT',
            'is_mandatory': True,
            'ocr_model_ref': 'transcript_ocr',
            'display_order': 2,
        },
        {
            'id': DOC_TYPE_IDS['TRANSCRIPT_HSC'],
            'code': 'TRANSCRIPT_HSC',
            'name': 'HSC Transcript',
            'stage': 'DRAFT',
            'is_mandatory': True,
            'ocr_model_ref': 'transcript_ocr',
            'display_order': 3,
        },
        {
            'id': DOC_TYPE_IDS['ENGLISH_TEST'],
            'code': 'ENGLISH_TEST',
            'name': 'English Test Results (IELTS/TOEFL/PTE)',
            'stage': 'DRAFT',
            'is_mandatory': True,
            'ocr_model_ref': 'english_test_ocr',
            'display_order': 4,
        },
        {
            'id': DOC_TYPE_IDS['ID_CARD'],
            'code': 'ID_CARD',
            'name': 'National ID Card / Driver License',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': 'id_card_ocr',
            'display_order': 5,
        },
        {
            'id': DOC_TYPE_IDS['BIRTH_CERTIFICATE'],
            'code': 'BIRTH_CERTIFICATE',
            'name': 'Birth Certificate',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 6,
        },
        {
            'id': DOC_TYPE_IDS['PREVIOUS_VISA'],
            'code': 'PREVIOUS_VISA',
            'name': 'Previous Visa (if applicable)',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 7,
        },
        {
            'id': DOC_TYPE_IDS['HEALTH_COVER'],
            'code': 'HEALTH_COVER',
            'name': 'Overseas Student Health Cover',
            'stage': 'DRAFT',
            'is_mandatory': True,
            'ocr_model_ref': None,
            'display_order': 8,
        },
        {
            'id': DOC_TYPE_IDS['FINANCIAL_PROOF'],
            'code': 'FINANCIAL_PROOF',
            'name': 'Financial Proof (GS Requirement)',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 9,
        },
        {
            'id': DOC_TYPE_IDS['RELATION_PROOF'],
            'code': 'RELATION_PROOF',
            'name': 'Relation Proof (GS Requirement)',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 10,
        },
        {
            'id': DOC_TYPE_IDS['TAX_INCOME'],
            'code': 'TAX_INCOME',
            'name': 'Tax Income Documents (GS Requirement)',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 11,
        },
        {
            'id': DOC_TYPE_IDS['BUSINESS_INCOME'],
            'code': 'BUSINESS_INCOME',
            'name': 'Business Income Documents (GS Requirement)',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 12,
        },
        {
            'id': DOC_TYPE_IDS['OTHER'],
            'code': 'OTHER',
            'name': 'Other Documents',
            'stage': 'DRAFT',
            'is_mandatory': False,
            'ocr_model_ref': None,
            'display_order': 99,
        },
    ]
    
    op.bulk_insert(document_type_table, document_types)


def downgrade() -> None:
    """Remove seeded document types."""
    op.execute(
        sa.text(
            "DELETE FROM document_type WHERE id IN :ids"
        ).bindparams(
            sa.bindparam('ids', expanding=True)
        ),
        {"ids": list(DOC_TYPE_IDS.values())}
    )
