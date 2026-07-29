from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee


class EmployeeRepository:
    """ Accès aux données des employés. """

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self.session.get(Employee, employee_id)

    def get_by_email(self, email: str) -> Employee | None:
        statement = select(Employee).where(Employee.email == email)
        return self.session.scalar(statement)

    def get_all(self) -> list[Employee]:
        statement = select(Employee).order_by(Employee.id)
        return list(self.session.scalars(statement).all())

    def create(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        self.session.refresh(employee)
        return employee

    def update(self, employee: Employee) -> Employee:
        self.session.flush()
        self.session.refresh(employee)
        return employee

    def delete(self, employee: Employee) -> None:
        self.session.delete(employee)
        self.session.flush()