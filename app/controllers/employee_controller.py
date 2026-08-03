from getpass import getpass

from app.models.employee import Employee, Role
from app.services.employee_service import EmployeeService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class EmployeeController:
    """Gère les interactions console liées aux collaborateurs."""

    def __init__(
        self,
        employee_service: EmployeeService,
        current_session: CurrentSession,
    ) -> None:
        self.employee_service = employee_service
        self.current_session = current_session

    def run(self) -> None:
        """
        Affiche le menu de gestion des collaborateurs.

        Ce controller est destiné au service gestion.
        Les autorisations sont également vérifiées dans le service.
        """

        while self.current_session.is_authenticated:
            print("\n=== Gestion des collaborateurs ===")
            print("1. Lister les collaborateurs")
            print("2. Consulter un collaborateur")
            print("3. Créer un collaborateur")
            print("4. Modifier un collaborateur")
            print("5. Supprimer un collaborateur")
            print("0. Retour")

            choice = input("\nVotre choix : ").strip()

            match choice:
                case "1":
                    self.list_employees()

                case "2":
                    self.get_employee()

                case "3":
                    self.create_employee()

                case "4":
                    self.update_employee()

                case "5":
                    self.delete_employee()

                case "0":
                    return

                case _:
                    print("Choix invalide.")

    def list_employees(self) -> None:
        """Affiche la liste des collaborateurs."""

        current_employee = self._get_current_employee()

        try:
            employees = self.employee_service.list_employees(
                current_employee
            )

            self._display_employee_list(employees)

        except EpicEventsError as error:
            self._display_error(error)

    def get_employee(self) -> None:
        """Affiche les informations détaillées d'un collaborateur."""

        current_employee = self._get_current_employee()

        employee_id = self._ask_integer(
            "Identifiant du collaborateur : "
        )

        if employee_id is None:
            return

        try:
            employee = self.employee_service.get_employee(
                current_employee=current_employee,
                employee_id=employee_id,
            )

            self._display_employee(employee)

        except EpicEventsError as error:
            self._display_error(error)

    def create_employee(self) -> None:
        """Demande les informations nécessaires à la création d'un collaborateur."""

        current_employee = self._get_current_employee()

        print("\n=== Création d'un collaborateur ===")

        first_name = input("Prénom : ").strip()
        last_name = input("Nom : ").strip()
        email = input("Email : ").strip()

        role = self._ask_role()

        if role is None:
            return

        password = getpass("Mot de passe : ")
        password_confirmation = getpass(
            "Confirmez le mot de passe : "
        )

        if password != password_confirmation:
            print(
                "\nErreur : les mots de passe "
                "ne correspondent pas."
            )
            return

        try:
            employee = self.employee_service.create_employee(
                current_employee=current_employee,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                role=role,
            )

            print(
                "\nCollaborateur créé avec succès : "
                f"{employee.first_name} "
                f"{employee.last_name} "
                f"(id={employee.id}, "
                f"rôle={employee.role.value})."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def update_employee(self) -> None:
        """Modifie les informations d'un collaborateur."""

        current_employee = self._get_current_employee()

        employee_id = self._ask_integer(
            "Identifiant du collaborateur à modifier : "
        )

        if employee_id is None:
            return

        print(
            "\nLaissez un champ vide pour conserver "
            "la valeur actuelle."
        )

        first_name = input(
            "Nouveau prénom : "
        ).strip()

        last_name = input(
            "Nouveau nom : "
        ).strip()

        email = input(
            "Nouvel email : "
        ).strip()

        change_role = input(
            "Modifier le rôle ? (o/N) : "
        ).strip().lower()

        role = None

        if change_role == "o":
            role = self._ask_role()

            if role is None:
                return

        try:
            employee = self.employee_service.update_employee(
                current_employee=current_employee,
                employee_id=employee_id,
                first_name=first_name or None,
                last_name=last_name or None,
                email=email or None,
                role=role,
            )

            print(
                f"\nCollaborateur {employee.id} "
                "mis à jour avec succès."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def delete_employee(self) -> None:
        """Supprime un collaborateur après confirmation."""

        current_employee = self._get_current_employee()

        employee_id = self._ask_integer(
            "Identifiant du collaborateur à supprimer : "
        )

        if employee_id is None:
            return

        confirmation = input(
            "Confirmer la suppression ? (o/N) : "
        ).strip().lower()

        if confirmation != "o":
            print("Suppression annulée.")
            return

        try:
            self.employee_service.delete_employee(
                current_employee=current_employee,
                employee_id=employee_id,
            )

            print(
                "\nCollaborateur supprimé avec succès."
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
                "L'identifiant doit être "
                "un nombre entier."
            )
            return None

    @staticmethod
    def _ask_role() -> Role | None:
        """Demande et valide le rôle d'un collaborateur."""

        print("\nChoisissez un rôle :")
        print("1. COMMERCIAL")
        print("2. GESTION")
        print("3. SUPPORT")

        choice = input("Votre choix : ").strip()

        role_by_choice = {
            "1": Role.COMMERCIAL,
            "2": Role.GESTION,
            "3": Role.SUPPORT,
        }

        role = role_by_choice.get(choice)

        if role is None:
            print("Rôle invalide.")

        return role

    @staticmethod
    def _display_employee(
        employee: Employee,
    ) -> None:
        """Affiche les informations détaillées d'un collaborateur."""

        print("\n=== Collaborateur ===")
        print(f"ID : {employee.id}")
        print(f"Prénom : {employee.first_name}")
        print(f"Nom : {employee.last_name}")
        print(f"Email : {employee.email}")
        print(f"Rôle : {employee.role.value}")

    @staticmethod
    def _display_employee_list(
        employees: list[Employee],
    ) -> None:
        """Affiche une liste synthétique de collaborateurs."""

        if not employees:
            print("\nAucun collaborateur trouvé.")
            return

        print("\n=== Liste des collaborateurs ===")

        for employee in employees:
            print(
                f"{employee.id} — "
                f"{employee.first_name} "
                f"{employee.last_name} — "
                f"{employee.email} — "
                f"{employee.role.value}"
            )

    @staticmethod
    def _display_error(
        error: Exception,
    ) -> None:
        """Affiche une erreur métier à l'utilisateur."""

        print(f"\nErreur : {error}")