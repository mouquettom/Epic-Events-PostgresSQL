from sqlalchemy import text

from app.database.session import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database();"))
        database_name = result.scalar()

    assert database_name == "epic_events_database"