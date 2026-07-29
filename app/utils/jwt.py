import os
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv


load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60


def create_access_token(employee_id: int) -> str:
    if not JWT_SECRET_KEY:
        raise RuntimeError("La variable JWT_SECRET_KEY est absente du fichier '.env'.")

    now = datetime.now(UTC)

    payload = {
        "sub": str(employee_id),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRATION_MINUTES),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int:
    if not JWT_SECRET_KEY:
        raise RuntimeError("La variable JWT_SECRET_KEY est absente du fichier '.env'.")

    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )

    return int(payload["sub"])