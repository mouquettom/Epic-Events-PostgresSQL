from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.employee import Employee, Role
from app.repositories.client_repository import ClientRepository
from app.utils.exceptions import (
    AuthorizationError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)


class ClientService:
    """ Applique les règles métier relatives aux clients. """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ClientRepository(session)

    def create_client(
        self,
        current_employee: Employee,
        full_name: str,
        email: str,
        phone: str,
        company: str,
    ) -> Client:

        self._require_commercial_role(current_employee)

        normalized_email = email.strip().lower()
        normalized_name = full_name.strip()
        normalized_phone = phone.strip()
        normalized_company = company.strip()

        if not normalized_name:
            raise ValidationError("Le nom du client est obligatoire.")

        if not normalized_email:
            raise ValidationError("L'email du client est obligatoire.")

        if not normalized_phone:
            raise ValidationError("Le téléphone du client est obligatoire.")

        if not normalized_company:
            raise ValidationError("L'entreprise du client est obligatoire.")

        existing_client = self.repository.get_by_email(normalized_email)

        if existing_client is not None:
            raise DuplicateError("Un client utilise déjà cette adresse email.")

        client = Client(
            full_name=normalized_name,
            email=normalized_email,
            phone=normalized_phone,
            company=normalized_company,
            commercial_id=current_employee.id,
        )

        try:
            created_client = self.repository.create(client)
            self.session.commit()
            return created_client

        except Exception:
            self.session.rollback()
            raise

    def get_client(
            self,
            current_employee: Employee,
            client_id: int,
    ) -> Client:

        client = self._get_existing_client(client_id)
        self._require_client_access(current_employee, client)

        return client

    def list_clients(
            self,
            current_employee: Employee,
    ) -> list[Client]:

        if current_employee.role == Role.COMMERCIAL:
            return self.repository.get_by_commercial_id(current_employee.id)

        if current_employee.role in {Role.GESTION, Role.SUPPORT}:
            return self.repository.get_all()

        raise AuthorizationError(
            "Vous n'êtes pas autorisé à consulter les clients."
        )

    def update_client(
            self,
            current_employee: Employee,
            client_id: int,
            full_name: str | None = None,
            email: str | None = None,
            phone: str | None = None,
            company: str | None = None,
    ) -> Client:

        client = self._get_existing_client(client_id)
        self._require_client_owner(current_employee, client)

        if full_name is not None:
            normalized_name = full_name.strip()

            if not normalized_name:
                raise ValidationError("Le nom du client ne peut pas être vide.")

            client.full_name = normalized_name

        if email is not None:
            normalized_email = email.strip().lower()

            if not normalized_email:
                raise ValidationError("L'email du client ne peut pas être vide.")

            existing_client = self.repository.get_by_email(normalized_email)

            if existing_client is not None and existing_client.id != client.id:
                raise DuplicateError("Un client utilise déjà cette adresse email.")

            client.email = normalized_email

        if phone is not None:
            normalized_phone = phone.strip()

            if not normalized_phone:
                raise ValidationError("Le téléphone du client ne peut pas être vide.")

            client.phone = normalized_phone

        if company is not None:
            normalized_company = company.strip()

            if not normalized_company:
                raise ValidationError("L'entreprise du client ne peut pas être vide.")

            client.company = normalized_company

        try:
            updated_client = self.repository.update(client)
            self.session.commit()
            return updated_client

        except Exception:
            self.session.rollback()
            raise

    def delete_client(
            self,
            current_employee: Employee,
            client_id: int,
    ) -> None:

        client = self._get_existing_client(client_id)
        self._require_client_owner(current_employee, client)

        if client.contracts:
            raise ValidationError(
                "Ce client ne peut pas être supprimé car il possède des contrats."
            )

        try:
            self.repository.delete(client)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _get_existing_client(self, client_id: int) -> Client:
        client = self.repository.get_by_id(client_id)

        if client is None:
            raise NotFoundError("Client introuvable.")

        return client

    @staticmethod
    def _require_commercial_role(employee: Employee) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError("Seul un commercial peut créer un client.")

    @staticmethod
    def _require_client_owner(
            employee: Employee,
            client: Client,
    ) -> None:

        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError("Seul un commercial peut modifier un client.")

        if client.commercial_id != employee.id:
            raise AuthorizationError("Vous ne pouvez modifier que vos propres clients.")

    @staticmethod
    def _require_client_access(
            employee: Employee,
            client: Client,
    ) -> None:

        if employee.role == Role.COMMERCIAL:
            if client.commercial_id != employee.id:
                raise AuthorizationError(
                    "Vous ne pouvez consulter que vos propres clients."
                )
            return

        if employee.role not in {Role.GESTION, Role.SUPPORT}:
            raise AuthorizationError("Vous n'êtes pas autorisé à consulter ce client.")