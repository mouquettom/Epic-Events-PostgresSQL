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


class ContractService:
    """ Applique les règles métier relatives aux contrats. """

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

        self._require_commercial_role(current_employee)

        client = self._get_existing_client(client_id)
        self._require_client_owner(current_employee, client)

        normalized_total = self._normalize_amount(
            total_amount,
            "Le montant total",
        )
        normalized_remaining = self._normalize_amount(
            remaining_amount,
            "Le montant restant",
        )

        self._validate_amounts(
            normalized_total,
            normalized_remaining,
        )

        contract = Contract(
            total_amount=normalized_total,
            remaining_amount=normalized_remaining,
            is_signed=is_signed,
            client_id=client.id,
            commercial_id=current_employee.id,
        )

        try:
            created_contract = self.contract_repository.create(contract)
            self.session.commit()
            return created_contract

        except Exception:
            self.session.rollback()
            raise

    def get_contract(
            self,
            current_employee: Employee,
            contract_id: int,
    ) -> Contract:

        contract = self._get_existing_contract(contract_id)
        self._require_contract_access(current_employee, contract)

        return contract

    def list_contracts(
            self,
            current_employee: Employee,
    ) -> list[Contract]:

        if current_employee.role == Role.COMMERCIAL:
            return self.contract_repository.get_by_commercial_id(current_employee.id)

        if current_employee.role in {Role.GESTION, Role.SUPPORT}:
            return self.contract_repository.get_all()

        raise AuthorizationError("Vous n'êtes pas autorisé à consulter les contrats.")

    def list_unsigned_contracts(
            self,
            current_employee: Employee,
    ) -> list[Contract]:

        self._require_management_role(current_employee)
        return self.contract_repository.get_unsigned_contracts()

    def list_unpaid_contracts(
            self,
            current_employee: Employee,
    ) -> list[Contract]:

        if current_employee.role not in {
            Role.GESTION,
            Role.COMMERCIAL,
        }:
            raise AuthorizationError(
                "Vous n'êtes pas autorisé à consulter " "les contrats non soldés."
            )

        contracts = self.contract_repository.get_unpaid_contracts()

        if current_employee.role == Role.COMMERCIAL:
            return [
                contract
                for contract in contracts
                if contract.commercial_id == current_employee.id
            ]

        return contracts

    def update_contract(
            self,
            current_employee: Employee,
            contract_id: int,
            total_amount: Decimal | str | int | float | None = None,
            remaining_amount: Decimal | str | int | float | None = None,
            is_signed: bool | None = None,
    ) -> Contract:

        contract = self._get_existing_contract(contract_id)
        self._require_contract_update_permission(
            current_employee,
            contract,
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

        self._validate_amounts(new_total, new_remaining)

        contract.total_amount = new_total
        contract.remaining_amount = new_remaining

        if is_signed is not None:
            contract.is_signed = is_signed

        try:
            updated_contract = self.contract_repository.update(contract)
            self.session.commit()
            return updated_contract

        except Exception:
            self.session.rollback()
            raise

    def delete_contract(
            self,
            current_employee: Employee,
            contract_id: int,
    ) -> None:

        self._require_management_role(current_employee)

        contract = self._get_existing_contract(contract_id)

        try:
            self.contract_repository.delete(contract)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

    def _get_existing_contract(self, contract_id: int) -> Contract:
        contract = self.contract_repository.get_by_id(contract_id)

        if contract is None:
            raise NotFoundError("Contrat introuvable.")

        return contract

    def _get_existing_client(self, client_id: int) -> Client:
        client = self.client_repository.get_by_id(client_id)

        if client is None:
            raise NotFoundError("Client introuvable.")

        return client

    @staticmethod
    def _require_commercial_role(employee: Employee) -> None:
        if employee.role != Role.COMMERCIAL:
            raise AuthorizationError("Seul un commercial peut créer un contrat.")

    @staticmethod
    def _require_management_role(employee: Employee) -> None:
        if employee.role != Role.GESTION:
            raise AuthorizationError("Cette action est réservée au service gestion.")

    @staticmethod
    def _require_client_owner(
            employee: Employee,
            client: Client,
    ) -> None:

        if client.commercial_id != employee.id:
            raise AuthorizationError(
                "Vous ne pouvez créer un contrat que pour vos propres clients."
            )

    @staticmethod
    def _require_contract_access(
            employee: Employee,
            contract: Contract,
    ) -> None:

        if employee.role == Role.COMMERCIAL:
            if contract.commercial_id != employee.id:
                raise AuthorizationError(
                    "Vous ne pouvez consulter que vos propres contrats."
                )
            return

        if employee.role not in {Role.GESTION, Role.SUPPORT}:
            raise AuthorizationError("Vous n'êtes pas autorisé à consulter ce contrat.")

    @staticmethod
    def _require_contract_update_permission(
            employee: Employee,
            contract: Contract,
    ) -> None:

        if employee.role == Role.GESTION:
            return

        if employee.role == Role.COMMERCIAL and contract.commercial_id == employee.id:
            return

        raise AuthorizationError("Vous n'êtes pas autorisé à modifier ce contrat.")

    @staticmethod
    def _normalize_amount(
            value: Decimal | str | int | float,
            field_name: str,
    ) -> Decimal:

        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise ValidationError(
                f"{field_name} doit être un nombre valide."
            ) from error

        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _validate_amounts(
            total_amount: Decimal,
            remaining_amount: Decimal,
    ) -> None:

        if total_amount <= 0:
            raise ValidationError("Le montant total doit être supérieur à zéro.")

        if remaining_amount < 0:
            raise ValidationError("Le montant restant ne peut pas être négatif.")

        if remaining_amount > total_amount:
            raise ValidationError(
                "Le montant restant ne peut pas dépasser " "le montant total."
            )