from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base


@pytest.fixture
def functional_session_factory(
    test_engine: Engine,
) -> Generator[sessionmaker[Session], None, None]:
    """
    Fournit une fabrique de sessions dédiée aux tests fonctionnels.

    Les tables sont nettoyées avant et après chaque parcours.
    """

    with test_engine.begin() as connection:
        connection.execute(text("""
                TRUNCATE TABLE
                    event,
                    contract,
                    client,
                    employee
                RESTART IDENTITY
                CASCADE
                """))

    Base.metadata.create_all(bind=test_engine)

    factory = sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    yield factory

    with test_engine.begin() as connection:
        connection.execute(text("""
                TRUNCATE TABLE
                    event,
                    contract,
                    client,
                    employee
                RESTART IDENTITY
                CASCADE
                """))