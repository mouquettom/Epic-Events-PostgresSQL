from datetime import datetime

from app.models.employee import Employee, Role
from app.models.event import Event
from app.services.event_service import EventService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class EventController:
    """Gère les interactions console liées aux événements."""

    def __init__(
        self,
        event_service: EventService,
        current_session: CurrentSession,
    ) -> None:
        self.event_service = event_service
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
                    should_return = self._run_support_menu()

                case _:
                    return

            if should_return:
                return

    def _run_management_menu(self) -> bool:
        """
        Affiche le menu du service gestion.

        La gestion peut consulter tous les événements,
        filtrer ceux sans support et affecter un collaborateur support.
        """

        print("\n=== Gestion des événements ===")
        print("1. Lister tous les événements")
        print("2. Consulter un événement")
        print("3. Lister les événements sans support")
        print("4. Affecter un collaborateur support")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_events()

            case "2":
                self.get_event()

            case "3":
                self.list_events_without_support()

            case "4":
                self.assign_support()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def _run_commercial_menu(self) -> bool:
        """
        Affiche le menu du service commercial.

        Le commercial peut consulter tous les événements
        et créer un événement pour l'un de ses contrats signés.
        """

        print("\n=== Consultation et création des événements ===")
        print("1. Lister tous les événements")
        print("2. Consulter un événement")
        print("3. Créer un événement")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_events()

            case "2":
                self.get_event()

            case "3":
                self.create_event()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def _run_support_menu(self) -> bool:
        """
        Affiche le menu du service support.

        Le support peut consulter tous les événements,
        filtrer ceux qui lui sont attribués et modifier
        uniquement les événements dont il est responsable.
        """

        print("\n=== Suivi des événements ===")
        print("1. Lister tous les événements")
        print("2. Consulter un événement")
        print("3. Lister mes événements attribués")
        print("4. Modifier l'un de mes événements")
        print("0. Retour")

        choice = input("\nVotre choix : ").strip()

        match choice:
            case "1":
                self.list_events()

            case "2":
                self.get_event()

            case "3":
                self.list_assigned_events()

            case "4":
                self.update_event()

            case "0":
                return True

            case _:
                print("Choix invalide.")

        return False

    def list_events(self) -> None:
        """Affiche tous les événements."""

        employee = self._get_current_employee()

        try:
            events = self.event_service.list_events(employee)

            self._display_event_list(events)

        except EpicEventsError as error:
            self._display_error(error)

    def get_event(self) -> None:
        """Affiche les informations détaillées d'un événement."""

        employee = self._get_current_employee()
        event_id = self._ask_integer(
            "Identifiant de l'événement : "
        )

        if event_id is None:
            return

        try:
            event = self.event_service.get_event(
                current_employee=employee,
                event_id=event_id,
            )

            self._display_event(event)

        except EpicEventsError as error:
            self._display_error(error)

    def create_event(self) -> None:
        """
        Demande les informations nécessaires à la création d'un événement.

        Le service vérifie que le contrat appartient au commercial
        connecté et qu'il est signé.
        """

        employee = self._get_current_employee()

        print("\n=== Création d'un événement ===")

        contract_id = self._ask_integer(
            "Identifiant du contrat : "
        )

        if contract_id is None:
            return

        start_date = self._ask_datetime(
            "Date de début (JJ/MM/AAAA HH:MM) : "
        )

        if start_date is None:
            return

        end_date = self._ask_datetime(
            "Date de fin (JJ/MM/AAAA HH:MM) : "
        )

        if end_date is None:
            return

        location = input("Lieu : ")

        attendees = self._ask_integer(
            "Nombre de participants : "
        )

        if attendees is None:
            return

        notes = input("Notes : ")

        try:
            event = self.event_service.create_event(
                current_employee=employee,
                contract_id=contract_id,
                start_date=start_date,
                end_date=end_date,
                location=location,
                attendees=attendees,
                notes=notes,
            )

            print(
                "\nÉvénement créé avec succès "
                f"(id={event.id})."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def list_events_without_support(self) -> None:
        """
        Affiche les événements sans collaborateur support affecté.

        Cette action est réservée au service gestion.
        """

        employee = self._get_current_employee()

        try:
            events = (
                self.event_service.list_events_without_support(
                    employee
                )
            )

            self._display_event_list(events)

        except EpicEventsError as error:
            self._display_error(error)

    def list_assigned_events(self) -> None:
        """
        Affiche les événements attribués au support connecté.

        Cette action est réservée au service support.
        """

        employee = self._get_current_employee()

        try:
            events = self.event_service.list_assigned_events(
                employee
            )

            self._display_event_list(events)

        except EpicEventsError as error:
            self._display_error(error)

    def update_event(self) -> None:
        """
        Modifie un événement attribué au support connecté.

        Le service vérifie que le collaborateur connecté est bien
        le support responsable de l'événement sélectionné.
        """

        employee = self._get_current_employee()
        event_id = self._ask_integer(
            "Identifiant de l'événement à modifier : "
        )

        if event_id is None:
            return

        print(
            "\nLaissez un champ vide pour conserver "
            "la valeur actuelle."
        )

        start_date = self._ask_optional_datetime(
            "Nouvelle date de début (JJ/MM/AAAA HH:MM) : "
        )

        end_date = self._ask_optional_datetime(
            "Nouvelle date de fin (JJ/MM/AAAA HH:MM) : "
        )

        location = input(
            "Nouveau lieu : "
        ).strip()

        attendees = self._ask_optional_integer(
            "Nouveau nombre de participants : "
        )

        notes = input(
            "Nouvelles notes : "
        ).strip()

        try:
            event = self.event_service.update_event(
                current_employee=employee,
                event_id=event_id,
                start_date=start_date,
                end_date=end_date,
                location=location or None,
                attendees=attendees,
                notes=notes or None,
            )

            print(
                f"\nÉvénement {event.id} "
                "mis à jour avec succès."
            )

        except EpicEventsError as error:
            self._display_error(error)

    def assign_support(self) -> None:
        """
        Affecte un collaborateur support à un événement.

        Cette action est réservée au service gestion.
        """

        employee = self._get_current_employee()

        event_id = self._ask_integer(
            "Identifiant de l'événement : "
        )

        if event_id is None:
            return

        support_id = self._ask_integer(
            "Identifiant du collaborateur support : "
        )

        if support_id is None:
            return

        try:
            event = self.event_service.assign_support(
                current_employee=employee,
                event_id=event_id,
                support_id=support_id,
            )

            print(
                f"\nCollaborateur support {event.support_id} "
                f"affecté à l'événement {event.id}."
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
                "La valeur doit être un nombre entier."
            )
            return None

    @staticmethod
    def _ask_optional_integer(
        message: str,
    ) -> int | None:
        """Demande et valide une valeur entière facultative."""

        raw_value = input(message).strip()

        if not raw_value:
            return None

        try:
            return int(raw_value)

        except ValueError:
            print(
                "La valeur doit être un nombre entier."
            )
            return None

    @staticmethod
    def _ask_datetime(
        message: str,
    ) -> datetime | None:
        """Demande et valide une date obligatoire."""

        raw_value = input(message).strip()

        try:
            return datetime.strptime(
                raw_value,
                "%d/%m/%Y %H:%M",
            )

        except ValueError:
            print(
                "Format invalide. "
                "Utilisez JJ/MM/AAAA HH:MM."
            )
            return None

    @staticmethod
    def _ask_optional_datetime(
        message: str,
    ) -> datetime | None:
        """Demande et valide une date facultative."""

        raw_value = input(message).strip()

        if not raw_value:
            return None

        try:
            return datetime.strptime(
                raw_value,
                "%d/%m/%Y %H:%M",
            )

        except ValueError:
            print(
                "Format invalide. "
                "Utilisez JJ/MM/AAAA HH:MM."
            )
            return None

    @staticmethod
    def _display_event(
        event: Event,
    ) -> None:
        """Affiche les informations détaillées d'un événement."""

        print("\n=== Événement ===")
        print(f"ID : {event.id}")
        print(f"Contrat ID : {event.contract_id}")
        print(
            "Support responsable ID : "
            f"{event.support_id or 'Non affecté'}"
        )
        print(f"Début : {event.start_date}")
        print(f"Fin : {event.end_date}")
        print(f"Lieu : {event.location}")
        print(f"Participants : {event.attendees}")
        print(f"Notes : {event.notes}")

    @staticmethod
    def _display_event_list(
        events: list[Event],
    ) -> None:
        """Affiche une liste synthétique d'événements."""

        if not events:
            print("\nAucun événement trouvé.")
            return

        print("\n=== Liste des événements ===")

        for event in events:
            print(
                f"{event.id} — "
                f"Contrat {event.contract_id} — "
                f"{event.location} — "
                f"{event.start_date} — "
                "Support : "
                f"{event.support_id or 'Non affecté'}"
            )

    @staticmethod
    def _display_error(
        error: Exception,
    ) -> None:
        """Affiche une erreur métier à l'utilisateur."""

        print(f"\nErreur : {error}")