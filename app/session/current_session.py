from app.models.employee import Employee


class CurrentSession:
    """ Mémorise l'employé actuellement connecté à l'application. """

    def __init__(self) -> None:
        self._current_employee: Employee | None = None
        self._access_token: str | None = None

    @property
    def current_employee(self) -> Employee | None:
        return self._current_employee

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def is_authenticated(self) -> bool:
        return self._current_employee is not None

    def login(
        self,
        employee: Employee,
        access_token: str,
    ) -> None:
        self._current_employee = employee
        self._access_token = access_token

    def logout(self) -> None:
        self._current_employee = None
        self._access_token = None