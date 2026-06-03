"""数据库连接与会话管理"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)

# SQLite 外键支持
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_generation_records()


def _migrate_sqlite_generation_records():
    """Keep existing desktop SQLite databases compatible with newer models."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    columns = {
        "provider": "VARCHAR(32) DEFAULT ''",
        "provider_model": "VARCHAR(128) DEFAULT ''",
        "quality_mode": "VARCHAR(16) DEFAULT 'sample'",
        "prompt": "TEXT DEFAULT ''",
        "negative_prompt": "TEXT DEFAULT ''",
        "reference_material_id": "INTEGER",
        "raw_params": "TEXT",
        "raw_response": "TEXT",
        "cost_estimate": "FLOAT DEFAULT 0.0",
        "output_has_alpha": "BOOLEAN DEFAULT 0",
        "postprocess_status": "VARCHAR(16) DEFAULT ''",
    }

    with engine.begin() as conn:
        existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(generation_records)").fetchall()
        }
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE generation_records ADD COLUMN {name} {ddl}"))
