from sqlalchemy.orm import Session

from app.models.employee import Employee, Role
from app.repositories.employee_repository import EmployeeRepository
from app.utils.exceptions import (
    AuthorizationError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from app.utils.password import hash_password


class EmployeeService:
    """Applique les règles métier relatives aux collaborateurs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = EmployeeRepository(session)

    def create_employee(
        self,
        current_employee: Employee,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        role: Role,
    ) -> Employee:
        """
        Crée un collaborateur.

        Cette action est exclusivement réservée au service gestion.
        """

        self._require_management_role(current_employee)

        normalized_first_name = first_name.strip()
        normalized_last_name = last_name.strip()
        normalized_email = email.strip().lower()

        self._validate_required_fields(
            first_name=normalized_first_name,
            last_name=normalized_last_name,
            email=normalized_email,
            password=password,
        )

        existing_employee = self.repository.get_by_email(
            normalized_email
        )

        if existing_employee is not None:
            raise DuplicateError(
                "Un collaborateur utilise déjà cette adresse email."
            )

        employee = Employee(
            first_name=normalized_first_name,
            last_name=normalized_last_name,
            email=normalized_email,
            password_hash=hash_password(password),
            role=role,
        )

        try:
            created_employee = self.repository.create(employee)
            self.session.commit()

            return created_employee

        except Exception:
            self.session.rollback()
            raise

    def get_employee(
        self,
        current_employee: Employee,
        employee_id: int,
    ) -> Employee:
        """
        Retourne un collaborateur.

        Cette action est exclusivement réservée au service gestion.
        """

        self._require_management_role(current_employee)

        return self._get_existing_employee(employee_id)

    def list_employees(
        self,
        current_employee: Employee,
    ) -> list[Employee]:
        """
        Retourne la liste des collaborateurs.

        Cette action est exclusivement réservée au service gestion.
        """

        self._require_management_role(current_employee)

        return self.repository.get_all()

    def update_employee(
        self,
        current_employee: Employee,
        employee_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        role: Role | None = None,
    ) -> Employee:
        """
        Modifie un collaborateur.

        Cette action est exclusivement réservée au service gestion.
        """

        self._require_management_role(current_employee)

        employee = self._get_existing_employee(employee_id)

        if first_name is not None:
            normalized_first_name = first_name.strip()

            if not normalized_first_name:
                raise ValidationError(
                    "Le prénom ne peut pas être vide."
                )

            employee.first_name = normalized_first_name

        if last_name is not None:
            normalized_last_name = last_name.strip()

            if not normalized_last_name:
                raise ValidationError(
                    "Le nom ne peut pas être vide."
                )

            employee.last_name = normalized_last_name

        if email is not None:
            normalized_email = email.strip().lower()

            if not normalized_email:
                raise ValidationError(
                    "L'email ne peut pas être vide."
                )

            existing_employee = self.repository.get_by_email(
                normalized_email
            )

            if (
                existing_employee is not None
                and existing_employee.id != employee.id
            ):
                raise DuplicateError(
                    "Un collaborateur utilise déjà cette adresse email."
                )

            employee.email = normalized_email

        if role is not None:
            employee.role = role

        try:
            updated_employee = self.repository.update(employee)
            self.session.commit()

            return updated_employee

        except Exception:
            self.session.rollback()
            raise

    def delete_employee(
        self,
        current_employee: Employee,
        employee_id: int,
    ) -> None:
        """
        Supprime un collaborateur.

        Cette action est exclusivement réservée au service gestion.
        Un gestionnaire ne peut pas supprimer son propre compte.
        """

        self._require_management_role(current_employee)

        employee = self._get_existing_employee(employee_id)

        if employee.id == current_employee.id:
            raise ValidationError(
                "Vous ne pouvez pas supprimer votre propre compte."
            )

        try:
            self.repository.delete(employee)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

    def _get_existing_employee(
        self,
        employee_id: int,
    ) -> Employee:
        employee = self.repository.get_by_id(employee_id)

        if employee is None:
            raise NotFoundError("Collaborateur introuvable.")

        return employee

    @staticmethod
    def _validate_required_fields(
        first_name: str,
        last_name: str,
        email: str,
        password: str,
    ) -> None:
        if not first_name:
            raise ValidationError(
                "Le prénom est obligatoire."
            )

        if not last_name:
            raise ValidationError(
                "Le nom est obligatoire."
            )

        if not email:
            raise ValidationError(
                "L'email est obligatoire."
            )

        if not password:
            raise ValidationError(
                "Le mot de passe est obligatoire."
            )

    @staticmethod
    def _require_management_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.GESTION:
            raise AuthorizationError(
                "Cette action est réservée au service gestion."
            )