from app.database.session import engine
from app.models.base import Base

from app import models


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == '__main__':
    init_db()
    print("Tables créées avec succès.")