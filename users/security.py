from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

# Checked against when the user does not exist, so that the response time
# does not reveal whether a username is registered
DUMMY_HASH = password_hash.hash("dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)
