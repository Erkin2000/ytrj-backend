import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "$".join(
        [
            ALGORITHM,
            str(ITERATIONS),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        # Хешируем впустую, чтобы время ответа не выдавало существование пользователя.
        hash_password(password)
        return False

    try:
        algorithm, iterations, salt, digest = hashed_password.split("$")
    except ValueError:
        return False

    if algorithm != ALGORITHM:
        return False

    expected = base64.b64decode(digest)
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        base64.b64decode(salt),
        int(iterations),
    )
    return hmac.compare_digest(actual, expected)
