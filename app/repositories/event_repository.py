from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event


class EventRepository:
    """ Gère l'accès aux données des événements. """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Event]:
        statement = select(Event).order_by(Event.id)
        return list(self.session.scalars(statement).all())

    def get_by_id(self, event_id: int) -> Event | None:
        return self.session.get(Event, event_id)

    def get_by_contract_id(self, contract_id: int) -> list[Event]:
        statement = (
            select(Event)
            .where(Event.contract_id == contract_id)
            .order_by(Event.id)
        )
        return list(self.session.scalars(statement).all())

    def get_by_support_id(self, support_id: int) -> list[Event]:
        statement = (
            select(Event)
            .where(Event.support_id == support_id)
            .order_by(Event.id)
        )
        return list(self.session.scalars(statement).all())

    def get_events_without_support(self) -> list[Event]:
        statement = (
            select(Event)
            .where(Event.support_id.is_(None))
            .order_by(Event.id)
        )
        return list(self.session.scalars(statement).all())

    def create(self, event: Event) -> Event:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def update(self, event: Event) -> Event:
        self.session.flush()
        self.session.refresh(event)
        return event

    def delete(self, event: Event) -> None:
        self.session.delete(event)
        self.session.flush()