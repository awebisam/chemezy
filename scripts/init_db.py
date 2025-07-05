#!/usr/bin/env python3
"""
Database initialization script for Chemezy Backend Engine.

This script creates the database tables and optionally seeds initial data.
"""

import asyncio
from sqlmodel import SQLModel, create_engine

from app.core.config import settings
from app.db.base import *  # Import all models to register with SQLModel


def create_db_and_tables():
    """Create database tables."""
    print("Creating database tables...")
    
    engine = create_engine(settings.database_url)
    SQLModel.metadata.create_all(engine)
    
    print("✅ Database tables created successfully!")
    print(f"Database URL: {settings.database_url}")
    print("\nTables created:")
    for table in SQLModel.metadata.tables.keys():
        print(f"  - {table}")


if __name__ == "__main__":
    create_db_and_tables()