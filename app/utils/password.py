import bcrypt

from app.utils.exceptions import ValidationError


def hash_password(password: str) -> str:
    """ Transforme un mot de passe en hash bcrypt. """

    if not password or len(password) < 8:
        raise ValidationError(
            "Le mot de passe doit contenir au moins 8 caractères."
        )

    password_bytes = password.encode("utf-8")
    hashed_password = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    )

    return hashed_password.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe en clair contre un hash bcrypt."""

    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    except (ValueError, TypeError):
        return False