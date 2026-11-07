from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import settings


# Change only the database name in memory.
test_url = make_url(settings.database_url).set(
    database="ledgerline_test_db"
)

settings.database_url = test_url.render_as_string(
    hide_password=False
)

# Apply existing migrations to the test database.
config = Config("alembic.ini")
command.upgrade(config, "head")

print("Test database migrations completed successfully.")