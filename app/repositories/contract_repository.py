from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import Contract


class ContractRepository:
    """ Accès aux données des contrats. """

    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Contract]:
        statement = select(Contract).order_by(Contract.id)
        return list(self.session.scalars(statement).all())

    def get_by_id(self, contract_id: int) -> Contract | None:
        return self.session.get(Contract, contract_id)

    def get_by_client_id(self, client_id: int) -> list[Contract]:
        statement = (
            select(Contract)
            .where(Contract.client_id == client_id)
        )
        return list(self.session.scalars(statement).all())

    def get_by_commercial_id(self, commercial_id: int) -> list[Contract]:
        statement = (
            select(Contract)
            .where(Contract.commercial_id == commercial_id)
            .order_by(Contract.id)
        )
        return list(self.session.scalars(statement).all())

    def get_unsigned_contracts(self) -> list[Contract]:
        statement = (
            select(Contract)
            .where(Contract.is_signed.is_(False))
        )
        return list(self.session.scalars(statement).all())

    def get_unpaid_contracts(self) -> list[Contract]:
        statement = (
            select(Contract)
            .where(Contract.remaining_amount > 0)
        )
        return list(self.session.scalars(statement).all())

    def create(self, contract: Contract) -> Contract:
        self.session.add(contract)
        self.session.flush()
        self.session.refresh(contract)
        return contract

    def update(self, contract: Contract) -> Contract:
        self.session.flush()
        self.session.refresh(contract)
        return contract

    def delete(self, contract: Contract) -> None:
        self.session.delete(contract)
        self.session.flush()