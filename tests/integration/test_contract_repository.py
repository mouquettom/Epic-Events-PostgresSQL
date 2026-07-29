from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.employee import Role
from app.repositories.contract_repository import ContractRepository
from tests.factories import (
    create_client,
    create_contract,
    create_employee,
)


def test_get_unsigned_contracts(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )
    client = create_client(
        db_session,
        commercial=commercial,
    )

    signed_contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
        is_signed=True,
    )
    unsigned_contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
        is_signed=False,
    )

    repository = ContractRepository(db_session)

    contracts = repository.get_unsigned_contracts()

    contract_ids = {contract.id for contract in contracts}

    assert unsigned_contract.id in contract_ids
    assert signed_contract.id not in contract_ids


def test_get_unpaid_contracts(db_session: Session) -> None:
    commercial = create_employee(
        db_session,
        role=Role.COMMERCIAL,
    )
    client = create_client(
        db_session,
        commercial=commercial,
    )

    paid_contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
        remaining_amount=Decimal("0.00"),
    )
    unpaid_contract = create_contract(
        db_session,
        client=client,
        commercial=commercial,
        remaining_amount=Decimal("2500.00"),
    )

    repository = ContractRepository(db_session)

    contracts = repository.get_unpaid_contracts()

    contract_ids = {contract.id for contract in contracts}

    assert unpaid_contract.id in contract_ids
    assert paid_contract.id not in contract_ids