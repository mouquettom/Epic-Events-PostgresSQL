from sqlalchemy.orm import Session

from app.models.employee import Role
from app.repositories.client_repository import ClientRepository
from tests.factories import create_client, create_employee


def test_create_and_find_client(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )

    client = create_client(
        db_session,
        commercial=commercial,
        email="repository.client@test.com",
    )

    repository = ClientRepository(db_session)

    found = repository.get_by_id(client.id)

    assert found is not None
    assert found.email == "repository.client@test.com"
    assert found.commercial_id == commercial.id


def test_find_client_by_email(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )

    create_client(
        db_session,
        commercial=commercial,
        email="find.client@test.com",
    )

    repository = ClientRepository(db_session)

    found = repository.get_by_email("find.client@test.com")

    assert found is not None
    assert found.company == "Test Company"