"""Operational CLI.

    python -m app.cli create-user --email admin@bridge.example --role admin --display-name "Admin"

The password is read interactively (or from BRIDGE_NEW_USER_PASSWORD for automation) and is never
accepted as a command-line argument, which would leak it into shell history and process lists.
This is the supported way to create the first administrator.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from app.core.config import get_settings
from app.db.session import Database
from app.models.user import Role
from app.services import audit
from app.services.users import EmailAlreadyRegisteredError, register_local_user


def _create_user(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.auth_provider != "local":
        print("create-user only applies to AUTH_PROVIDER=local.", file=sys.stderr)
        return 2
    password = os.environ.get("BRIDGE_NEW_USER_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < 10:
        print("Password must be at least 10 characters.", file=sys.stderr)
        return 2
    db = Database(settings.database_url)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="Create a local user with a given role")
    create.add_argument("--email", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--role", choices=[r.value for r in Role], default=Role.STUDENT.value)
    create.set_defaults(func=_create_user)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
