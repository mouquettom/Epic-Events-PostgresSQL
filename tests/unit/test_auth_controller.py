from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.controllers.auth_controller import AuthController
from app.models.employee import Role
from app.utils.exceptions import AuthorizationError


def make_employee(
    *,
    first_name: str = "Alice",
    last_name: str = "Martin",
    role: Role = Role.GESTION,
):
    """Crée un employé minimal pour les tests du contrôleur."""
    return SimpleNamespace(
        id=1,
        first_name=first_name,
        last_name=last_name,
        email="alice@example.com",
        role=role,
    )


@pytest.fixture
def db_session():
    return Mock()


@pytest.fixture
def current_session():
    session = Mock()
    session.login = Mock()
    session.logout = Mock()
    return session


@pytest.fixture
def controller(db_session, current_session):
    controller = AuthController(
        db_session=db_session,
        current_session=current_session,
    )
    controller.auth_service = Mock()
    return controller


@patch(
    "app.controllers.auth_controller.getpass",
    return_value="secret-password",
)
@patch(
    "builtins.input",
    return_value="  ALICE@EXAMPLE.COM  ",
)
def test_login_authenticates_employee_and_opens_session(
    input_mock,
    getpass_mock,
    controller,
    current_session,
    capsys,
) -> None:
    employee = make_employee(
        first_name="Alice",
        last_name="Martin",
        role=Role.GESTION,
    )
    controller.auth_service.authenticate.return_value = "access-token"
    controller.auth_service.get_current_employee.return_value = employee

    result = controller.login()

    assert result is True

    input_mock.assert_called_once_with("Email : ")
    getpass_mock.assert_called_once_with("Mot de passe : ")

    controller.auth_service.authenticate.assert_called_once_with(
        email="alice@example.com",
        password="secret-password",
    )
    controller.auth_service.get_current_employee.assert_called_once_with(
        "access-token"
    )
    current_session.login.assert_called_once_with(
        employee=employee,
        access_token="access-token",
    )

    output = capsys.readouterr().out
    assert "Connexion à Epic Events" in output
    assert "Connexion réussie" in output
    assert "Bienvenue Alice Martin" in output
    assert "Rôle : GESTION" in output


@pytest.mark.parametrize(
    "role",
    [Role.GESTION, Role.COMMERCIAL, Role.SUPPORT],
)
@patch(
    "app.controllers.auth_controller.getpass",
    return_value="secret-password",
)
@patch(
    "builtins.input",
    return_value="employee@example.com",
)
def test_login_displays_employee_role(
    input_mock,
    getpass_mock,
    controller,
    current_session,
    capsys,
    role,
) -> None:
    employee = make_employee(role=role)
    controller.auth_service.authenticate.return_value = "token"
    controller.auth_service.get_current_employee.return_value = employee

    result = controller.login()

    assert result is True
    assert f"Rôle : {role.value}" in capsys.readouterr().out
    current_session.login.assert_called_once_with(
        employee=employee,
        access_token="token",
    )


@patch(
    "app.controllers.auth_controller.getpass",
    return_value="wrong-password",
)
@patch(
    "builtins.input",
    return_value="unknown@example.com",
)
def test_login_returns_false_when_authentication_fails(
    input_mock,
    getpass_mock,
    controller,
    current_session,
    capsys,
) -> None:
    controller.auth_service.authenticate.side_effect = AuthorizationError(
        "Identifiants invalides."
    )

    result = controller.login()

    assert result is False

    controller.auth_service.authenticate.assert_called_once_with(
        email="unknown@example.com",
        password="wrong-password",
    )
    controller.auth_service.get_current_employee.assert_not_called()
    current_session.login.assert_not_called()

    output = capsys.readouterr().out
    assert "Erreur : Identifiants invalides." in output


@patch(
    "app.controllers.auth_controller.getpass",
    return_value="secret-password",
)
@patch(
    "builtins.input",
    return_value="alice@example.com",
)
def test_login_returns_false_when_token_employee_lookup_fails(
    input_mock,
    getpass_mock,
    controller,
    current_session,
    capsys,
) -> None:
    controller.auth_service.authenticate.return_value = "invalid-token"
    controller.auth_service.get_current_employee.side_effect = (
        AuthorizationError("Token invalide.")
    )

    result = controller.login()

    assert result is False

    controller.auth_service.authenticate.assert_called_once_with(
        email="alice@example.com",
        password="secret-password",
    )
    controller.auth_service.get_current_employee.assert_called_once_with(
        "invalid-token"
    )
    current_session.login.assert_not_called()

    output = capsys.readouterr().out
    assert "Erreur : Token invalide." in output


@patch(
    "app.controllers.auth_controller.getpass",
    return_value="secret-password",
)
@patch(
    "builtins.input",
    return_value="   ",
)
def test_login_passes_empty_normalized_email_to_service(
    input_mock,
    getpass_mock,
    controller,
    current_session,
    capsys,
) -> None:
    controller.auth_service.authenticate.side_effect = AuthorizationError(
        "Email obligatoire."
    )

    result = controller.login()

    assert result is False
    controller.auth_service.authenticate.assert_called_once_with(
        email="",
        password="secret-password",
    )
    current_session.login.assert_not_called()
    assert "Erreur : Email obligatoire." in capsys.readouterr().out


def test_logout_closes_session_and_displays_confirmation(
    controller,
    current_session,
    capsys,
) -> None:
    result = controller.logout()

    assert result is None
    current_session.logout.assert_called_once_with()

    output = capsys.readouterr().out
    assert "Vous êtes maintenant déconnecté." in output


def test_constructor_creates_auth_service_with_database_session(
    db_session,
    current_session,
) -> None:
    with patch(
        "app.controllers.auth_controller.AuthService"
    ) as auth_service_class:
        auth_service_instance = Mock()
        auth_service_class.return_value = auth_service_instance

        controller = AuthController(
            db_session=db_session,
            current_session=current_session,
        )

    auth_service_class.assert_called_once_with(db_session)
    assert controller.auth_service is auth_service_instance
    assert controller.current_session is current_session