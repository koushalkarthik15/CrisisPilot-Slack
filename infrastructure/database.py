import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from core.config import get_settings

logger = logging.getLogger("crisispilot.database")

settings = get_settings()

# Create Async Engine for SQLite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),
    future=True,
    # SQLite-specific: allow multithreading and prevent locking issues
    connect_args={"check_same_thread": False}
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Base class for SQLAlchemy models
Base = declarative_base()

# Import models to ensure they are registered with the declarative Base
import features.incident_management.models  # noqa: F401
import features.recommendations.models  # noqa: F401
import features.workflow.models  # noqa: F401
import features.mini_agents.models  # noqa: F401
import features.watchlists.models  # noqa: F401
import features.operations.models  # noqa: F401
import features.missions.models  # noqa: F401
import features.workflows.models  # noqa: F401
import features.timeline.models  # noqa: F401
import features.evidence.models  # noqa: F401
import features.monitoring.models  # noqa: F401
from sqlalchemy import text

MIGRATIONS = [
    {
        "version": 1,
        "up": [
            "ALTER TABLE incidents ADD COLUMN parent_id VARCHAR;",
            "ALTER TABLE incidents ADD COLUMN assigned_user_id VARCHAR;",
            "ALTER TABLE recommendations ADD COLUMN approved_by VARCHAR;",
            "ALTER TABLE recommendations ADD COLUMN assigned_to VARCHAR;",
            "ALTER TABLE recommendations ADD COLUMN assigned_by VARCHAR;",
            "ALTER TABLE recommendations ADD COLUMN assigned_at DATETIME;",
            "ALTER TABLE recommendations ADD COLUMN due_at DATETIME;",
            "ALTER TABLE recommendations ADD COLUMN completed_by VARCHAR;",
            "ALTER TABLE recommendations ADD COLUMN completed_at DATETIME;",
            "ALTER TABLE recommendations ADD COLUMN completion_notes VARCHAR;",
            "ALTER TABLE audit_trails ADD COLUMN incident_id VARCHAR;"
        ]
    },
    {
        "version": 2,
        "up": [
            "ALTER TABLE incidents ADD COLUMN thread_ts VARCHAR;"
        ]
    },
    {
        "version": 3,
        "up": [
            "ALTER TABLE incidents ADD COLUMN operation_id VARCHAR;"
        ]
    },
    {
        "version": 4,
        "up": []
    },
    {
        "version": 5,
        "up": []
    },
    {
        "version": 7,
        "up": [
            "ALTER TABLE recommendations ADD COLUMN operation_id VARCHAR;"
        ]
    },
    {
        "version": 8,
        "up": [
            "ALTER TABLE monitoring_profiles ADD COLUMN custom_frequency VARCHAR;"
        ]
    },
    {
        "version": 9,
        "up": [
            "ALTER TABLE incidents ADD COLUMN mission_id VARCHAR;",
            "ALTER TABLE incidents ADD COLUMN execution_details VARCHAR;"
        ]
    }
]

async def run_migrations(conn):
    logger.info("Checking schema migrations...")
    await conn.execute(text(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
    ))
    
    result = await conn.execute(text("SELECT MAX(version) FROM schema_migrations"))
    current_version = result.scalar() or 0
    
    for migration in MIGRATIONS:
        if migration["version"] > current_version:
            logger.info(f"Applying migration version {migration['version']}...")
            for sql in migration["up"]:
                try:
                    await conn.execute(text(sql))
                except Exception as e:
                    # Ignore duplicate column errors on SQLite
                    if "duplicate column name" in str(e).lower():
                        pass
                    else:
                        raise e
            await conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": migration["version"]})
            logger.info(f"Migration version {migration['version']} applied successfully.")

async def seed_watchlists(conn):
    logger.info("Seeding watchlists if necessary...")
    result = await conn.execute(text("SELECT COUNT(*) FROM watchlists"))
    count = result.scalar()
    if count == 0:
        await conn.execute(text("""
            INSERT INTO watchlists (id, org_id, name, description, keywords, channel_id, severity_threshold, enabled, created_at, updated_at) 
            VALUES 
            ('w-1', 'default', 'Global Weather Alerts', 'Monitors severe weather patterns globally', 'cyclone, hurricane, flood, tornado, blizzard, heatwave', '#operations', 'MEDIUM', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('w-2', 'default', 'Humanitarian Crises', 'Monitors emerging humanitarian crises', 'refugee, famine, earthquake disaster, evacuation, humanitarian crisis, displacement', '#operations', 'MEDIUM', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """))
        logger.info("Seeded initial watchlists (weather, humanitarian).")

async def init_db() -> None:
    """
    Initializes the database by creating all defined tables.
    Runs lightweight schema migrations.
    """
    try:
        logger.info(f"Initializing database at {settings.DATABASE_URL}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await run_migrations(conn)
            await seed_watchlists(conn)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Gracefully shuts down the database engine.
    """
    logger.info("Shutting down database engine...")
    await engine.dispose()
    logger.info("Database engine shut down successfully.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to yield an async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
