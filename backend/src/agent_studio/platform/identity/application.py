from typing import Protocol

from agent_studio.platform.identity.domain import AuthenticatedIdentity, CurrentUser


class UserProvisioner(Protocol):
    def resolve(self, identity: AuthenticatedIdentity) -> CurrentUser: ...


def resolve_current_user(
    identity: AuthenticatedIdentity,
    provisioner: UserProvisioner,
) -> CurrentUser:
    return provisioner.resolve(identity)
