import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.contract import Contract
from app.models.employee import Employee, Role
from app.repositories.client_repository import ClientRepository
from app.repositories.contract_repository import ContractRepository
from app.utils.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)


logger = logging.getLogger(__name__)


class ContractService:
    """Applique les règles métier relatives aux contrats."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.contract_repository = ContractRepository(session)
        self.client_repository = ClientRepository(session)

    def create_contract(
        self,
        current_employee: Employee,
        client_id: int,
        total_amount: Decimal | str | int | float,
        remaining_amount: Decimal | str | int | float,
        is_signed: bool = False,
    ) -> Contract:
        """
        Crée un contrat pour un client.

        Cette action est exclusivement réservée au service gestion.
        Le commercial associé au contrat est automatiquement celui
        qui est responsable du client.
        """

        self._require_management_role(current_employee)

        client = self._get_existing_client(client_id)

        normalized_total = self._normalize_amount(
            total_amount,
            "Le montant total",
        )

        normalized_remaining = self._normalize_amount(
            remaining_amount,
            "Le montant restant",
        )

        self._validate_amounts(
            total_amount=normalized_total,
            remaining_amount=normalized_remaining,
        )

        contract = Contract(
            total_amount=normalized_total,
            remaining_amount=normalized_remaining,
            is_signed=is_signed,
            client_id=client.id,
            commercial_id=client.commercial_id,
        )

        try:
            created_contract = self.contract_repository.create(
                contract
            )

            self.session.commit()

            logger.info(
                "Contrat créé : contract_id=%s, client_id=%s, "
                "commercial_id=%s, created_by_employee_id=%s.",
                created_contract.id,
                client.id,
                client.commercial_id,
                current_employee.id,
            )

            return created_contract

        except Exception:
            self.session.rollback()

            logger.exception(
                "Erreur technique lors de la création d'un contrat "
                "pour client_id=%s par employee_id=%s.",
                client_id,
                current_employee.id,
            )

            raise

    def get_contract(
        self,
        current_employee: Employee,
        contract_id: int,
    ) -> Contract:
        """
        Retourne un contrat.

        Tous les collaborateurs peuvent consulter tous les contrats
        en lecture seule.
        """

        self._require_valid_role(current_employee)

        return self._get_existing_contract(contract_id)

    def list_contracts(
        self,
        current_employee: Employee,
    ) -> list[Contract]:
        """
        Retourne tous les contrats.

        La lecture est autorisée aux équipes gestion,
        commerciale et support.
        """

        self._require_valid_role(current_employee)

        return self.contract_repository.get_all()

    def list_unsigned_contracts(
        self,
        current_employee: Employee,
    ) -> list[Contract]:
        """
        Retourne les contrats non signés du commercial connecté.

        Ce filtre est réservé au service commercial.
        """

        self._require_commercial_role(current_employee)

        contracts = (
            self.contract_repository.get_unsigned_contracts()
        )

        return [
            contract
            for contract in contracts
            if contract.commercial_id == current_employee.id
        ]

    def list_unpaid_contracts(
        self,
        current_employee: Employee,
    ) -> list[Contract]:
        """
        Retourne les contrats non entièrement payés
        du commercial connecté.

        Ce filtre est réservé au service commercial.
        """

        self._require_commercial_role(current_employee)

        contracts = (
            self.contract_repository.get_unpaid_contracts()
        )

        return [
            contract
            for contract in contracts
            if contract.commercial_id == current_employee.id
        ]

    def update_contract(
        self,
        current_employee: Employee,
        contract_id: int,
        total_amount: Decimal | str | int | float | None = None,
        remaining_amount: Decimal | str | int | float | None = None,
        is_signed: bool | None = None,
    ) -> Contract:
        """
        Modifie un contrat.

        Le service gestion peut modifier tous les contrats.
        Un commercial peut uniquement modifier les contrats
        associés aux clients dont il est responsable.
        """

        contract = self._get_existing_contract(contract_id)

        self._require_contract_update_permission(
            employee=current_employee,
            contract=contract,
        )

        new_total = contract.total_amount
        new_remaining = contract.remaining_amount

        if total_amount is not None:
            new_total = self._normalize_amount(
                total_amount,
                "Le montant total",
            )

        if remaining_amount is not None:
            new_remaining = self._normalize_amount(
                remaining_amount,
                "Le montant restant",
            )

        self._validate_amounts(
            total_amount=new_total,
            remaining_amount=new_remaining,
        )

        contract.total_amount = new_total
        contract.remaining_amount = new_remaining

        if is_signed is not None:
            contract.is_signed = is_signed

        try:
            updated_contract = (
                self.contract_repository.update(contract)
            )

            self.session.commit()

            logger.info(
                "Contrat modifié : contract_id=%s, employee_id=%s, "
                "role=%s.",
                updated_contract.id,
                current_employee.id,
                current_employee.role.value,
            )

            return updated_contract

        except Exception:
            self.session.rollback()

            logger.exception(
                "Erreur technique lors de la modification "
                "du contract_id=%s par employee_id=%s.",
                contract_id,
                current_employee.id,
            )

            raise

    def _get_existing_contract(
        self,
        contract_id: int,
    ) -> Contract:
        contract = self.contract_repository.get_by_id(
            contract_id
        )

        if contract is None:
            raise NotFoundError(
                "Contrat introuvable."
            )

        return contract

    def _get_existing_client(
        self,
        client_id: int,
    ) -> Client:
        client = self.client_repository.get_by_id(
            client_id
        )

        if client is None:
            raise NotFoundError(
                "Client introuvable."
            )

        return client

    @staticmethod
    def _require_management_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.GESTION:
            raise AuthorizationError(
                "Cette action est réservée au service gestion."
            )

    @staticmethod
    def _require_commercial_role(
        employee: Employee,
    ) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError(
                "Cette action est réservée au service commercial."
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
                "Vous n'êtes pas autorisé à consulter les contrats."
            )

    @staticmethod
    def _require_contract_update_permission(
        employee: Employee,
        contract: Contract,
    ) -> None:
        if employee.role == Role.GESTION:
            return

        if (
            employee.role == Role.COMMERCIAL
            and contract.commercial_id == employee.id
        ):
            return

        raise AuthorizationError(
            "Vous n'êtes pas autorisé à modifier ce contrat."
        )

    @staticmethod
    def _normalize_amount(
        value: Decimal | str | int | float,
        field_name: str,
    ) -> Decimal:
        try:
            amount = Decimal(str(value))

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as error:
            raise ValidationError(
                f"{field_name} doit être un nombre valide."
            ) from error

        return amount.quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _validate_amounts(
        total_amount: Decimal,
        remaining_amount: Decimal,
    ) -> None:
        if total_amount <= 0:
            raise ValidationError(
                "Le montant total doit être supérieur à zéro."
            )

        if remaining_amount < 0:
            raise ValidationError(
                "Le montant restant ne peut pas être négatif."
            )

        if remaining_amount > total_amount:
            raise ValidationError(
                "Le montant restant ne peut pas dépasser "
                "le montant total."
            )