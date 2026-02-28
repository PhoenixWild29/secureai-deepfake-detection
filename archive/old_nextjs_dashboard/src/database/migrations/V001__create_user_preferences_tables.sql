-- Migration: Create User Preferences Tables
-- Version: V001
-- Description: Create tables for user dashboard preferences management
-- Created: 2025-01-15

-- Create user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    preferences_data JSONB NOT NULL DEFAULT '{}',
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Constraints
    CONSTRAINT chk_role CHECK (role IN ('admin', 'analyst', 'viewer', 'security_officer', 'compliance_manager', 'system_admin')),
    CONSTRAINT chk_version CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    CONSTRAINT chk_user_id_length CHECK (LENGTH(user_id) > 0 AND LENGTH(user_id) <= 255),
    CONSTRAINT uq_user_preferences_user_id UNIQUE (user_id)
);

-- Create user_preferences_history table for audit trail
CREATE TABLE IF NOT EXISTS user_preferences_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    preferences_data JSONB NOT NULL DEFAULT '{}',
    action VARCHAR(20) NOT NULL,
    changed_by VARCHAR(255) NOT NULL,
    change_reason TEXT,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_action CHECK (action IN ('create', 'update', 'delete', 'restore')),
    CONSTRAINT chk_version_history CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    CONSTRAINT chk_user_id_history_length CHECK (LENGTH(user_id) > 0 AND LENGTH(user_id) <= 255),
    CONSTRAINT chk_changed_by_length CHECK (LENGTH(changed_by) > 0 AND LENGTH(changed_by) <= 255)
);

-- Create indexes for user_preferences table
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_role ON user_preferences(role);
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at);
CREATE INDEX IF NOT EXISTS idx_user_preferences_active ON user_preferences(is_active);
CREATE INDEX IF NOT EXISTS idx_user_preferences_version ON user_preferences(version);

