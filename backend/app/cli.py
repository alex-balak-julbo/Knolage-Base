import click

from .container import svc
from .seed import demo_data, ensure_templates, ensure_user


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables (prefer Alembic migrations in production) and system templates."""
        repo = svc().repo
        if hasattr(repo, "create_all"):
            repo.create_all()
        ensure_templates(repo)
        repo.commit()
        click.echo("Database initialised.")

    @app.cli.command("create-user")
    @click.argument("email")
    @click.password_option()
    @click.option("--role", default="editor", type=click.Choice(["admin", "editor", "reader"]))
    @click.option("--name", default="")
    def create_user(email, password, role, name):
        repo = svc().repo
        ensure_user(repo, email, password, role, name or email.split("@")[0])
        repo.commit()
        click.echo(f"User {email} ready.")

    @app.cli.command("seed")
    @click.option("--email", default="admin@example.com")
    @click.option("--password", default="admin1234")
    @click.option("--demo/--no-demo", default=True)
    def seed(email, password, demo):
        """Create templates, an admin user and (optionally) demo content."""
        s = svc()
        ensure_templates(s.repo)
        user = ensure_user(s.repo, email, password, "admin")
        if demo and not s.repo.list_active(user.id):
            demo_data(s.tree, user)
        s.repo.commit()
        click.echo(f"Seeded. Login: {email} / {password}")

    @app.cli.command("purge-trash")
    def purge_trash():
        """Permanently delete items trashed longer than TRASH_RETENTION_DAYS."""
        n = svc().tree.purge_expired()
        svc().repo.commit()
        click.echo(f"Purged {n} trashed item(s).")
