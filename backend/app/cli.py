"""Operational CLI.

    python -m app.cli setup               # migrate + sync scenarios (+ demo data in development)
    python -m app.cli sync-scenarios      # load/refresh scenarios from ../scenarios
    python -m app.cli seed-demo           # fictional demo accounts, course and sample data
    python -m app.cli create-user --email a@b.org --display-name "Admin" --role admin

Passwords are read interactively (or from BRIDGE_NEW_USER_PASSWORD) and never accepted as
command-line arguments, which would leak them into shell history and process lists.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.session import Database
from app.models.user import Role
from app.services import audit
from app.services.users import EmailAlreadyRegisteredError, register_local_user

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _db() -> Database:
    return Database(get_settings().database_url)


def _create_user(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.auth_provider != "local":
        print("create-user only applies to AUTH_PROVIDER=local.", file=sys.stderr)
        return 2
    password = os.environ.get("BRIDGE_NEW_USER_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < 10:
        print("Password must be at least 10 characters.", file=sys.stderr)
        return 2
    db = _db()
    with db.session_factory() as session:
        try:
            user = register_local_user(
                session, email=args.email, password=password, display_name=args.display_name
            )
        except EmailAlreadyRegisteredError:
            print("A user with that email already exists.", file=sys.stderr)
            return 1
        user.role = Role(args.role).value
        audit.record(
            session,
            action="cli.user.created",
            target_type="user",
            target_id=str(user.id),
            details={"role": user.role},
        )
        session.commit()
        print(f"Created {user.role} {user.email} ({user.id})")
    db.dispose()
    return 0


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


def _sync(_: argparse.Namespace | None = None) -> int:
    from app.services.scenarios import sync_from_files

    db = _db()
    with db.session_factory() as session:
        for line in sync_from_files(session):
            print("  scenario", line)
        session.commit()
    db.dispose()
    return 0


def _seed_demo(_: argparse.Namespace | None = None) -> int:
    settings = get_settings()
    if settings.is_production or not settings.allow_demo_seed:
        print("Demo data is disabled in this environment.", file=sys.stderr)
        return 2
    from app.services.demo import seed

    db = _db()
    with db.session_factory() as session:
        for line in seed(session, settings):
            print("  demo", line)
        session.commit()
    db.dispose()
    return 0


def _setup(args: argparse.Namespace) -> int:
    print("Applying database migrations...")
    _migrate()
    print("Syncing scenarios...")
    _sync()
    settings = get_settings()
    if not args.no_demo and not settings.is_production and settings.allow_demo_seed:
        print("Seeding demo data...")
        _seed_demo()
    print("Setup complete.")
    return 0


def _check(_: argparse.Namespace) -> int:
    from app.simulation.loader import DEFAULT_SCENARIO_DIR, load_file

    failures = 0
    for path in sorted(DEFAULT_SCENARIO_DIR.glob("*/*.yaml")):
        name = f"{path.parent.name}/{path.name}"
        try:
            d = load_file(path)
        except Exception as exc:  # report every broken file, not just the first
            failures += 1
            print(f"FAIL {name}: {exc}")
            continue
        print(f"OK   {name}: {d.title} ({len(d.actions)} actions, {len(d.events)} events)")
    return 1 if failures else 0


def _evaluation(args: argparse.Namespace) -> int:
    import json
    import uuid

    from app.services import evaluation

    db = _db()
    with db.session_factory() as session:
        if args.session:
            data = evaluation.consistency(
                session, get_settings(), uuid.UUID(args.session), args.runs
            )
        else:
            data = evaluation.report(session)
    db.dispose()
    print(json.dumps(data, indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="Create a local user with a given role")
    create.add_argument("--email", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--role", choices=[r.value for r in Role], default=Role.STUDENT.value)
    create.set_defaults(func=_create_user)
    sub.add_parser("sync-scenarios", help="Load scenario files into the database").set_defaults(
        func=_sync
    )
    sub.add_parser("seed-demo", help="Create fictional demo accounts and data").set_defaults(
        func=_seed_demo
    )
    sub.add_parser("check-scenarios", help="Validate all scenario files").set_defaults(func=_check)
    ev = sub.add_parser("evaluation-report", help="Evaluation metrics from recorded data (JSON)")
    ev.add_argument("--session", help="Session id: measure assessment consistency by re-running it")
    ev.add_argument("--runs", type=int, default=3)
    ev.set_defaults(func=_evaluation)
    setup = sub.add_parser("setup", help="Migrate, sync scenarios and seed demo data")
    setup.add_argument("--no-demo", action="store_true")
    setup.set_defaults(func=_setup)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
