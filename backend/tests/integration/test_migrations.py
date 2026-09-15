import os

import pytest
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.integration


def test_app_user_migration_has_identity_constraint() -> None:
    database_url = os.environ["AGENT_STUDIO_DATABASE_URL"]
    engine = create_engine(database_url)

    with engine.connect() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("app_user")
        }
        constraints = inspect(connection).get_unique_constraints("app_user")
        connection.execute(text("SELECT 1"))

    assert columns == {
        "id",
        "auth_issuer",
        "auth_subject",
        "email",
        "display_name",
        "created_at",
        "updated_at",
    }
    assert any(
        constraint["name"] == "uq_app_user_identity" for constraint in constraints
    )
