"""refactor_timeline_to_comment_system

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-11-19 06:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename timeline_entry to comment and refactor for pure comment/chat system.
    
    Changes:
    - Rename table: timeline_entry → comment
    - Remove: entry_type, stage, event_payload, correlation_id (covered by ApplicationStageHistory & AuditLog)
    - Add: parent_id (threaded comments), is_internal, is_edited, edited_at
    - Add: content_metadata, reactions, read_by, edit_history (JSONB)
    - Make actor_id and actor_role NOT NULL (required for comments)
    """
    
    # 1. Rename table
    op.rename_table('timeline_entry', 'comment')
    
    # 2. Rename columns: actor -> author, message -> content
    op.alter_column('comment', 'actor_id', new_column_name='author_id')
    op.alter_column('comment', 'actor_role', new_column_name='author_role')
    op.alter_column('comment', 'message', new_column_name='content')
    
    # 3. Add new columns for comment/chat features
    op.add_column('comment', sa.Column('parent_id', UUID(as_uuid=True), nullable=True))
    op.add_column('comment', sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('comment', sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('comment', sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.add_column('comment', sa.Column('content_metadata', JSONB, nullable=True))
    op.add_column('comment', sa.Column('reactions', JSONB, nullable=True))
    op.add_column('comment', sa.Column('read_by', JSONB, nullable=True))
    op.add_column('comment', sa.Column('edit_history', JSONB, nullable=True))
    
    # 4. Add foreign key for parent_id (self-referential for threaded comments)
    op.create_foreign_key(
        'fk_comment_parent',
        'comment', 'comment',
        ['parent_id'], ['id']
    )
    
    # 5. Add index for parent_id
    op.create_index('ix_comment_parent_id', 'comment', ['parent_id'])
    
    # 6. Make author_id and author_role NOT NULL (comments always have an author)
    # First, clean up any NULL values (should be none in practice)
    op.execute("DELETE FROM comment WHERE author_id IS NULL")
    op.alter_column('comment', 'author_id', nullable=False)
    op.alter_column('comment', 'author_role', nullable=False)
    
    # 7. Drop old system event columns (now handled by ApplicationStageHistory & AuditLog)
    op.drop_column('comment', 'entry_type')
    op.drop_column('comment', 'stage')
    op.drop_column('comment', 'event_payload')
    op.drop_column('comment', 'correlation_id')
    
    # 8. Drop old index if it exists
    op.execute("""
        DROP INDEX IF EXISTS idx_timeline_event_payload
    """)
    
    # 9. Create new JSONB indexes
    op.execute("""
        CREATE INDEX idx_comment_content_metadata ON comment 
        USING gin (content_metadata)
    """)
    op.execute("""
        CREATE INDEX idx_comment_reactions ON comment 
        USING gin (reactions)
    """)


def downgrade() -> None:
    """
    Revert comment back to timeline_entry with system events model.
    """
    
    # 1. Drop new indexes
    op.drop_index('idx_comment_reactions', table_name='comment')
    op.drop_index('idx_comment_content_metadata', table_name='comment')
    
    # 2. Re-add old system event columns
    op.add_column('comment', sa.Column('entry_type', sa.String(50), nullable=True))
    op.add_column('comment', sa.Column('stage', sa.String(50), nullable=True))
    op.add_column('comment', sa.Column('event_payload', JSONB, nullable=True))
    op.add_column('comment', sa.Column('correlation_id', sa.String(100), nullable=True))
    
    # 3. Make author_id and author_role nullable again (reverting from comment requirement)
    op.alter_column('comment', 'author_id', nullable=True)
    op.alter_column('comment', 'author_role', nullable=True)
    
    # 4. Rename columns back: author -> actor, content -> message
    op.alter_column('comment', 'author_id', new_column_name='actor_id')
    op.alter_column('comment', 'author_role', new_column_name='actor_role')
    op.alter_column('comment', 'content', new_column_name='message')
    
    # 5. Drop parent_id foreign key and index
    op.drop_index('ix_comment_parent_id', table_name='comment')
    op.drop_constraint('fk_comment_parent', 'comment', type_='foreignkey')
    
    # 6. Drop new comment/chat columns
    op.drop_column('comment', 'edit_history')
    op.drop_column('comment', 'read_by')
    op.drop_column('comment', 'reactions')
    op.drop_column('comment', 'content_metadata')
    op.drop_column('comment', 'edited_at')
    op.drop_column('comment', 'is_edited')
    op.drop_column('comment', 'is_internal')
    op.drop_column('comment', 'parent_id')
    
    # 7. Rename table back
    op.rename_table('comment', 'timeline_entry')
    
    # 8. Re-create old index
    op.execute("""
        CREATE INDEX idx_timeline_event_payload ON timeline_entry 
        USING gin (event_payload)
    """)
