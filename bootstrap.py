"""Provision a temporary initial login credential without exposing it in GitHub sources/logs.

Run only inside the Control GRC container. Redirect its stdout to a root-only
file on the host, then delete that file after the operator changes password.
"""
import os
import secrets
import sys

import app
import identity


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "create":
        command, username = "create", os.environ.get("CONTROL_UI_USER", "grcadmin")
    elif len(sys.argv) in (3, 4) and sys.argv[1] in ("create", "reset"):
        command, username = sys.argv[1:3]
    else:
        raise SystemExit("Usage: python bootstrap.py create [USERNAME] | reset USERNAME --force")
    if not username or not username.isascii() or not all(c.isalnum() or c in "_.-" for c in username):
        raise SystemExit("Invalid account name")
    if command == "reset" and (len(sys.argv) != 4 or sys.argv[3] != "--force"):
        raise SystemExit("Reset requires explicit --force")
    if command == "create" and len(sys.argv) not in (2, 3):
        raise SystemExit("Invalid create arguments")
    app.initialize()
    with app.connect() as db:
        exists = db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if exists and command == "create":
            print("ACCOUNT_ALREADY_EXISTS")
            return
        password = secrets.token_urlsafe(18)
        changed = identity.provision(db, username, password, reset=command == "reset")
        if not changed:
            raise RuntimeError("Account provisioning did not complete")
        db.commit()
    # Do not log this output in CI. Redirect to a private root-owned host file.
    print("Kullanici adi:", username)
    print("Gecici parola:", password)
    print("Ilk giriste yeni bir parola belirlemeniz gerekecektir.")


if __name__ == "__main__":
    main()
