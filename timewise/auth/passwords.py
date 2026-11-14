"""Salted PBKDF2 hashing for passwords and recovery codes."""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 600_000


def _derive(secret: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations).hex()


def hash_secret(secret: str) -> str:
    """Return a self-describing hash: ``algorithm$iterations$salt$digest``."""
    salt = secrets.token_bytes(16)
    digest = _derive(secret, salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest}"


def verify_secret(secret: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest = stored_hash.split("$")
        candidate = _derive(secret, bytes.fromhex(salt_hex), int(iterations))
    except ValueError:
        return False
    return algorithm == _ALGORITHM and hmac.compare_digest(candidate, digest)
