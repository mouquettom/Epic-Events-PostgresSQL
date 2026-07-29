from app.controllers.auth_controller import AuthController
from app.controllers.employee_controller import EmployeeController
from app.controllers.client_controller import ClientController
from app.controllers.contract_controller import ContractController
from app.controllers.event_controller import EventController
from app.models.employee import Role
from app.session.current_session import CurrentSession


class MainMenuController:
    """ Affiche le menu principal selon le rôle de l'employé. """

    def __init__(
        self,
        current_session: CurrentSession,
        auth_controller: AuthController,
        employee_controller: EmployeeController,
        client_controller: ClientController,
        contract_controller: ContractController,
        event_controller: EventController,
    ) -> None:

        self.current_session = current_session
        self.auth_controller = auth_controller
        self.employee_controller = employee_controller
        self.client_controller = client_controller
        self.contract_controller = contract_controller
        self.event_controller = event_controller

    def run(self) -> None:
        while self.current_session.is_authenticated:
            employee = self.current_session.current_employee

            if employee is None:
                return

            self._display_header()

            if employee.role == Role.GESTION:
                self._run_management_menu()

            elif employee.role == Role.COMMERCIAL:
                self._run_commercial_menu()

            elif employee.role == Role.SUPPORT:
                self._run_support_menu()

    def _display_header(self) -> None:
        employee = self.current_session.current_employee

        if employee is None:
            return

        print("\n" + "=" * 45)
        print("EPIC EVENTS CRM")
        print("=" * 45)
        print(f"Utilisateur : " f"{employee.first_name} {employee.last_name}")
        print(f"Rôle : {employee.role.value}")
        print("=" * 45)

    def _run_management_menu(self) -> None:
        print("1. Gérer les employés")
        print("2. Consulter les clients")
        print("3. Gérer les contrats")
        print("4. Gérer les événements")
        print("0. Se déconnecter")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.employee_controller.run()
            case "2":
                self.client_controller.run()
            case "3":
                self.contract_controller.run()
            case "4":
                self.event_controller.run()
            case "0":
                self.auth_controller.logout()
            case _:
                print("Choix invalide.")

    def _run_commercial_menu(self) -> None:
        print("1. Gérer mes clients")
        print("2. Gérer mes contrats")
        print("3. Consulter mes événements")
        print("0. Se déconnecter")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.client_controller.run()
            case "2":
                self.contract_controller.run()
            case "3":
                self.event_controller.run()
            case "0":
                self.auth_controller.logout()
            case _:
                print("Choix invalide.")

    def _run_support_menu(self) -> None:
        print("1. Consulter mes événements")
        print("0. Se déconnecter")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.event_controller.run()
            case "0":
                self.auth_controller.logout()
            case _:
                print("Choix invalide.")

    @staticmethod
    def _not_implemented(feature_name: str) -> None:
        print(f"\n{feature_name} : fonctionnalité à venir.")