from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.models.employee import Employee, Role
from app.models.client import Client
from app.models.contract import Contract
from app.models.event import Event
from app.utils.password import hash_password

_employee_counter = count(1)
_client_counter = count(1)
_contract_counter = count(1)


def create_employee(
    session: Session,
    *,
    role: Role = Role.COMMERCIAL,
    first_name: str = "Test",
    last_name: str = "Employee",
    email: str | None = None,
    password: str = "Password123!",
) -> Employee:
    """Crée et enregistre un employé utilisable dans un test."""

    employee_number = next(_employee_counter)

    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        email=email or f"employee{employee_number}@test.com",
        password_hash=hash_password(password),
        role=role,
    )

    session.add(employee)
    session.flush()
    session.refresh(employee)

    return employee


def create_client(
    session: Session,
    *,
    commercial: Employee,
    full_name: str = "Test Client",
    email: str | None = None,
    phone: str = "0601020304",
    company: str = "Test Company",
) -> Client:

    client_number = next(_client_counter)

    client = Client(
        full_name=full_name,
        email=email or f"client{client_number}@test.com",
        phone=phone,
        company=company,
        commercial_id=commercial.id,
    )

    session.add(client)
    session.flush()
    session.refresh(client)

    return client


def create_contract(
    session: Session,
    *,
    client: Client,
    commercial: Employee,
    total_amount: Decimal = Decimal("10000.00"),
    remaining_amount: Decimal = Decimal("10000.00"),
    is_signed: bool = True,
) -> Contract:
    next(_contract_counter)

    contract = Contract(
        total_amount=total_amount,
        remaining_amount=remaining_amount,
        is_signed=is_signed,
        client_id=client.id,
        commercial_id=commercial.id,
    )

    session.add(contract)
    session.flush()
    session.refresh(contract)

    return contract


def create_event(
    session: Session,
    *,
    contract: Contract,
    support: Employee | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    location: str = "Paris",
    attendees: int = 100,
    notes: str = "Événement de test",
) -> Event:
    actual_start_date = start_date or (datetime.now(UTC) + timedelta(days=10))

    actual_end_date = end_date or (actual_start_date + timedelta(hours=4))

    event = Event(
        start_date=actual_start_date,
        end_date=actual_end_date,
        location=location,
        attendees=attendees,
        notes=notes,
        contract_id=contract.id,
        support_id=support.id if support is not None else None,
    )

    session.add(event)
    session.flush()
    session.refresh(event)

    return event