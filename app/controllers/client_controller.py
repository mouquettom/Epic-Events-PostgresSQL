from app.models.employee import Employee
from app.services.client_service import ClientService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class ClientController:
    """ Gère les interactions console liées aux clients. """

    def __init__(
        self, client_service: ClientService, current_session: CurrentSession
    ) -> None:

        self.client_service = client_service
        self.current_session = current_session

    def run(self) -> None:
        while self.current_session.is_authenticated:
            print("\n=== Gestion des clients ===")
            print("1. Lister les clients")
            print("2. Consulter un client")
            print("3. Créer un client")
            print("4. Modifier un client")
            print("5. Supprimer un client")
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
                case "5":
                    self.delete_client()
                case "0":
                    return
                case _:
                    print("Choix invalide.")

    def list_clients(self) -> None:
        employee = self._get_current_employee()

        try:
            clients = self.client_service.list_clients(employee)

            if not clients:
                print("\nAucun client trouvé.")
                return

            print("\n=== Liste des clients ===")

            for client in clients:
                print(
                    f"{client.id} — {client.full_name} — "
                    f"{client.company} — {client.email}"
                )

        except EpicEventsError as error:
            self._display_error(error)

    def get_client(self) -> None:
        employee = self._get_current_employee()
        client_id = self._ask_integer("Identifiant du client : ")

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
                f"\nClient créé avec succès : " f"{client.full_name} (id={client.id})."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def update_client(self) -> None:
        employee = self._get_current_employee()
        client_id = self._ask_integer("Identifiant du client : ")

        if client_id is None:
            return

        print("\nLaissez un champ vide pour conserver " "la valeur actuelle.")

        full_name = input("Nouveau nom complet : ").strip()
        email = input("Nouvel email : ").strip()
        phone = input("Nouveau téléphone : ").strip()
        company = input("Nouvelle entreprise : ").strip()

        try:
            client = self.client_service.update_client(
                current_employee=employee,
                client_id=client_id,
                full_name=full_name or None,
                email=email or None,
                phone=phone or None,
                company=company or None,
            )

            print(f"\nClient {client.id} mis à jour avec succès.")

        except EpicEventsError as error:
            self._display_error(error)

    def delete_client(self) -> None:
        employee = self._get_current_employee()
        client_id = self._ask_integer("Identifiant du client : ")

        if client_id is None:
            return

        confirmation = input("Confirmer la suppression ? (o/N) : ").strip().lower()

        if confirmation != "o":
            print("Suppression annulée.")
            return

        try:
            self.client_service.delete_client(
                current_employee=employee,
                client_id=client_id,
            )

            print("\nClient supprimé avec succès.")

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
            print("L'identifiant doit être un nombre entier.")
            return None

    @staticmethod
    def _display_client(client) -> None:
        print("\n=== Client ===")
        print(f"ID : {client.id}")
        print(f"Nom : {client.full_name}")
        print(f"Email : {client.email}")
        print(f"Téléphone : {client.phone}")
        print(f"Entreprise : {client.company}")
        print(f"Commercial ID : {client.commercial_id}")
        print(f"Créé le : {client.created_at}")
        print(f"Mis à jour le : {client.updated_at}")

    @staticmethod
    def _display_error(error: Exception) -> None:
        print(f"\nErreur : {error}")