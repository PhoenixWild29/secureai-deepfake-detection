-- Migration: Create Notification Tables
-- Version: V002
-- Description: Create tables for dashboard notifications management with real-time integration
-- Created: 2025-01-15

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Content fields
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    summary VARCHAR(500),
    details JSONB NOT NULL DEFAULT '{}',
    
    -- Action fields
    action_url TEXT,
    action_text VARCHAR(100),
    
    -- Delivery fields
    delivery_methods JSONB NOT NULL DEFAULT '["in_app"]',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata fields
    source VARCHAR(100),
    component VARCHAR(100),
    event_id VARCHAR(255),
    analysis_id VARCHAR(255),
    video_id VARCHAR(255),
    tags JSONB NOT NULL DEFAULT '[]',
    context JSONB NOT NULL DEFAULT '{}',
    
    -- Status tracking fields
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    
    -- Retry and error handling
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_notification_type CHECK (type IN (
        'analysis_completion', 'system_status', 'compliance_alert', 'security_alert',
        'user_activity', 'maintenance', 'performance_alert', 'blockchain_update',
        'export_completion', 'training_completion'
    )),
    CONSTRAINT chk_notification_category CHECK (category IN (
        'detection', 'security', 'system', 'compliance', 'user',
        'maintenance', 'performance', 'blockchain', 'export', 'training'
    )),
    CONSTRAINT chk_notification_priority CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT chk_notification_status CHECK (status IN (
        'pending', 'delivered', 'read', 'acknowledged', 'dismissed', 'failed'
    )),
    CONSTRAINT chk_retry_count CHECK (retry_count >= 0 AND retry_count <= 5),
    CONSTRAINT chk_max_retries CHECK (max_retries >= 0 AND max_retries <= 5),
    CONSTRAINT chk_title_length CHECK (LENGTH(title) > 0 AND LENGTH(title) <= 200),
    CONSTRAINT chk_message_length CHECK (LENGTH(message) > 0)
);

-- Create notification_history table for audit trail
CREATE TABLE IF NOT EXISTS notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL,
    user_id VARCHAR(255),
    action VARCHAR(20) NOT NULL,
    action_by VARCHAR(255) NOT NULL,
    action_reason TEXT,
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_notification_action CHECK (action IN (
        'acknowledge', 'dismiss', 'mark_read', 'mark_unread', 'archive', 'restore'
    )),
    CONSTRAINT chk_action_by_length CHECK (LENGTH(action_by) > 0 AND LENGTH(action_by) <= 255)
);

-- Create user_notification_preferences table
CREATE TABLE IF NOT EXISTS user_notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    
    -- Delivery preferences
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    delivery_methods JSONB NOT NULL DEFAULT '["in_app"]',
    email_address VARCHAR(255),
    phone_number VARCHAR(20),
    
    -- Category preferences
    enabled_categories JSONB NOT NULL DEFAULT '["detection", "security", "system"]',
    priority_filter VARCHAR(20) NOT NULL DEFAULT 'low',
    
    -- Timing preferences
    quiet_hours_start VARCHAR(5),
    quiet_hours_end VARCHAR(5),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    
    -- Advanced preferences
    batch_notifications BOOLEAN NOT NULL DEFAULT FALSE,
    digest_frequency VARCHAR(20) NOT NULL DEFAULT 'immediate',
    auto_dismiss_after INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_priority_filter CHECK (priority_filter IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT chk_digest_frequency CHECK (digest_frequency IN ('immediate', 'hourly', 'daily')),
    CONSTRAINT chk_user_id_length CHECK (LENGTH(user_id) > 0 AND LENGTH(user_id) <= 255),
    CONSTRAINT chk_auto_dismiss CHECK (auto_dismiss_after IS NULL OR (auto_dismiss_after > 0 AND auto_dismiss_after <= 168)), -- Max 1 week
    CONSTRAINT uq_user_notification_preferences_user_id UNIQUE (user_id)
);

