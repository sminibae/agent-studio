import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    issuer: str
    subject: str
    email: str
    display_name: str | None


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    issuer: str
    subject: str
    email: str
    display_name: str | None
