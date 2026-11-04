# Isolated deployment on the existing NILES host

The Control GRC service must be deployed in its own directory, e.g. /opt/control-grc, without changing any NILES files, containers, networks or database.

1. Check host capacity, existing ports, reverse-proxy rules, backups and Docker permissions before deployment.
2. Clone this repository into /opt/control-grc.
3. Copy .env.example to .env and replace CONTROL_API_KEY with a securely generated random secret. Keep .env out of Git.
4. Run `docker compose -p control-grc up -d --build` from this directory.
5. Verify `docker compose -p control-grc ps` and `curl -H "X-API-Key: YOUR_SECRET" http://127.0.0.1:18080/api/health`.
6. Keep port 18080 bound to loopback only. Expose externally only through a separately configured HTTPS reverse proxy with authentication and access controls.
7. Back up the `control-grc_control_data` named volume using SQLite's online backup API; verify restore independently.

**Caution:** The current prototype uses a shared API key for both UI and API. It is NOT appropriate to expose it publicly or use it with sensitive evidence until a separate authenticated UI, authorization, and file storage are implemented. No production deployment is authorized by these instructions.

Stop only this app: `docker compose -p control-grc down` (never use `-v` unless deliberately destroying its data). Do not run broad Docker cleanup commands on the NILES host.
