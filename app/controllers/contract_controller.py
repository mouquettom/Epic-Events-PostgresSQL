from decimal import Decimal, InvalidOperation

from app.models.contract import Contract
from app.models.employee import Employee
from app.services.contract_service import ContractService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class ContractController:
    """ Gère les interactions console liées aux contrats. """

    def __init__(
        self, contract_service: ContractService, current_session: CurrentSession
    ) -> None:

        self.contract_service = contract_service
        self.current_session = current_session

    def run(self) -> None:
        while self.current_session.is_authenticated:
            print("\n=== Gestion des contrats ===")
            print("1. Lister les contrats")
            print("2. Consulter un contrat")
            print("3. Créer un contrat")
            print("4. Modifier un contrat")
            print("5. Lister les contrats non signés")
            print("6. Lister les contrats non soldés")
            print("7. Supprimer un contrat")
            print("0. Retour")

            choice = input("\nVotre choix : ").strip()

            match choice:
                case "1":
                    self.list_contracts()
                case "2":
                    self.get_contract()
                case "3":
                    self.create_contract()
                case "4":
                    self.update_contract()
                case "5":
                    self.list_unsigned_contracts()
                case "6":
                    self.list_unpaid_contracts()
                case "7":
                    self.delete_contract()
                case "0":
                    return
                case _:
                    print("Choix invalide.")

    def list_contracts(self) -> None:
        employee = self._get_current_employee()

        try:
            contracts = self.contract_service.list_contracts(employee)
            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def get_contract(self) -> None:
        employee = self._get_current_employee()
        contract_id = self._ask_integer("Identifiant du contrat : ")

        if contract_id is None:
            return

        try:
            contract = self.contract_service.get_contract(
                current_employee=employee,
                contract_id=contract_id,
            )

            self._display_contract(contract)

        except EpicEventsError as error:
            self._display_error(error)

    def create_contract(self) -> None:
        employee = self._get_current_employee()

        print("\n=== Création d'un contrat ===")

        client_id = self._ask_integer("Identifiant du client : ")

        if client_id is None:
            return

        total_amount = self._ask_decimal("Montant total : ")

        if total_amount is None:
            return

        remaining_amount = self._ask_decimal("Montant restant à payer : ")

        if remaining_amount is None:
            return

        is_signed = self._ask_boolean("Le contrat est-il signé ? (o/N) : ")

        try:
            contract = self.contract_service.create_contract(
                current_employee=employee,
                client_id=client_id,
                total_amount=total_amount,
                remaining_amount=remaining_amount,
                is_signed=is_signed,
            )

            print(f"\nContrat créé avec succès " f"(id={contract.id}).")

        except EpicEventsError as error:
            self._display_error(error)

    def update_contract(self) -> None:
        employee = self._get_current_employee()
        contract_id = self._ask_integer("Identifiant du contrat : ")

        if contract_id is None:
            return

        print("\nLaissez un champ vide pour conserver " "la valeur actuelle.")

        total_amount = self._ask_optional_decimal("Nouveau montant total : ")

        remaining_amount = self._ask_optional_decimal("Nouveau montant restant : ")

        signed_choice = input("Modifier le statut signé ? (o/N) : ").strip().lower()

        is_signed = None

        if signed_choice == "o":
            is_signed = self._ask_boolean("Le contrat est-il signé ? (o/N) : ")

        try:
            contract = self.contract_service.update_contract(
                current_employee=employee,
                contract_id=contract_id,
                total_amount=total_amount,
                remaining_amount=remaining_amount,
                is_signed=is_signed,
            )

            print(f"\nContrat {contract.id} mis à jour avec succès.")

        except EpicEventsError as error:
            self._display_error(error)

    def list_unsigned_contracts(self) -> None:
        employee = self._get_current_employee()

        try:
            contracts = self.contract_service.list_unsigned_contracts(employee)
            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def list_unpaid_contracts(self) -> None:
        employee = self._get_current_employee()

        try:
            contracts = self.contract_service.list_unpaid_contracts(employee)
            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def delete_contract(self) -> None:
        employee = self._get_current_employee()
        contract_id = self._ask_integer("Identifiant du contrat : ")

        if contract_id is None:
            return

        confirmation = input("Confirmer la suppression ? (o/N) : ").strip().lower()

        if confirmation != "o":
            print("Suppression annulée.")
            return

        try:
            self.contract_service.delete_contract(
                current_employee=employee,
                contract_id=contract_id,
            )

            print("\nContrat supprimé avec succès.")

        except EpicEventsError as error:
            self._display_error(error)

    def _get_current_employee(self) -> Employee:
        employee = self.current_session.current_employee

        if employee is None:
            raise RuntimeError("Aucun employé connecté dans la session.")

        return employee

    @staticmethod
    def _ask_integer(message: str) -> int | None:
        raw_value = input(message).strip()

        try:
            return int(raw_value)

        except ValueError:
            print("La valeur doit être un nombre entier.")
            return None

    @staticmethod
    def _ask_decimal(message: str) -> Decimal | None:
        raw_value = input(message).strip().replace(",", ".")

        try:
            return Decimal(raw_value)

        except InvalidOperation:
            print("Le montant doit être un nombre valide.")
            return None

    @staticmethod
    def _ask_optional_decimal(
        message: str,
    ) -> Decimal | None:
        raw_value = input(message).strip().replace(",", ".")

        if not raw_value:
            return None

        try:
            return Decimal(raw_value)

        except InvalidOperation:
            print("Le montant doit être un nombre valide.")
            return None

    @staticmethod
    def _ask_boolean(message: str) -> bool:
        return input(message).strip().lower() == "o"

    @staticmethod
    def _display_contract(contract: Contract) -> None:
        print("\n=== Contrat ===")
        print(f"ID : {contract.id}")
        print(f"Client ID : {contract.client_id}")
        print(f"Commercial ID : {contract.commercial_id}")
        print(f"Montant total : {contract.total_amount} €")
        print(f"Montant restant : " f"{contract.remaining_amount} €")
        print(f"Signé : " f"{'Oui' if contract.is_signed else 'Non'}")
        print(f"Créé le : {contract.created_at}")

    @classmethod
    def _display_contract_list(
        cls,
        contracts: list[Contract],
    ) -> None:
        if not contracts:
            print("\nAucun contrat trouvé.")
            return

        print("\n=== Liste des contrats ===")

        for contract in contracts:
            print(
                f"{contract.id} — Client {contract.client_id} — "
                f"Total : {contract.total_amount} € — "
                f"Restant : {contract.remaining_amount} € — "
                f"Signé : {'Oui' if contract.is_signed else 'Non'}"
            )

    @staticmethod
    def _display_error(error: Exception) -> None:
        print(f"\nErreur : {error}")