-- Create indexes for notifications table
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_category ON notifications(category);
CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notifications(priority);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_delivered_at ON notifications(delivered_at);
CREATE INDEX IF NOT EXISTS idx_notifications_read_at ON notifications(read_at);
CREATE INDEX IF NOT EXISTS idx_notifications_expires_at ON notifications(expires_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_type_priority ON notifications(type, priority);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notifications_retry_count ON notifications(retry_count);

-- Create indexes for notification_history table
CREATE INDEX IF NOT EXISTS idx_notification_history_notification_id ON notification_history(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_user_id ON notification_history(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_action ON notification_history(action);
CREATE INDEX IF NOT EXISTS idx_notification_history_created_at ON notification_history(created_at);
CREATE INDEX IF NOT EXISTS idx_notification_history_action_by ON notification_history(action_by);

-- Create indexes for user_notification_preferences table
CREATE INDEX IF NOT EXISTS idx_user_notification_preferences_user_id ON user_notification_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notification_preferences_enabled ON user_notification_preferences(enabled);

-- Create GIN indexes for JSONB columns for better query performance
CREATE INDEX IF NOT EXISTS idx_notifications_details_gin ON notifications USING GIN(details);
CREATE INDEX IF NOT EXISTS idx_notifications_tags_gin ON notifications USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_notifications_context_gin ON notifications USING GIN(context);
CREATE INDEX IF NOT EXISTS idx_notification_history_metadata_gin ON notification_history USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_user_notification_preferences_delivery_methods_gin ON user_notification_preferences USING GIN(delivery_methods);
CREATE INDEX IF NOT EXISTS idx_user_notification_preferences_enabled_categories_gin ON user_notification_preferences USING GIN(enabled_categories);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notifications_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at timestamp for notifications
CREATE TRIGGER trigger_update_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_notifications_updated_at();

-- Create trigger to automatically update updated_at timestamp for user_notification_preferences
CREATE TRIGGER trigger_update_user_notification_preferences_updated_at
    BEFORE UPDATE ON user_notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_notifications_updated_at();

-- Create function to log notification actions
CREATE OR REPLACE FUNCTION log_notification_action()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Log status changes
        IF OLD.status != NEW.status THEN
            INSERT INTO notification_history (
                notification_id,
                user_id,
                action,
                action_by,
                previous_status,
                new_status,
                metadata
            ) VALUES (
                NEW.id,
                NEW.user_id,
                CASE 
                    WHEN NEW.status = 'read' THEN 'mark_read'
                    WHEN NEW.status = 'acknowledged' THEN 'acknowledge'
                    WHEN NEW.status = 'dismissed' THEN 'dismiss'
                    ELSE 'update'
                END,
                COALESCE(NEW.user_id, 'system'),
                OLD.status,
                NEW.status,
                jsonb_build_object(
                    'updated_at', NEW.updated_at,
                    'previous_values', jsonb_build_object(
                        'delivered_at', OLD.delivered_at,
                        'read_at', OLD.read_at,
                        'acknowledged_at', OLD.acknowledged_at,
                        'dismissed_at', OLD.dismissed_at
                    )
                )
            );
        END IF;
        
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to log notification status changes
CREATE TRIGGER trigger_log_notification_action
    AFTER UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION log_notification_action();

-- Create function to clean up expired notifications
CREATE OR REPLACE FUNCTION cleanup_expired_notifications()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    UPDATE notifications 
    SET status = 'dismissed', dismissed_at = NOW(), updated_at = NOW()
    WHERE expires_at IS NOT NULL 
      AND expires_at < NOW() 
      AND status IN ('pending', 'delivered', 'read');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get notification statistics for a user
CREATE OR REPLACE FUNCTION get_user_notification_stats(user_uuid VARCHAR(255))
RETURNS JSONB AS $$
DECLARE
    stats JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_notifications', COUNT(*),
        'unread_count', COUNT(*) FILTER (WHERE read_at IS NULL AND status NOT IN ('dismissed', 'failed')),
        'pending_count', COUNT(*) FILTER (WHERE status = 'pending'),
        'failed_count', COUNT(*) FILTER (WHERE status = 'failed'),
        'category_breakdown', (
            SELECT jsonb_object_agg(category, count)
            FROM (
                SELECT category, COUNT(*) as count
                FROM notifications 
                WHERE user_id = user_uuid OR user_id IS NULL
                GROUP BY category
            ) category_stats
        ),
        'priority_breakdown', (
            SELECT jsonb_object_agg(priority, count)
            FROM (
                SELECT priority, COUNT(*) as count
                FROM notifications 
                WHERE user_id = user_uuid OR user_id IS NULL
                GROUP BY priority
            ) priority_stats
        )
    ) INTO stats
    FROM notifications
    WHERE user_id = user_uuid OR user_id IS NULL;
    
    RETURN stats;
END;
$$ LANGUAGE plpgsql;

-- Create function to check if user should receive notification
CREATE OR REPLACE FUNCTION should_notify_user(
    user_uuid VARCHAR(255),
    notification_category VARCHAR(50),
    notification_priority VARCHAR(20)
)
RETURNS BOOLEAN AS $$
DECLARE
    user_prefs RECORD;
    priority_levels JSONB := '{"low": 1, "medium": 2, "high": 3, "critical": 4}'::jsonb;
    user_min_level INTEGER;
    notification_level INTEGER;
BEGIN
    -- Get user preferences
    SELECT * INTO user_prefs
    FROM user_notification_preferences
    WHERE user_id = user_uuid;
    
    -- If no preferences found, use defaults
    IF NOT FOUND THEN
        RETURN TRUE; -- Default to notify
    END IF;
    
    -- Check if notifications are enabled
    IF NOT user_prefs.enabled THEN
        RETURN FALSE;
    END IF;
    
    -- Check category filter
    IF NOT (user_prefs.enabled_categories ? notification_category) THEN
        RETURN FALSE;
    END IF;
    
    -- Check priority filter
    user_min_level := (priority_levels ->> user_prefs.priority_filter)::INTEGER;
    notification_level := (priority_levels ->> notification_priority)::INTEGER;
    
    IF notification_level < user_min_level THEN
        RETURN FALSE;
    END IF;
    
    -- Check quiet hours (simplified check - would need timezone handling in production)
    IF user_prefs.quiet_hours_start IS NOT NULL AND user_prefs.quiet_hours_end IS NOT NULL THEN
        IF EXTRACT(HOUR FROM NOW()) BETWEEN 
            EXTRACT(HOUR FROM user_prefs.quiet_hours_start::TIME) AND 
            EXTRACT(HOUR FROM user_prefs.quiet_hours_end::TIME) THEN
            RETURN FALSE;
        END IF;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Create function to get notifications for user with filtering
CREATE OR REPLACE FUNCTION get_user_notifications(
    user_uuid VARCHAR(255),
    limit_count INTEGER DEFAULT 50,
    offset_count INTEGER DEFAULT 0,
    category_filter VARCHAR(50) DEFAULT NULL,
    status_filter VARCHAR(20) DEFAULT NULL,
    priority_filter VARCHAR(20) DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    type VARCHAR(50),
    category VARCHAR(50),
    priority VARCHAR(20),
    status VARCHAR(20),
    title VARCHAR(200),
    message TEXT,
    summary VARCHAR(500),
    action_url TEXT,
    action_text VARCHAR(100),
    tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.id,
        n.type,
        n.category,
        n.priority,
        n.status,
        n.title,
        n.message,
        n.summary,
        n.action_url,
        n.action_text,
        n.tags,
        n.created_at,
        n.delivered_at,
        n.read_at,
        n.acknowledged_at,
        n.dismissed_at,
        n.expires_at
    FROM notifications n
    WHERE (n.user_id = user_uuid OR n.user_id IS NULL)
      AND (category_filter IS NULL OR n.category = category_filter)
      AND (status_filter IS NULL OR n.status = status_filter)
      AND (priority_filter IS NULL OR n.priority = priority_filter)
      AND (n.expires_at IS NULL OR n.expires_at > NOW())
    ORDER BY 
        CASE n.priority
            WHEN 'critical' THEN 4
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 1
            ELSE 0
        END DESC,
        n.created_at DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Create views for common queries
CREATE OR REPLACE VIEW active_notifications AS
SELECT 
    n.id,
    n.user_id,
    n.type,
    n.category,
    n.priority,
    n.status,
    n.title,
    n.message,
    n.summary,
    n.action_url,
    n.action_text,
    n.created_at,
    n.delivered_at,
    n.read_at,
    n.acknowledged_at,
    n.dismissed_at,
    n.expires_at,
    -- Computed fields
    CASE 
        WHEN n.read_at IS NULL AND n.status NOT IN ('dismissed', 'failed') THEN TRUE
        ELSE FALSE
    END as is_unread,
    CASE 
        WHEN n.expires_at IS NOT NULL AND n.expires_at <= NOW() THEN TRUE
        ELSE FALSE
    END as is_expired
FROM notifications n
WHERE n.status NOT IN ('dismissed', 'failed')
  AND (n.expires_at IS NULL OR n.expires_at > NOW());

CREATE OR REPLACE VIEW notification_summary AS
SELECT 
    user_id,
    COUNT(*) as total_notifications,
    COUNT(*) FILTER (WHERE read_at IS NULL AND status NOT IN ('dismissed', 'failed')) as unread_count,
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status = 'delivered') as delivered_count,
    COUNT(*) FILTER (WHERE status = 'read') as read_count,
    COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged_count,
    COUNT(*) FILTER (WHERE status = 'dismissed') as dismissed_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    MAX(created_at) as last_notification_at,
    MAX(read_at) as last_read_at
FROM notifications
WHERE user_id IS NOT NULL
GROUP BY user_id;

-- Insert some sample data for testing (optional)
-- Uncomment the following lines if you want to insert sample data

/*
INSERT INTO notifications (
    user_id, type, category, priority, title, message, summary, 
    delivery_methods, tags, source
) VALUES 
(
    'test-user-001', 
    'analysis_completion', 
    'detection', 
    'high',
    'Video Analysis Complete',
    'Your video analysis has been completed successfully. The video was determined to be authentic with 95.2% confidence.',
    'Video analysis completed - Authentic (95.2%)',
    '["in_app", "email"]',
    '["analysis", "completion", "authentic"]',
    'detection_engine'
),
(
    'test-user-001',
    'security_alert',
    'security',
    'critical',
    'High Threat Detected',
    'A high-confidence deepfake has been detected in video stream. Immediate attention required.',
    'High-confidence deepfake detected',
    '["in_app", "email", "push"]',
    '["security", "threat", "deepfake"]',
    'morpheus_security'
);
*/

-- Grant necessary permissions (adjust as needed for your security requirements)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON notifications TO your_app_user;
-- GRANT SELECT, INSERT ON notification_history TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE ON user_notification_preferences TO your_app_user;
-- GRANT SELECT ON active_notifications TO your_app_user;
-- GRANT SELECT ON notification_summary TO your_app_user;
-- GRANT USAGE ON SCHEMA public TO your_app_user;

COMMENT ON TABLE notifications IS 'Stores dashboard notifications with real-time delivery support';
COMMENT ON TABLE notification_history IS 'Audit trail for notification actions and status changes';
COMMENT ON TABLE user_notification_preferences IS 'User preferences for notification delivery and filtering';
COMMENT ON VIEW active_notifications IS 'View of active notifications with computed fields';
COMMENT ON VIEW notification_summary IS 'Summary view of notifications per user';
COMMENT ON FUNCTION get_user_notification_stats(VARCHAR) IS 'Returns notification statistics for a specific user';
COMMENT ON FUNCTION should_notify_user(VARCHAR, VARCHAR, VARCHAR) IS 'Checks if user should receive notification based on preferences';
COMMENT ON FUNCTION get_user_notifications(VARCHAR, INTEGER, INTEGER, VARCHAR, VARCHAR, VARCHAR) IS 'Retrieves filtered notifications for a user';
COMMENT ON FUNCTION cleanup_expired_notifications() IS 'Cleans up expired notifications by marking them as dismissed';
COMMENT ON FUNCTION log_notification_action() IS 'Trigger function to log notification status changes';
COMMENT ON FUNCTION update_notifications_updated_at() IS 'Trigger function to update the updated_at timestamp';