-- Create indexes for user_preferences_history table
CREATE INDEX IF NOT EXISTS idx_user_preferences_history_user_id ON user_preferences_history(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_history_created_at ON user_preferences_history(created_at);
CREATE INDEX IF NOT EXISTS idx_user_preferences_history_action ON user_preferences_history(action);
CREATE INDEX IF NOT EXISTS idx_user_preferences_history_changed_by ON user_preferences_history(changed_by);

-- Create GIN indexes for JSONB columns for better query performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_data_gin ON user_preferences USING GIN(preferences_data);
CREATE INDEX IF NOT EXISTS idx_user_preferences_history_data_gin ON user_preferences_history USING GIN(preferences_data);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER trigger_update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_user_preferences_updated_at();

-- Create function to insert history record on preferences changes
CREATE OR REPLACE FUNCTION log_user_preferences_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO user_preferences_history (
            user_id,
            preferences_data,
            action,
            changed_by,
            version
        ) VALUES (
            NEW.user_id,
            NEW.preferences_data,
            'create',
            NEW.user_id,
            NEW.version
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO user_preferences_history (
            user_id,
            preferences_data,
            action,
            changed_by,
            version
        ) VALUES (
            NEW.user_id,
            NEW.preferences_data,
            'update',
            NEW.user_id,
            NEW.version
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO user_preferences_history (
            user_id,
            preferences_data,
            action,
            changed_by,
            version
        ) VALUES (
            OLD.user_id,
            OLD.preferences_data,
            'delete',
            OLD.user_id,
            OLD.version
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to log changes to history table
CREATE TRIGGER trigger_log_user_preferences_change
    AFTER INSERT OR UPDATE OR DELETE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION log_user_preferences_change();

-- Create function to clean up old history records (older than 1 year)
CREATE OR REPLACE FUNCTION cleanup_old_preferences_history()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_preferences_history 
    WHERE created_at < NOW() - INTERVAL '1 year';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get default preferences for a role
CREATE OR REPLACE FUNCTION get_default_preferences_for_role(user_role VARCHAR(50))
RETURNS JSONB AS $$
DECLARE
    default_prefs JSONB;
BEGIN
    CASE user_role
        WHEN 'admin' THEN
            default_prefs := '{
                "widgets": [
                    {
                        "widget_id": "system_overview",
                        "widget_type": "system_status",
                        "position_x": 0,
                        "position_y": 0,
                        "width": 6,
                        "height": 3,
                        "visible": true
                    },
                    {
                        "widget_id": "user_management",
                        "widget_type": "user_activity",
                        "position_x": 6,
                        "position_y": 0,
                        "width": 6,
                        "height": 3,
                        "visible": true
                    },
                    {
                        "widget_id": "performance_metrics",
                        "widget_type": "performance_metrics",
                        "position_x": 0,
                        "position_y": 3,
                        "width": 12,
                        "height": 4,
                        "visible": true
                    }
                ],
                "notifications": {
                    "enabled": true,
                    "types": ["email", "in_app"],
                    "frequency": "immediate",
                    "alert_types": ["system_alerts", "security_alerts", "user_alerts"]
                },
                "theme": {
                    "theme_type": "dark",
                    "primary_color": "#1976d2",
                    "secondary_color": "#424242",
                    "accent_color": "#ff4081"
                },
                "layout": {
                    "layout_type": "grid",
                    "grid_columns": 12,
                    "auto_save": true
                },
                "accessibility": {
                    "screen_reader": false,
                    "keyboard_navigation": true,
                    "focus_indicators": true
                },
                "version": "1.0.0"
            }'::JSONB;
        
        WHEN 'security_officer' THEN
            default_prefs := '{
                "widgets": [
                    {
                        "widget_id": "security_alerts",
                        "widget_type": "security_alerts",
                        "position_x": 0,
                        "position_y": 0,
                        "width": 8,
                        "height": 4,
                        "visible": true
                    },
                    {
                        "widget_id": "detection_summary",
                        "widget_type": "detection_summary",
                        "position_x": 8,
                        "position_y": 0,
                        "width": 4,
                        "height": 4,
                        "visible": true
                    },
                    {
                        "widget_id": "recent_activity",
                        "widget_type": "recent_activity",
                        "position_x": 0,
                        "position_y": 4,
                        "width": 12,
                        "height": 3,
                        "visible": true
                    }
                ],
                "notifications": {
                    "enabled": true,
                    "types": ["email", "in_app", "push"],
                    "frequency": "immediate",
                    "alert_types": ["security_alerts", "detection_alerts", "system_alerts"]
                },
                "theme": {
                    "theme_type": "dark",
                    "primary_color": "#d32f2f",
                    "secondary_color": "#424242",
                    "accent_color": "#ff9800"
                },
                "version": "1.0.0"
            }'::JSONB;
        
        WHEN 'compliance_manager' THEN
            default_prefs := '{
                "widgets": [
                    {
                        "widget_id": "compliance_reports",
                        "widget_type": "compliance_reports",
                        "position_x": 0,
                        "position_y": 0,
                        "width": 6,
                        "height": 4,
                        "visible": true
                    },
                    {
                        "widget_id": "export_history",
                        "widget_type": "export_history",
                        "position_x": 6,
                        "position_y": 0,
                        "width": 6,
                        "height": 4,
                        "visible": true
                    },
                    {
                        "widget_id": "analytics_chart",
                        "widget_type": "analytics_chart",
                        "position_x": 0,
                        "position_y": 4,
                        "width": 12,
                        "height": 3,
                        "visible": true
                    }
                ],
                "notifications": {
                    "enabled": true,
                    "types": ["email", "in_app"],
                    "frequency": "daily",
                    "alert_types": ["compliance_alerts", "export_alerts"]
                },
                "theme": {
                    "theme_type": "light",
                    "primary_color": "#388e3c",
                    "secondary_color": "#424242",
                    "accent_color": "#ffc107"
                },
                "version": "1.0.0"
            }'::JSONB;
        
        ELSE -- Default for viewer, analyst, etc.
            default_prefs := '{
                "widgets": [
                    {
                        "widget_id": "detection_summary",
                        "widget_type": "detection_summary",
                        "position_x": 0,
                        "position_y": 0,
                        "width": 6,
                        "height": 3,
                        "visible": true
                    },
                    {
                        "widget_id": "recent_activity",
                        "widget_type": "recent_activity",
                        "position_x": 6,
                        "position_y": 0,
                        "width": 6,
                        "height": 3,
                        "visible": true
                    }
                ],
                "notifications": {
                    "enabled": true,
                    "types": ["in_app"],
                    "frequency": "daily",
                    "alert_types": ["detection_alerts"]
                },
                "theme": {
                    "theme_type": "light",
                    "primary_color": "#1976d2",
                    "secondary_color": "#424242",
                    "accent_color": "#ff4081"
                },
                "version": "1.0.0"
            }'::JSONB;
    END CASE;
    
    RETURN default_prefs;
END;
$$ LANGUAGE plpgsql;

