"""
Initialize database tables
Run this script to create all tables
"""
from app.core.database import engine, Base
from app.models.deploy import DeployTask, DeployDeviceRecord

def init_db():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
