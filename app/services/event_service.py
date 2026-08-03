from datetime import datetime

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee, Role
from app.models.event import Event
from app.repositories.contract_repository import ContractRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.event_repository import EventRepository
from app.utils.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)


class EventService:
    """Applique les règles métier relatives aux événements."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.event_repository = EventRepository(session)
        self.contract_repository = ContractRepository(session)
        self.employee_repository = EmployeeRepository(session)

    def create_event(
        self,
        current_employee: Employee,
        contract_id: int,
        start_date: datetime,
        end_date: datetime,
        location: str,
        attendees: int,
        notes: str = "",
    ) -> Event:
        """
        Crée un événement pour un contrat signé.

        Cette action est réservée au commercial responsable
        du contrat concerné.
        """

        self._require_commercial_role(current_employee)

        contract = self._get_existing_contract(contract_id)

        self._require_contract_owner(
            employee=current_employee,
            contract=contract,
        )

        if not contract.is_signed:
            raise ValidationError(
                "Un événement ne peut être créé que pour "
                "un contrat signé."
            )

        normalized_location = location.strip()
        normalized_notes = notes.strip()

        self._validate_event_data(
            start_date=start_date,
            end_date=end_date,
            location=normalized_location,
            attendees=attendees,
        )

        event = Event(
            start_date=start_date,
            end_date=end_date,
            location=normalized_location,
            attendees=attendees,
            notes=normalized_notes,
            contract_id=contract.id,
            support_id=None,
        )

        try:
            created_event = self.event_repository.create(event)
            self.session.commit()

            return created_event

        except Exception:
            self.session.rollback()
            raise

    def get_event(
        self,
        current_employee: Employee,
        event_id: int,
    ) -> Event:
        """
        Retourne un événement.

        Tous les collaborateurs peuvent consulter tous les événements
        en lecture seule.
        """

        self._require_valid_role(current_employee)

        return self._get_existing_event(event_id)

    def list_events(
        self,
        current_employee: Employee,
    ) -> list[Event]:
        """
        Retourne tous les événements.

        La consultation globale est autorisée aux équipes gestion,
        commerciale et support.
        """

        self._require_valid_role(current_employee)

        return self.event_repository.get_all()

    def list_events_without_support(
        self,
        current_employee: Employee,
    ) -> list[Event]:
        """
        Retourne les événements sans collaborateur support affecté.

        Ce filtre est réservé au service gestion.
        """

        self._require_management_role(current_employee)

        return self.event_repository.get_events_without_support()

    def list_assigned_events(
        self,
        current_employee: Employee,
    ) -> list[Event]:
        """
        Retourne les événements attribués au support connecté.

        Ce filtre est réservé au service support.
        """

        self._require_support_role(current_employee)

        return self.event_repository.get_by_support_id(
            current_employee.id
        )

    def update_event(
        self,
        current_employee: Employee,
        event_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        location: str | None = None,
        attendees: int | None = None,
        notes: str | None = None,
    ) -> Event:
        """
        Modifie un événement.

        Seul le collaborateur support affecté à l'événement
        peut modifier ses informations opérationnelles.
        """

        event = self._get_existing_event(event_id)

        self._require_assigned_support(
            employee=current_employee,
            event=event,
        )

        new_start_date = (
            start_date
            if start_date is not None
            else event.start_date
        )

        new_end_date = (
            end_date
            if end_date is not None
            else event.end_date
        )

        new_location = (
            location.strip()
            if location is not None
            else event.location
        )

        new_attendees = (
            attendees
            if attendees is not None
            else event.attendees
        )

        self._validate_event_data(
            start_date=new_start_date,
            end_date=new_end_date,
            location=new_location,
            attendees=new_attendees,
        )

        event.start_date = new_start_date
        event.end_date = new_end_date
        event.location = new_location
        event.attendees = new_attendees

        if notes is not None:
            event.notes = notes.strip()

        try:
            updated_event = self.event_repository.update(event)
            self.session.commit()

            return updated_event

        except Exception:
            self.session.rollback()
            raise

    def assign_support(
        self,
        current_employee: Employee,
        event_id: int,
        support_id: int,
    ) -> Event:
        """
        Affecte un collaborateur support à un événement.

        Cette action est exclusivement réservée au service gestion.
        """

        self._require_management_role(current_employee)

        event = self._get_existing_event(event_id)
        support = self._get_existing_employee(support_id)

        if support.role != Role.SUPPORT:
            raise ValidationError(
                "L'employé sélectionné n'appartient pas "
                "au service support."
            )

        event.support_id = support.id

        try:
            updated_event = self.event_repository.update(event)
            self.session.commit()

            return updated_event

        except Exception:
            self.session.rollback()
            raise

    def _get_existing_event(
        self,
        event_id: int,
    ) -> Event:
        event = self.event_repository.get_by_id(event_id)

        if event is None:
            raise NotFoundError("Événement introuvable.")

        return event

    def _get_existing_contract(
        self,
        contract_id: int,
    ) -> Contract:
        contract = self.contract_repository.get_by_id(contract_id)

        if contract is None:
            raise NotFoundError("Contrat introuvable.")

        return contract

    def _get_existing_employee(
        self,
        employee_id: int,
    ) -> Employee:
        employee = self.employee_repository.get_by_id(employee_id)

        if employee is None:
            raise NotFoundError("Employé introuvable.")

        return employee

    @staticmethod
    def _require_valid_role(
        employee: Employee,
    ) -> None:
        allowed_roles = {
            Role.GESTION,
            Role.COMMERCIAL,
            Role.SUPPORT,
        }

        if employee.role not in allowed_roles:
            raise AuthorizationError(
                "Vous n'êtes pas autorisé à consulter les événements."
            )

    @staticmethod
    def _require_commercial_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError(
                "Seul un commercial peut créer un événement."
            )

    @staticmethod
    def _require_management_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.GESTION:
            raise AuthorizationError(
                "Cette action est réservée au service gestion."
            )

    @staticmethod
    def _require_support_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.SUPPORT:
            raise AuthorizationError(
                "Cette action est réservée au service support."
            )

    @staticmethod
    def _require_contract_owner(
        employee: Employee,
        contract: Contract,
    ) -> None:
        if contract.commercial_id != employee.id:
            raise AuthorizationError(
                "Vous ne pouvez créer un événement que pour "
                "un contrat associé à l'un de vos clients."
            )

    @staticmethod
    def _require_assigned_support(
        employee: Employee,
        event: Event,
    ) -> None:
        if employee.role != Role.SUPPORT:
            raise AuthorizationError(
                "Seul le service support peut modifier "
                "les informations d'un événement."
            )

        if event.support_id != employee.id:
            raise AuthorizationError(
                "Vous ne pouvez modifier que les événements "
                "dont vous êtes responsable."
            )

    @staticmethod
    def _validate_event_data(
        start_date: datetime,
        end_date: datetime,
        location: str,
        attendees: int,
    ) -> None:
        if end_date <= start_date:
            raise ValidationError(
                "La date de fin doit être postérieure "
                "à la date de début."
            )

        if not location:
            raise ValidationError(
                "Le lieu de l'événement est obligatoire."
            )

        if attendees <= 0:
            raise ValidationError(
                "Le nombre de participants doit être "
                "supérieur à zéro."
            )