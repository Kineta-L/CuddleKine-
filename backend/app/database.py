"""Database connection and lightweight SQLite migrations."""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema():
    """Additive migrations for existing local desktop SQLite databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    table_columns = {
        "materials": {
            "source_type": "VARCHAR(64) DEFAULT ''",
            "detected_subject": "VARCHAR(256) DEFAULT ''",
            "image_width": "INTEGER",
            "image_height": "INTEGER",
            "ai_description": "TEXT DEFAULT ''",
            "visual_features_json": "TEXT DEFAULT ''",
            "processing_status": "VARCHAR(32) DEFAULT 'pending'",
        },
        "briefs": {
            "source_material_ids": "TEXT DEFAULT ''",
            "source_type": "VARCHAR(64) DEFAULT ''",
            "pending_questions": "TEXT DEFAULT ''",
            "risk_notes": "TEXT DEFAULT ''",
            "designer_edits": "TEXT DEFAULT ''",
            "ai_model_used": "VARCHAR(128) DEFAULT 'rule-based'",
            "prompt_version": "VARCHAR(64) DEFAULT 'plush-prompt-v1'",
        },
        "orders": {
            "brief_status": "VARCHAR(32) DEFAULT 'not_started'",
            "confirmed_brief_id": "INTEGER",
            "source_summary": "TEXT DEFAULT ''",
            "customer_question_status": "VARCHAR(32) DEFAULT 'not_needed'",
        },
        "generation_records": {
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
            "brief_id": "INTEGER",
            "prompt_builder_version": "VARCHAR(64) DEFAULT ''",
            "final_prompt": "TEXT DEFAULT ''",
            "provider_prompt": "TEXT DEFAULT ''",
            "source_material_ids": "TEXT DEFAULT ''",
            "quality_status": "VARCHAR(32) DEFAULT 'unreviewed'",
            "review_notes": "TEXT DEFAULT ''",
        },
    }

    with engine.begin() as conn:
        for table, columns in table_columns.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
