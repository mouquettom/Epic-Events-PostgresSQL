from app.utils.password import hash_password, verify_password


def test_hash_password_returns_different_value() -> None:
    password = "StrongPassword123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert isinstance(password_hash, str)


def test_verify_password_with_correct_password() -> None:
    password = "StrongPassword123!"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_with_wrong_password() -> None:
    password_hash = hash_password("StrongPassword123!")

    assert verify_password("WrongPassword", password_hash) is False