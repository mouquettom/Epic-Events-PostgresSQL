import logging

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.utils.exceptions import AuthorizationError
from app.utils.jwt import create_access_token, decode_access_token
from app.utils.password import verify_password


logger = logging.getLogger(__name__)


class AuthService:
    """Gère l'authentification des collaborateurs."""

    def __init__(self, session: Session) -> None:
        self.employee_repository = EmployeeRepository(session)

    def authenticate(
        self,
        email: str,
        password: str,
    ) -> str:
        """Authentifie un collaborateur et retourne un JWT."""

        normalized_email = email.strip().lower()

        employee = self.employee_repository.get_by_email(
            normalized_email
        )

        if employee is None:
            logger.warning(
                "Échec d'authentification : collaborateur introuvable."
            )

            raise AuthorizationError(
                "Email ou mot de passe incorrect."
            )

        if not verify_password(
            password,
            employee.password_hash,
        ):
            logger.warning(
                "Échec d'authentification : mot de passe incorrect "
                "pour employee_id=%s.",
                employee.id,
            )

            raise AuthorizationError(
                "Email ou mot de passe incorrect."
            )

        token = create_access_token(employee.id)

        logger.info(
            "Authentification réussie : employee_id=%s, role=%s.",
            employee.id,
            employee.role.value,
        )

        return token

    def get_current_employee(
        self,
        token: str,
    ) -> Employee:
        """Retourne le collaborateur associé au JWT."""

        try:
            employee_id = decode_access_token(token)

        except Exception as error:
            logger.warning(
                "Échec du décodage d'un JWT."
            )

            raise AuthorizationError(
                "Token invalide ou expiré."
            ) from error

        employee = self.employee_repository.get_by_id(
            employee_id
        )

        if employee is None:
            logger.warning(
                "JWT valide mais collaborateur introuvable : "
                "employee_id=%s.",
                employee_id,
            )

            raise AuthorizationError(
                "L'utilisateur associé au token n'existe plus."
            )

        return employee