-- Create function to validate preferences data structure
CREATE OR REPLACE FUNCTION validate_preferences_data(prefs_data JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    widget_ids TEXT[];
    widget_id TEXT;
    i INTEGER;
BEGIN
    -- Check if preferences_data is valid JSON
    IF prefs_data IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check required top-level fields
    IF NOT (prefs_data ? 'version' AND prefs_data ? 'widgets' AND prefs_data ? 'theme') THEN
        RETURN FALSE;
    END IF;
    
    -- Check widgets array
    IF jsonb_typeof(prefs_data->'widgets') != 'array' THEN
        RETURN FALSE;
    END IF;
    
    -- Check for unique widget IDs
    SELECT ARRAY(
        SELECT jsonb_array_elements_text(
            jsonb_path_query_array(prefs_data->'widgets', '$[*].widget_id')
        )
    ) INTO widget_ids;
    
    FOR i IN 1..array_length(widget_ids, 1) LOOP
        FOR widget_id IN SELECT unnest(widget_ids[i+1:]) LOOP
            IF widget_ids[i] = widget_id THEN
                RETURN FALSE; -- Duplicate widget ID found
            END IF;
        END LOOP;
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add constraint to validate preferences data
ALTER TABLE user_preferences 
ADD CONSTRAINT chk_preferences_data_valid 
CHECK (validate_preferences_data(preferences_data));

-- Create view for active user preferences with role information
CREATE OR REPLACE VIEW active_user_preferences AS
SELECT 
    up.id,
    up.user_id,
    up.preferences_data,
    up.role,
    up.created_at,
    up.updated_at,
    up.version,
    up.is_active,
    -- Add computed fields
    jsonb_array_length(up.preferences_data->'widgets') as widget_count,
    up.preferences_data->'theme'->>'theme_type' as theme_type,
    up.preferences_data->'notifications'->>'enabled' as notifications_enabled
FROM user_preferences up
WHERE up.is_active = TRUE;

-- Create view for user preferences summary
CREATE OR REPLACE VIEW user_preferences_summary AS
SELECT 
    up.user_id,
    up.role,
    up.version,
    up.updated_at,
    up.is_active,
    jsonb_array_length(up.preferences_data->'widgets') as widget_count,
    up.preferences_data->'theme'->>'theme_type' as theme_type,
    up.preferences_data->'notifications'->>'enabled' as notifications_enabled,
    up.preferences_data->'notifications'->>'frequency' as notification_frequency,
    COUNT(h.id) as change_count,
    MAX(h.created_at) as last_change_date
FROM user_preferences up
LEFT JOIN user_preferences_history h ON up.user_id = h.user_id
WHERE up.is_active = TRUE
GROUP BY up.user_id, up.role, up.version, up.updated_at, up.is_active, 
         up.preferences_data->'widgets', up.preferences_data->'theme', 
         up.preferences_data->'notifications';

-- Insert some sample data for testing (optional)
-- Uncomment the following lines if you want to insert sample data

/*
INSERT INTO user_preferences (user_id, preferences_data, role) VALUES 
('admin-user-001', get_default_preferences_for_role('admin'), 'admin'),
('security-user-001', get_default_preferences_for_role('security_officer'), 'security_officer'),
('compliance-user-001', get_default_preferences_for_role('compliance_manager'), 'compliance_manager');
*/

-- Grant necessary permissions (adjust as needed for your security requirements)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO your_app_user;
-- GRANT SELECT ON user_preferences_history TO your_app_user;
-- GRANT SELECT ON active_user_preferences TO your_app_user;
-- GRANT SELECT ON user_preferences_summary TO your_app_user;
-- GRANT USAGE ON SCHEMA public TO your_app_user;

COMMENT ON TABLE user_preferences IS 'Stores user dashboard preferences with role-based customization';
COMMENT ON TABLE user_preferences_history IS 'Audit trail for user preferences changes';
COMMENT ON VIEW active_user_preferences IS 'View of active user preferences with computed fields';
COMMENT ON VIEW user_preferences_summary IS 'Summary view of user preferences with statistics';
COMMENT ON FUNCTION get_default_preferences_for_role(VARCHAR) IS 'Returns default preferences JSON for a given user role';
COMMENT ON FUNCTION validate_preferences_data(JSONB) IS 'Validates the structure and content of preferences data';
COMMENT ON FUNCTION cleanup_old_preferences_history() IS 'Cleans up old history records (older than 1 year)';
COMMENT ON FUNCTION log_user_preferences_change() IS 'Trigger function to log changes to preferences history';
COMMENT ON FUNCTION update_user_preferences_updated_at() IS 'Trigger function to update the updated_at timestamp';
