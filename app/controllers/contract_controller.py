from decimal import Decimal, InvalidOperation

from app.models.contract import Contract
from app.models.employee import Employee, Role
from app.services.contract_service import ContractService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class ContractController:
    """Gère les interactions console liées aux contrats."""

    def __init__(
        self,
        contract_service: ContractService,
        current_session: CurrentSession,
    ) -> None:
        self.contract_service = contract_service
        self.current_session = current_session

    def run(self) -> None:
        """Affiche le menu adapté au rôle du collaborateur connecté."""

        employee = self._get_current_employee()

        while self.current_session.is_authenticated:
            match employee.role:
                case Role.GESTION:
                    should_return = self._run_management_menu()

                case Role.COMMERCIAL:
                    should_return = self._run_commercial_menu()

                case Role.SUPPORT:
                    should_return = self._run_read_only_menu()

                case _:
                    return

            if should_return:
                return

    def _run_management_menu(self) -> bool:
        """
        Affiche le menu du service gestion.

        La gestion peut consulter tous les contrats, en créer
        et modifier n'importe quel contrat.
        """

        print("\n=== Gestion des contrats ===")
        print("1. Lister tous les contrats")
        print("2. Consulter un contrat")
        print("3. Créer un contrat")
        print("4. Modifier un contrat")
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

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def _run_commercial_menu(self) -> bool:
        """
        Affiche le menu du service commercial.

        Le commercial peut consulter tous les contrats, modifier
        ceux de ses clients et utiliser les filtres demandés.
        """

        print("\n=== Consultation et suivi des contrats ===")
        print("1. Lister tous les contrats")
        print("2. Consulter un contrat")
        print("3. Modifier le contrat d'un de mes clients")
        print("4. Lister mes contrats non signés")
        print("5. Lister mes contrats non soldés")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_contracts()

            case "2":
                self.get_contract()

            case "3":
                self.update_contract()

            case "4":
                self.list_unsigned_contracts()

            case "5":
                self.list_unpaid_contracts()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def _run_read_only_menu(self) -> bool:
        """
        Affiche le menu de consultation du support.

        Le support possède un accès en lecture seule à tous
        les contrats.
        """

        print("\n=== Consultation des contrats ===")
        print("1. Lister tous les contrats")
        print("2. Consulter un contrat")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_contracts()

            case "2":
                self.get_contract()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def list_contracts(self) -> None:
        """Affiche tous les contrats."""

        employee = self._get_current_employee()

        try:
            contracts = self.contract_service.list_contracts(
                employee
            )

            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def get_contract(self) -> None:
        """Affiche les informations détaillées d'un contrat."""

        employee = self._get_current_employee()
        contract_id = self._ask_integer(
            "Identifiant du contrat : "
        )

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
        """
        Demande les informations nécessaires à la création d'un contrat.

        Le service récupère automatiquement le commercial associé
        au client sélectionné.
        """

        employee = self._get_current_employee()

        print("\n=== Création d'un contrat ===")

        client_id = self._ask_integer(
            "Identifiant du client : "
        )

        if client_id is None:
            return

        total_amount = self._ask_decimal(
            "Montant total : "
        )

        if total_amount is None:
            return

        remaining_amount = self._ask_decimal(
            "Montant restant à payer : "
        )

        if remaining_amount is None:
            return

        is_signed = self._ask_boolean(
            "Le contrat est-il signé ? (o/N) : "
        )

        try:
            contract = self.contract_service.create_contract(
                current_employee=employee,
                client_id=client_id,
                total_amount=total_amount,
                remaining_amount=remaining_amount,
                is_signed=is_signed,
            )

            print(
                "\nContrat créé avec succès "
                f"(id={contract.id})."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def update_contract(self) -> None:
        """
        Modifie un contrat.

        Le service vérifie les autorisations :
        - gestion : tous les contrats ;
        - commercial : contrats de ses clients uniquement.
        """

        employee = self._get_current_employee()
        contract_id = self._ask_integer(
            "Identifiant du contrat à modifier : "
        )

        if contract_id is None:
            return

        print(
            "\nLaissez un champ vide pour conserver "
            "la valeur actuelle."
        )

        total_amount = self._ask_optional_decimal(
            "Nouveau montant total : "
        )

        remaining_amount = self._ask_optional_decimal(
            "Nouveau montant restant : "
        )

        signed_choice = input(
            "Modifier le statut signé ? (o/N) : "
        ).strip().lower()

        is_signed = None

        if signed_choice == "o":
            is_signed = self._ask_boolean(
                "Le contrat est-il signé ? (o/N) : "
            )

        try:
            contract = self.contract_service.update_contract(
                current_employee=employee,
                contract_id=contract_id,
                total_amount=total_amount,
                remaining_amount=remaining_amount,
                is_signed=is_signed,
            )

            print(
                f"\nContrat {contract.id} "
                "mis à jour avec succès."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def list_unsigned_contracts(self) -> None:
        """
        Affiche les contrats non signés associés
        au commercial connecté.
        """

        employee = self._get_current_employee()

        try:
            contracts = (
                self.contract_service.list_unsigned_contracts(
                    employee
                )
            )

            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def list_unpaid_contracts(self) -> None:
        """
        Affiche les contrats non entièrement payés associés
        au commercial connecté.
        """

        employee = self._get_current_employee()

        try:
            contracts = (
                self.contract_service.list_unpaid_contracts(
                    employee
                )
            )

            self._display_contract_list(contracts)

        except EpicEventsError as error:
            self._display_error(error)

    def _get_current_employee(self) -> Employee:
        """Retourne le collaborateur actuellement connecté."""

        employee = self.current_session.current_employee

        if employee is None:
            raise RuntimeError(
                "Aucun collaborateur connecté dans la session."
            )

        return employee

    @staticmethod
    def _ask_integer(
        message: str,
    ) -> int | None:
        """Demande et valide une valeur entière."""

        raw_value = input(message).strip()

        try:
            return int(raw_value)

        except ValueError:
            print(
                "La valeur doit être un nombre entier."
            )
            return None

    @staticmethod
    def _ask_decimal(
        message: str,
    ) -> Decimal | None:
        """Demande et valide un montant obligatoire."""

        raw_value = input(message).strip().replace(",", ".")

        try:
            return Decimal(raw_value)

        except InvalidOperation:
            print(
                "Le montant doit être un nombre valide."
            )
            return None

    @staticmethod
    def _ask_optional_decimal(
        message: str,
    ) -> Decimal | None:
        """Demande et valide un montant facultatif."""

        raw_value = input(message).strip().replace(",", ".")

        if not raw_value:
            return None

        try:
            return Decimal(raw_value)

        except InvalidOperation:
            print(
                "Le montant doit être un nombre valide."
            )
            return None

    @staticmethod
    def _ask_boolean(
        message: str,
    ) -> bool:
        """Retourne True lorsque l'utilisateur répond par 'o'."""

        return input(message).strip().lower() == "o"

    @staticmethod
    def _display_contract(
        contract: Contract,
    ) -> None:
        """Affiche les informations détaillées d'un contrat."""

        print("\n=== Contrat ===")
        print(f"ID : {contract.id}")
        print(f"Client ID : {contract.client_id}")
        print(
            f"Commercial responsable ID : "
            f"{contract.commercial_id}"
        )
        print(
            f"Montant total : "
            f"{contract.total_amount} €"
        )
        print(
            f"Montant restant : "
            f"{contract.remaining_amount} €"
        )
        print(
            "Signé : "
            f"{'Oui' if contract.is_signed else 'Non'}"
        )
        print(f"Créé le : {contract.created_at}")

    @staticmethod
    def _display_contract_list(
        contracts: list[Contract],
    ) -> None:
        """Affiche une liste synthétique de contrats."""

        if not contracts:
            print("\nAucun contrat trouvé.")
            return

        print("\n=== Liste des contrats ===")

        for contract in contracts:
            print(
                f"{contract.id} — "
                f"Client {contract.client_id} — "
                f"Commercial {contract.commercial_id} — "
                f"Total : {contract.total_amount} € — "
                f"Restant : {contract.remaining_amount} € — "
                f"Signé : "
                f"{'Oui' if contract.is_signed else 'Non'}"
            )

    @staticmethod
    def _display_error(
        error: Exception,
    ) -> None:
        """Affiche une erreur métier à l'utilisateur."""

        print(f"\nErreur : {error}")