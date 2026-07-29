from collections.abc import Callable

import sentry_sdk
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.controllers.auth_controller import AuthController
from app.controllers.main_menu_controller import MainMenuController
from app.controllers.employee_controller import EmployeeController
from app.controllers.client_controller import ClientController
from app.controllers.contract_controller import ContractController
from app.controllers.event_controller import EventController
from app.services.employee_service import EmployeeService
from app.services.client_service import ClientService
from app.services.contract_service import ContractService
from app.services.event_service import EventService
from app.database.session import SessionLocal
from app.session.current_session import CurrentSession
from app.utils.sentry import init_sentry


def run_application(
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:

    db_session = session_factory()
    current_session = CurrentSession()

    auth_controller = AuthController(
        db_session=db_session,
        current_session=current_session,
    )

    employee_service = EmployeeService(db_session)

    employee_controller = EmployeeController(
        employee_service=employee_service,
        current_session=current_session,
    )

    client_service = ClientService(db_session)

    client_controller = ClientController(
        client_service=client_service,
        current_session=current_session,
    )

    contract_service = ContractService(db_session)

    contract_controller = ContractController(
        contract_service=contract_service,
        current_session=current_session,
    )

    event_service = EventService(db_session)

    event_controller = EventController(
        event_service=event_service,
        current_session=current_session,
    )

    main_menu_controller = MainMenuController(
        current_session=current_session,
        auth_controller=auth_controller,
        employee_controller=employee_controller,
        client_controller=client_controller,
        contract_controller=contract_controller,
        event_controller=event_controller,
    )

    try:
        while True:
            print("\n" + "=" * 45)
            print("EPIC EVENTS CRM")
            print("=" * 45)
            print("1. Se connecter")
            print("0. Quitter")

            choice = input("\nVotre choix : ").strip()

            if choice == "1":
                if auth_controller.login():
                    main_menu_controller.run()

            elif choice == "0":
                print("\nFermeture de l'application.")
                break

            else:
                print("Choix invalide.")

    except KeyboardInterrupt:
        print("\n\nFermeture de l'application.")

    except Exception as error:
        sentry_sdk.capture_exception(error)
        sentry_sdk.flush(timeout=5.0)

        print(
            "\nUne erreur technique inattendue est survenue. "
            "Elle a été transmise à Sentry."
        )

    finally:
        db_session.close()


if __name__ == "__main__":
    load_dotenv()
    init_sentry()
    run_application()