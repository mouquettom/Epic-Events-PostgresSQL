from app.models.client import Client
from app.models.employee import Employee, Role
from app.services.client_service import ClientService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class ClientController:
    """Gère les interactions console liées aux clients."""

    def __init__(
        self,
        client_service: ClientService,
        current_session: CurrentSession,
    ) -> None:
        self.client_service = client_service
        self.current_session = current_session

    def run(self) -> None:
        """Affiche le menu adapté au rôle du collaborateur connecté."""

        employee = self._get_current_employee()

        while self.current_session.is_authenticated:
            if employee.role == Role.COMMERCIAL:
                should_return = self._run_commercial_menu()
            else:
                should_return = self._run_read_only_menu()

            if should_return:
                return

    def _run_commercial_menu(self) -> bool:
        """
        Affiche le menu destiné au service commercial.

        Le commercial peut consulter tous les clients, créer un client
        et modifier uniquement les clients dont il est responsable.
        """

        print("\n=== Gestion des clients ===")
        print("1. Lister tous les clients")
        print("2. Consulter un client")
        print("3. Créer un client")
        print("4. Modifier l'un de mes clients")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_clients()

            case "2":
                self.get_client()

            case "3":
                self.create_client()

            case "4":
                self.update_client()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def _run_read_only_menu(self) -> bool:
        """
        Affiche le menu de consultation.

        Les collaborateurs des services gestion et support disposent
        d'un accès en lecture seule à tous les clients.
        """

        print("\n=== Consultation des clients ===")
        print("1. Lister tous les clients")
        print("2. Consulter un client")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_clients()

            case "2":
                self.get_client()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def list_clients(self) -> None:
        """Affiche tous les clients accessibles en lecture seule."""

        employee = self._get_current_employee()

        try:
            clients = self.client_service.list_clients(employee)

            self._display_client_list(clients)

        except EpicEventsError as error:
            self._display_error(error)

    def get_client(self) -> None:
        """Affiche les informations détaillées d'un client."""

        employee = self._get_current_employee()
        client_id = self._ask_integer(
            "Identifiant du client : "
        )

        if client_id is None:
            return

        try:
            client = self.client_service.get_client(
                current_employee=employee,
                client_id=client_id,
            )

            self._display_client(client)

        except EpicEventsError as error:
            self._display_error(error)

    def create_client(self) -> None:
        """
        Demande les informations nécessaires à la création d'un client.

        Le service associe automatiquement le client au commercial
        actuellement connecté.
        """

        employee = self._get_current_employee()

        print("\n=== Création d'un client ===")

        full_name = input("Nom complet : ")
        email = input("Email : ")
        phone = input("Téléphone : ")
        company = input("Entreprise : ")

        try:
            client = self.client_service.create_client(
                current_employee=employee,
                full_name=full_name,
                email=email,
                phone=phone,
                company=company,
            )

            print(
                "\nClient créé avec succès : "
                f"{client.full_name} "
                f"(id={client.id})."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def update_client(self) -> None:
        """
        Modifie un client.

        Le service vérifie que le commercial connecté est bien
        responsable du client sélectionné.
        """

        employee = self._get_current_employee()
        client_id = self._ask_integer(
            "Identifiant du client à modifier : "
        )

        if client_id is None:
            return

        print(
            "\nLaissez un champ vide pour conserver "
            "la valeur actuelle."
        )

        full_name = input(
            "Nouveau nom complet : "
        ).strip()

        email = input(
            "Nouvel email : "
        ).strip()

        phone = input(
            "Nouveau téléphone : "
        ).strip()

        company = input(
            "Nouvelle entreprise : "
        ).strip()

        try:
            client = self.client_service.update_client(
                current_employee=employee,
                client_id=client_id,
                full_name=full_name or None,
                email=email or None,
                phone=phone or None,
                company=company or None,
            )

            print(
                f"\nClient {client.id} "
                "mis à jour avec succès."
            )

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
                "L'identifiant doit être un nombre entier."
            )
            return None

    @staticmethod
    def _display_client(
        client: Client,
    ) -> None:
        """Affiche les informations détaillées d'un client."""

        print("\n=== Client ===")
        print(f"ID : {client.id}")
        print(f"Nom : {client.full_name}")
        print(f"Email : {client.email}")
        print(f"Téléphone : {client.phone}")
        print(f"Entreprise : {client.company}")
        print(
            f"Commercial responsable ID : "
            f"{client.commercial_id}"
        )
        print(f"Créé le : {client.created_at}")
        print(
            f"Dernière mise à jour : "
            f"{client.updated_at}"
        )

    @staticmethod
    def _display_client_list(
        clients: list[Client],
    ) -> None:
        """Affiche une liste synthétique de clients."""

        if not clients:
            print("\nAucun client trouvé.")
            return

        print("\n=== Liste des clients ===")

        for client in clients:
            print(
                f"{client.id} — "
                f"{client.full_name} — "
                f"{client.company} — "
                f"{client.email} — "
                f"Commercial ID : "
                f"{client.commercial_id}"
            )

    @staticmethod
    def _display_error(
        error: Exception,
    ) -> None:
        """Affiche une erreur métier à l'utilisateur."""

        print(f"\nErreur : {error}")