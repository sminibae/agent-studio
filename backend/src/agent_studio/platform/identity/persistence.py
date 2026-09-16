from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from uuid6 import uuid7

from agent_studio.platform.database import get_session_factory
from agent_studio.platform.identity.domain import AuthenticatedIdentity, CurrentUser
from agent_studio.platform.users.persistence import AppUserModel


class SqlAlchemyUserProvisioner:
    def resolve(self, identity: AuthenticatedIdentity) -> CurrentUser:
        now = datetime.now(UTC)
        proposed_user = insert(AppUserModel).values(
            id=uuid7(),
            auth_issuer=identity.issuer,
            auth_subject=identity.subject,
            email=identity.email,
            display_name=identity.display_name,
            created_at=now,
            updated_at=now,
        )
        statement = proposed_user.on_conflict_do_update(
            index_elements=["auth_issuer", "auth_subject"],
            set_={
                "email": proposed_user.excluded.email,
                "display_name": proposed_user.excluded.display_name,
                "updated_at": proposed_user.excluded.updated_at,
            },
        )

        with get_session_factory().begin() as session:
            session.execute(statement)
            user = session.scalar(
                select(AppUserModel).where(
                    AppUserModel.auth_issuer == identity.issuer,
                    AppUserModel.auth_subject == identity.subject,
                )
            )
            if user is None:
                raise RuntimeError("user provisioning did not produce a user")
            return CurrentUser(
                id=user.id,
                issuer=user.auth_issuer,
                subject=user.auth_subject,
                email=user.email,
                display_name=user.display_name,
            )
