"""Exercise deployment and custom-type generation against isolated databases."""

import shutil
import subprocess
from pathlib import Path

import sqlalchemy as sa
from alembic.script import ScriptDirectory

from authentic_dynamics import create_app
from authentic_dynamics.extensions import db
from authentic_dynamics.hub.models import UTCDateTime


def test_restore_migrations_removes_server_only_heads(tmp_path):
    root = Path(__file__).resolve().parents[1]
    migrations = tmp_path / "migrations"
    shutil.copytree(root / "migrations", migrations, ignore=shutil.ignore_patterns("__pycache__"))
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(root / "scripts/restore_migrations.sh", scripts)

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("add", "migrations", "scripts")
    git("-c", "user.name=Migration Test", "-c", "user.email=migrations@example.test",
        "-c", "commit.gpgsign=false", "commit", "-m", "Deployment fixture")
    expected_heads = ScriptDirectory(str(migrations)).get_heads()
    assert len(expected_heads) == 1
    (migrations / "versions/server_only.py").write_text(
        "revision = 'server_only'\ndown_revision = None\n"
    )
    assert len(ScriptDirectory(str(migrations)).get_heads()) == 2
    (migrations / "env.py").write_text("# Locally regenerated environment\n")

    result = subprocess.run(
        ["bash", str(scripts / "restore_migrations.sh")],
        cwd=migrations, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not (migrations / "versions/server_only.py").exists()
    assert (migrations / "env.py").read_text() == (root / "migrations/env.py").read_text()
    assert ScriptDirectory(str(migrations)).get_heads() == expected_heads


def test_fresh_upgrade_and_generated_utc_migration(tmp_path):
    migrations = tmp_path / "migrations"
    shutil.copytree(
        Path(__file__).resolve().parents[1] / "migrations",
        migrations,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "migration-test-only",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'fresh.db'}",
        "HUB_PRIVATE_DIR": str(tmp_path / "private"),
    })
    runner = app.test_cli_runner()

    def run(*args):
        result = runner.invoke(args=["db", *args, "--directory", str(migrations)])
        assert result.exit_code == 0, result.output
        return result

    run("upgrade")
    run("upgrade")
    run("check")
    with app.app_context():
        assert set(sa.inspect(db.engine).get_table_names()) == set(db.metadata.tables) | {
            "alembic_version"
        }

        table = sa.Table(
            "migration_utc_probe", db.metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", UTCDateTime(), nullable=False),
        )
        try:
            existing = set((migrations / "versions").glob("*.py"))
            run("migrate", "-m", "UTC rendering regression")
            generated, = set((migrations / "versions").glob("*.py")) - existing
            source = generated.read_text()
            assert "sa.DateTime()" in source
            assert "authentic_dynamics" not in source
            assert "UTCDateTime" not in source
            run("upgrade")
            run("check")
            assert "migration_utc_probe" in sa.inspect(db.engine).get_table_names()
        finally:
            db.metadata.remove(table)
