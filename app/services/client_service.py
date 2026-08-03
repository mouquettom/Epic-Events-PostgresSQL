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
    """Applique les règles métier relatives aux clients."""

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
        """
        Crée un client et l'associe automatiquement au commercial connecté.

        Cette action est exclusivement réservée aux commerciaux.
        """

        self._require_commercial_role(current_employee)

        normalized_name = full_name.strip()
        normalized_email = email.strip().lower()
        normalized_phone = phone.strip()
        normalized_company = company.strip()

        self._validate_required_fields(
            full_name=normalized_name,
            email=normalized_email,
            phone=normalized_phone,
            company=normalized_company,
        )

        existing_client = self.repository.get_by_email(
            normalized_email
        )

        if existing_client is not None:
            raise DuplicateError(
                "Un client utilise déjà cette adresse email."
            )

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
        """
        Retourne un client.

        Tous les collaborateurs authentifiés peuvent consulter
        tous les clients en lecture seule.
        """

        self._require_valid_role(current_employee)

        return self._get_existing_client(client_id)

    def list_clients(
        self,
        current_employee: Employee,
    ) -> list[Client]:
        """
        Retourne tous les clients.

        La lecture de tous les clients est autorisée aux trois services.
        """

        self._require_valid_role(current_employee)

        return self.repository.get_all()

    def update_client(
        self,
        current_employee: Employee,
        client_id: int,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        company: str | None = None,
    ) -> Client:
        """
        Modifie un client.

        Seul le commercial responsable du client peut le modifier.
        """

        client = self._get_existing_client(client_id)

        self._require_client_owner(
            employee=current_employee,
            client=client,
        )

        if full_name is not None:
            normalized_name = full_name.strip()

            if not normalized_name:
                raise ValidationError(
                    "Le nom du client ne peut pas être vide."
                )

            client.full_name = normalized_name

        if email is not None:
            normalized_email = email.strip().lower()

            if not normalized_email:
                raise ValidationError(
                    "L'email du client ne peut pas être vide."
                )

            existing_client = self.repository.get_by_email(
                normalized_email
            )

            if (
                existing_client is not None
                and existing_client.id != client.id
            ):
                raise DuplicateError(
                    "Un client utilise déjà cette adresse email."
                )

            client.email = normalized_email

        if phone is not None:
            normalized_phone = phone.strip()

            if not normalized_phone:
                raise ValidationError(
                    "Le téléphone du client ne peut pas être vide."
                )

            client.phone = normalized_phone

        if company is not None:
            normalized_company = company.strip()

            if not normalized_company:
                raise ValidationError(
                    "L'entreprise du client ne peut pas être vide."
                )

            client.company = normalized_company

        try:
            updated_client = self.repository.update(client)
            self.session.commit()

            return updated_client

        except Exception:
            self.session.rollback()
            raise

    def _get_existing_client(
        self,
        client_id: int,
    ) -> Client:
        client = self.repository.get_by_id(client_id)

        if client is None:
            raise NotFoundError("Client introuvable.")

        return client

    @staticmethod
    def _validate_required_fields(
        full_name: str,
        email: str,
        phone: str,
        company: str,
    ) -> None:
        if not full_name:
            raise ValidationError(
                "Le nom du client est obligatoire."
            )

        if not email:
            raise ValidationError(
                "L'email du client est obligatoire."
            )

        if not phone:
            raise ValidationError(
                "Le téléphone du client est obligatoire."
            )

        if not company:
            raise ValidationError(
                "L'entreprise du client est obligatoire."
            )

    @staticmethod
    def _require_commercial_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError(
                "Seul un commercial peut créer un client."
            )

    @staticmethod
    def _require_client_owner(
        employee: Employee,
        client: Client,
    ) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError(
                "Seul un commercial peut modifier un client."
            )

        if client.commercial_id != employee.id:
            raise AuthorizationError(
                "Vous ne pouvez modifier que les clients "
                "dont vous êtes responsable."
            )

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
                "Vous n'êtes pas autorisé à consulter les clients."
            )