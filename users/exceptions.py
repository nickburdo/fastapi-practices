class UsernameTakenError(Exception):
    def __init__(self, username: str) -> None:
        super().__init__(f"Username {username!r} is already taken.")
        self.username = username


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} not found.")
        self.user_id = user_id


class SelfDeletionError(Exception):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} tried to delete themselves.")
        self.user_id = user_id
