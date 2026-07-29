import os
from collections.abc import Generator

import pytest
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.models
from app.models.base import Base

load_dotenv()


def build_test_database_url() -> URL:
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["TEST_DB_USER"],
        password=os.environ["TEST_DB_PASSWORD"],
        host=os.environ["TEST_DB_HOST"],
        port=int(os.environ["TEST_DB_PORT"]),
        database=os.environ["TEST_DB_NAME"],
    )


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        build_test_database_url(),
        echo=False,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session

    finally:
        session.close()
        transaction.rollback()
        connection.close()