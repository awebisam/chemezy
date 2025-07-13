#!/usr/bin/env python3
"""
Database Performance Optimization Script

Adds database indexes and other performance optimizations for the award system.
"""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, create_engine
from app.core.config import settings


def create_performance_indexes(engine):
    """Create database indexes for improved query performance."""
    print("Creating performance indexes...")
    
    indexes = [
        # User awards table indexes
        "CREATE INDEX IF NOT EXISTS idx_user_awards_granted_at ON user_awards(granted_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_awards_user_template ON user_awards(user_id, template_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_awards_template_granted ON user_awards(template_id, granted_at DESC)",
        
        # Award templates table indexes
        "CREATE INDEX IF NOT EXISTS idx_award_templates_category_active ON award_templates(category, is_active)",
        "CREATE INDEX IF NOT EXISTS idx_award_templates_active_name ON award_templates(is_active, name)",
        
        # Audit logs table indexes (if exists)
        "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON auditlog(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON auditlog(user_id, action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_action_status ON auditlog(action, status)",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON auditlog(entity_type, entity_id)",
        
        # User table indexes
        "CREATE INDEX IF NOT EXISTS idx_user_is_admin ON user(is_admin)",
        "CREATE INDEX IF NOT EXISTS idx_user_is_active ON user(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_user_created_at ON user(created_at DESC)",
        
        # Discovery table indexes (if exists)
        "CREATE INDEX IF NOT EXISTS idx_discovery_user_effect ON discovery(discovered_by, effect)",
        "CREATE INDEX IF NOT EXISTS idx_discovery_discovered_at ON discovery(discovered_at DESC)",
        
        # Deletion request table indexes
        "CREATE INDEX IF NOT EXISTS idx_deletion_request_status ON deletionrequest(status)",
        "CREATE INDEX IF NOT EXISTS idx_deletion_request_created_at ON deletionrequest(created_at DESC)",
        
        # Composite indexes for common queries
        "CREATE INDEX IF NOT EXISTS idx_user_awards_leaderboard ON user_awards(user_id, granted_at DESC, template_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_awards_category_stats ON user_awards(user_id, template_id) WHERE template_id IN (SELECT id FROM award_templates WHERE is_active = 1)",
    ]
    
    created_count = 0
    failed_count = 0
    
    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                index_name = index_sql.split("IF NOT EXISTS ")[1].split(" ON")[0]
                print(f"Created index: {index_name}")
                created_count += 1
            except Exception as e:
                print(f"Failed to create index: {e}")
                failed_count += 1
        
        conn.commit()
    
    print(f"Index creation complete. Created: {created_count}, Failed: {failed_count}")
    return created_count, failed_count


def create_database_views(engine):
    """Create database views for common queries."""
    print("Creating database views...")
    
    views = [
        # User award statistics view
        """
        CREATE VIEW IF NOT EXISTS user_award_stats AS
        SELECT 
            u.id as user_id,
            u.username,
            COUNT(ua.id) as total_awards,
            COUNT(DISTINCT at.category) as categories_earned,
            SUM(CASE WHEN at.award_metadata ->> '$.points' IS NOT NULL 
                     THEN CAST(at.award_metadata ->> '$.points' AS INTEGER) * ua.tier 
                     ELSE 10 * ua.tier END) as total_points,
            MAX(ua.granted_at) as latest_award_date
        FROM user u
        LEFT JOIN user_awards ua ON u.id = ua.user_id
        LEFT JOIN award_templates at ON ua.template_id = at.id
        GROUP BY u.id, u.username
        """,
        
        # Category leaderboard view
        """
        CREATE VIEW IF NOT EXISTS category_leaderboard AS
        SELECT 
            u.id as user_id,
            u.username,
            at.category,
            COUNT(ua.id) as award_count,
            SUM(CASE WHEN at.award_metadata ->> '$.points' IS NOT NULL 
                     THEN CAST(at.award_metadata ->> '$.points' AS INTEGER) * ua.tier 
                     ELSE 10 * ua.tier END) as total_points
        FROM user u
        JOIN user_awards ua ON u.id = ua.user_id
        JOIN award_templates at ON ua.template_id = at.id
        WHERE at.is_active = 1
        GROUP BY u.id, u.username, at.category
        """,
        
        # Recent achievements view
        """
        CREATE VIEW IF NOT EXISTS recent_achievements AS
        SELECT 
            ua.id,
            ua.user_id,
            u.username,
            at.name as template_name,
            at.category,
            ua.tier,
            ua.granted_at,
            at.award_metadata ->> '$.icon' as icon,
            at.award_metadata ->> '$.rarity' as rarity
        FROM user_awards ua
        JOIN user u ON ua.user_id = u.id
        JOIN award_templates at ON ua.template_id = at.id
        WHERE at.is_active = 1
        ORDER BY ua.granted_at DESC
        """,
        
        # Template statistics view
        """
        CREATE VIEW IF NOT EXISTS template_stats AS
        SELECT 
            at.id,
            at.name,
            at.category,
            COUNT(ua.id) as awarded_count,
            COUNT(DISTINCT ua.user_id) as unique_recipients,
            AVG(ua.tier) as average_tier,
            MAX(ua.granted_at) as last_awarded
        FROM award_templates at
        LEFT JOIN user_awards ua ON at.id = ua.template_id
        WHERE at.is_active = 1
        GROUP BY at.id, at.name, at.category
        """
    ]
    
    created_count = 0
    failed_count = 0
    
    with engine.connect() as conn:
        for view_sql in views:
            try:
                conn.execute(text(view_sql))
                view_name = view_sql.split("VIEW IF NOT EXISTS ")[1].split(" AS")[0]
                print(f"Created view: {view_name}")
                created_count += 1
            except Exception as e:
                print(f"Failed to create view: {e}")
                failed_count += 1
        
        conn.commit()
    
    print(f"View creation complete. Created: {created_count}, Failed: {failed_count}")
    return created_count, failed_count


