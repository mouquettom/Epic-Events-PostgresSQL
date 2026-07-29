from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client


class ClientRepository:
    """ Accès aux données des clients. """

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, client_id: int) -> Client | None:
        return self.session.get(Client, client_id)

    def get_by_email(self, email: str) -> Client | None:
        statement = select(Client).where(Client.email == email)
        return self.session.scalar(statement)

    def get_by_commercial_id(self, commercial_id: int) -> list[Client]:
        statement = (
            select(Client)
            .where(Client.commercial_id == commercial_id)
            .order_by(Client.id)
        )
        return list(self.session.scalars(statement).all())

    def get_all(self) -> list[Client]:
        statement = select(Client).order_by(Client.id)
        return list(self.session.scalars(statement).all())

    def create(self, client: Client) -> Client:
        self.session.add(client)
        self.session.flush()
        self.session.refresh(client)
        return client

    def update(self, client: Client) -> Client:
        self.session.flush()
        self.session.refresh(client)
        return client

    def delete(self, client: Client) -> None:
        self.session.delete(client)
        self.session.flush()