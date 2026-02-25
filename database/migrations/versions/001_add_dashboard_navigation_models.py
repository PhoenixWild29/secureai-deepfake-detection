"""Add dashboard navigation models

Revision ID: 001
Revises: 
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add dashboard navigation models and supporting enum types"""
    
    # Create enum types for navigation styles and activity types
    op.execute("CREATE TYPE navigationstyleenum AS ENUM ('sidebar', 'top_nav', 'breadcrumb', 'minimal')")
    op.execute("CREATE TYPE mobilenavigationstyleenum AS ENUM ('bottom_tab', 'drawer', 'top_tab', 'full_screen')")
    op.execute("CREATE TYPE activitytypeenum AS ENUM ('navigation', 'analysis', 'settings', 'authentication', 'system')")
    op.execute("CREATE TYPE navigationmethodenum AS ENUM ('click', 'keyboard', 'gesture', 'automatic', 'direct_url')")
    
    # Create user table
    op.create_table('user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for user table
    op.create_index('idx_user_email', 'user', ['email'])
    op.create_index('idx_user_active', 'user', ['is_active'])
    op.create_unique_constraint('uq_user_email', 'user', ['email'])
    
    # Create dashboard_session table
    op.create_table('dashboard_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_context', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_dashboard_session_user_id'),
    )
    
    # Create indexes for dashboard_session table
    op.create_index('idx_session_token', 'dashboard_session', ['session_token'])
    op.create_index('idx_session_user_id', 'dashboard_session', ['user_id'])
    op.create_index('idx_session_expires', 'dashboard_session', ['expires_at'])
    op.create_unique_constraint('uq_session_token', 'dashboard_session', ['session_token'])
    
    # Create user_preference table
    op.create_table('user_preference',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('default_landing_page', sa.String(255), nullable=False, default='/dashboard'),
        sa.Column('navigation_style', sa.Enum('sidebar', 'top_nav', 'breadcrumb', 'minimal', name='navigationstyleenum'), nullable=False, default='sidebar'),
        sa.Column('show_navigation_labels', sa.Boolean(), nullable=False, default=True),
        sa.Column('enable_keyboard_shortcuts', sa.Boolean(), nullable=False, default=True),
        sa.Column('mobile_navigation_style', sa.Enum('bottom_tab', 'drawer', 'top_tab', 'full_screen', name='mobilenavigationstyleenum'), nullable=False, default='bottom_tab'),
        sa.Column('accessibility_mode', sa.Boolean(), nullable=False, default=False),
        sa.Column('custom_navigation_order', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('theme_preference', sa.String(50), nullable=True),
        sa.Column('language_preference', sa.String(10), nullable=True),
        sa.Column('timezone_preference', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_user_preference_user_id'),
    )
    
    # Create indexes for user_preference table
    op.create_index('idx_preference_user_id', 'user_preference', ['user_id'])
    
    # Create user_activity table
    op.create_table('user_activity',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type', sa.Enum('navigation', 'analysis', 'settings', 'authentication', 'system', name='activitytypeenum'), nullable=False),
        sa.Column('activity_data', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_user_activity_user_id'),
        sa.ForeignKeyConstraint(['session_id'], ['dashboard_session.id'], name='fk_user_activity_session_id'),
    )
    
    # Create indexes for user_activity table
    op.create_index('idx_activity_user_id', 'user_activity', ['user_id'])
    op.create_index('idx_activity_type', 'user_activity', ['activity_type'])
    op.create_index('idx_activity_created_at', 'user_activity', ['created_at'])
    op.create_index('idx_activity_session_id', 'user_activity', ['session_id'])
    
    # Add comments to tables for documentation
    op.execute("COMMENT ON TABLE user IS 'User authentication and profile information'")
    op.execute("COMMENT ON TABLE dashboard_session IS 'Dashboard session management with navigation context storage'")
    op.execute("COMMENT ON TABLE user_preference IS 'User navigation and dashboard preferences'")
    op.execute("COMMENT ON TABLE user_activity IS 'User activity tracking including navigation performance data'")
    
    # Add comments to key columns
    op.execute("COMMENT ON COLUMN dashboard_session.session_context IS 'JSONB field storing navigation context including currentPath, navigationHistory, breadcrumbPreferences, sidebarCollapsed, favoriteRoutes, and lastVisitedSections'")
    op.execute("COMMENT ON COLUMN user_activity.activity_data IS 'JSONB field storing activity-specific data including navigationData for navigation activities'")
    op.execute("COMMENT ON COLUMN user_preference.custom_navigation_order IS 'Array of strings defining custom navigation menu order'")
    
    # Add comments to enum types
    op.execute("COMMENT ON TYPE navigationstyleenum IS 'Enumeration of supported navigation styles for dashboard'")
    op.execute("COMMENT ON TYPE mobilenavigationstyleenum IS 'Enumeration of supported mobile navigation styles'")
    op.execute("COMMENT ON TYPE activitytypeenum IS 'Enumeration of user activity types for tracking'")
    op.execute("COMMENT ON TYPE navigationmethodenum IS 'Enumeration of navigation methods for performance tracking'")


def downgrade():
    """Remove dashboard navigation models and supporting enum types"""
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('user_activity')
    op.drop_table('user_preference')
    op.drop_table('dashboard_session')
    op.drop_table('user')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS navigationmethodenum")
    op.execute("DROP TYPE IF EXISTS activitytypeenum")
    op.execute("DROP TYPE IF EXISTS mobilenavigationstyleenum")
    op.execute("DROP TYPE IF EXISTS navigationstyleenum")