def optimize_database_settings(engine):
    """Apply database optimization settings."""
    print("Applying database optimization settings...")
    
    # SQLite optimization settings
    optimizations = [
        "PRAGMA journal_mode = WAL",  # Write-Ahead Logging for better concurrency
        "PRAGMA synchronous = NORMAL",  # Balance between performance and durability
        "PRAGMA cache_size = 10000",  # Increase cache size (10MB)
        "PRAGMA temp_store = MEMORY",  # Store temporary tables in memory
        "PRAGMA mmap_size = 268435456",  # Use memory-mapped I/O (256MB)
        "PRAGMA optimize",  # Optimize database
    ]
    
    applied_count = 0
    failed_count = 0
    
    with engine.connect() as conn:
        for optimization in optimizations:
            try:
                conn.execute(text(optimization))
                print(f"Applied: {optimization}")
                applied_count += 1
            except Exception as e:
                print(f"Failed to apply optimization: {e}")
                failed_count += 1
        
        conn.commit()
    
    print(f"Optimization settings applied. Success: {applied_count}, Failed: {failed_count}")
    return applied_count, failed_count


def analyze_database_performance(engine):
    """Analyze database performance and suggest optimizations."""
    print("Analyzing database performance...")
    
    analyses = [
        ("Table sizes", "SELECT name, COUNT(*) as row_count FROM sqlite_master WHERE type='table' GROUP BY name"),
        ("Index usage", "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"),
        ("User awards distribution", "SELECT COUNT(*) as total_awards, COUNT(DISTINCT user_id) as unique_users FROM user_awards"),
        ("Template popularity", "SELECT at.name, COUNT(ua.id) as times_awarded FROM award_templates at LEFT JOIN user_awards ua ON at.id = ua.template_id GROUP BY at.name ORDER BY times_awarded DESC LIMIT 10"),
        ("Recent activity", "SELECT DATE(granted_at) as date, COUNT(*) as awards_granted FROM user_awards WHERE granted_at >= date('now', '-7 days') GROUP BY DATE(granted_at) ORDER BY date DESC"),
    ]
    
    with engine.connect() as conn:
        for analysis_name, query in analyses:
            try:
                print(f"\n{analysis_name}:")
                result = conn.execute(text(query))
                rows = result.fetchall()
                
                if rows:
                    # Print column headers
                    columns = result.keys()
                    print("  " + " | ".join(columns))
                    print("  " + "-" * (len(" | ".join(columns))))
                    
                    # Print rows
                    for row in rows:
                        print("  " + " | ".join(str(value) for value in row))
                else:
                    print("  No data found")
                    
            except Exception as e:
                print(f"  Error running analysis: {e}")


def main():
    """Main function to run database optimizations."""
    print("Starting database performance optimization...")
    
    try:
        engine = create_engine(settings.database_url)
        
        # Create indexes
        created_indexes, failed_indexes = create_performance_indexes(engine)
        
        # Create views
        created_views, failed_views = create_database_views(engine)
        
        # Apply optimization settings
        applied_optimizations, failed_optimizations = optimize_database_settings(engine)
        
        # Analyze performance
        analyze_database_performance(engine)
        
        print(f"\nOptimization Summary:")
        print(f"- Indexes: {created_indexes} created, {failed_indexes} failed")
        print(f"- Views: {created_views} created, {failed_views} failed")
        print(f"- Settings: {applied_optimizations} applied, {failed_optimizations} failed")
        
        print("\nDatabase optimization complete!")
        
    except Exception as e:
        print(f"Error during optimization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()