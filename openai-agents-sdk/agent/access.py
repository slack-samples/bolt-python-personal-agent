import os


def owner_user_id() -> str | None:
    return os.environ.get("OWNER_USER_ID") or None


def is_owner(user_id: str | None) -> bool:
    owner = owner_user_id()
    return owner is not None and user_id == owner


def reply_user_token(user_token: str | None, is_private_reply: bool) -> str | None:
    return user_token if is_private_reply else None
