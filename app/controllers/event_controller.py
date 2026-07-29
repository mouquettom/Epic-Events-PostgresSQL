from datetime import datetime

from app.models.employee import Employee
from app.models.event import Event
from app.services.event_service import EventService
from app.session.current_session import CurrentSession
from app.utils.exceptions import EpicEventsError


class EventController:
    """ Gère les interactions console liées aux événements. """

    def __init__(
        self, event_service: EventService, current_session: CurrentSession
    ) -> None:

        self.event_service = event_service
        self.current_session = current_session

    def run(self) -> None:
        while self.current_session.is_authenticated:
            print("\n=== Gestion des événements ===")
            print("1. Lister les événements")
            print("2. Consulter un événement")
            print("3. Créer un événement")
            print("4. Modifier un événement")
            print("5. Lister les événements sans support")
            print("6. Affecter un support")
            print("7. Retirer le support")
            print("8. Supprimer un événement")
            print("0. Retour")

            choice = input("\nVotre choix : ").strip()

            match choice:
                case "1":
                    self.list_events()
                case "2":
                    self.get_event()
                case "3":
                    self.create_event()
                case "4":
                    self.update_event()
                case "5":
                    self.list_events_without_support()
                case "6":
                    self.assign_support()
                case "7":
                    self.remove_support()
                case "8":
                    self.delete_event()
                case "0":
                    return
                case _:
                    print("Choix invalide.")

    def list_events(self) -> None:
        employee = self._get_current_employee()

        try:
            events = self.event_service.list_events(employee)
            self._display_event_list(events)

        except EpicEventsError as error:
            self._display_error(error)

    def get_event(self) -> None:
        employee = self._get_current_employee()
        event_id = self._ask_integer("Identifiant de l'événement : ")

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
        employee = self._get_current_employee()

        print("\n=== Création d'un événement ===")

        contract_id = self._ask_integer("Identifiant du contrat : ")
        if contract_id is None:
            return

        start_date = self._ask_datetime("Date de début (JJ/MM/AAAA HH:MM) : ")
        if start_date is None:
            return

        end_date = self._ask_datetime("Date de fin (JJ/MM/AAAA HH:MM) : ")
        if end_date is None:
            return

        location = input("Lieu : ")
        attendees = self._ask_integer("Nombre de participants : ")
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

            print(f"\nÉvénement créé avec succès " f"(id={event.id}).")

        except EpicEventsError as error:
            self._display_error(error)

    def update_event(self) -> None:
        employee = self._get_current_employee()
        event_id = self._ask_integer("Identifiant de l'événement : ")

        if event_id is None:
            return

        print("\nLaissez un champ vide pour conserver " "la valeur actuelle.")

        start_date = self._ask_optional_datetime(
            "Nouvelle date de début (JJ/MM/AAAA HH:MM) : "
        )
        end_date = self._ask_optional_datetime(
            "Nouvelle date de fin (JJ/MM/AAAA HH:MM) : "
        )

        location = input("Nouveau lieu : ").strip()
        attendees = self._ask_optional_integer("Nouveau nombre de participants : ")
        notes = input("Nouvelles notes : ").strip()

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

            print(f"\nÉvénement {event.id} mis à jour avec succès.")

        except EpicEventsError as error:
            self._display_error(error)

    def list_events_without_support(self) -> None:
        employee = self._get_current_employee()

        try:
            events = self.event_service.list_events_without_support(employee)
            self._display_event_list(events)

        except EpicEventsError as error:
            self._display_error(error)

    def assign_support(self) -> None:
        employee = self._get_current_employee()

        event_id = self._ask_integer("Identifiant de l'événement : ")
        if event_id is None:
            return

        support_id = self._ask_integer("Identifiant de l'employé support : ")
        if support_id is None:
            return

        try:
            event = self.event_service.assign_support(
                current_employee=employee,
                event_id=event_id,
                support_id=support_id,
            )

            print(f"\nSupport {event.support_id} affecté " f"à l'événement {event.id}.")

        except EpicEventsError as error:
            self._display_error(error)

    def remove_support(self) -> None:
        employee = self._get_current_employee()

        event_id = self._ask_integer("Identifiant de l'événement : ")
        if event_id is None:
            return

        try:
            event = self.event_service.remove_support(
                current_employee=employee,
                event_id=event_id,
            )

            print(f"\nSupport retiré de l'événement {event.id}.")

        except EpicEventsError as error:
            self._display_error(error)

    def delete_event(self) -> None:
        employee = self._get_current_employee()
        event_id = self._ask_integer("Identifiant de l'événement : ")

        if event_id is None:
            return

        confirmation = input("Confirmer la suppression ? (o/N) : ").strip().lower()

        if confirmation != "o":
            print("Suppression annulée.")
            return

        try:
            self.event_service.delete_event(
                current_employee=employee,
                event_id=event_id,
            )

            print("\nÉvénement supprimé avec succès.")

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
    def _ask_optional_integer(message: str) -> int | None:
        raw_value = input(message).strip()

        if not raw_value:
            return None

        try:
            return int(raw_value)

        except ValueError:
            print("La valeur doit être un nombre entier.")
            return None

    @staticmethod
    def _ask_datetime(message: str) -> datetime | None:
        raw_value = input(message).strip()

        try:
            return datetime.strptime(raw_value, "%d/%m/%Y %H:%M")

        except ValueError:
            print("Format invalide. Utilisez JJ/MM/AAAA HH:MM.")
            return None

    @staticmethod
    def _ask_optional_datetime(
        message: str,
    ) -> datetime | None:
        raw_value = input(message).strip()

        if not raw_value:
            return None

        try:
            return datetime.strptime(raw_value, "%d/%m/%Y %H:%M")

        except ValueError:
            print("Format invalide. Utilisez JJ/MM/AAAA HH:MM.")
            return None

    @staticmethod
    def _display_event(event: Event) -> None:
        print("\n=== Événement ===")
        print(f"ID : {event.id}")
        print(f"Contrat ID : {event.contract_id}")
        print(f"Support ID : {event.support_id or 'Non affecté'}")
        print(f"Début : {event.start_date}")
        print(f"Fin : {event.end_date}")
        print(f"Lieu : {event.location}")
        print(f"Participants : {event.attendees}")
        print(f"Notes : {event.notes}")

    @classmethod
    def _display_event_list(
        cls,
        events: list[Event],
    ) -> None:
        if not events:
            print("\nAucun événement trouvé.")
            return

        print("\n=== Liste des événements ===")

        for event in events:
            print(
                f"{event.id} — Contrat {event.contract_id} — "
                f"{event.location} — "
                f"{event.start_date} — "
                f"Support : {event.support_id or 'Non affecté'}"
            )

    @staticmethod
    def _display_error(error: Exception) -> None:
        print(f"\nErreur : {error}")