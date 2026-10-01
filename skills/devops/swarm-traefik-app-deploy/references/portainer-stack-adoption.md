# Reading and adopting stacks in Portainer (EE) via API

Use when a deployed stack shows up in Portainer with limited control, or before
deciding whether to deploy a new app with `docker stack deploy` or through
Portainer.

## Authenticating

The API key goes in `X-API-Key`. Read it into a variable — never echo it, never
paste it into a command line that gets reported back.

```bash
PT_TOKEN=$(tr -d '\r\n' < /root/token.io)
PT=https://wit-portainer.awecloudsolution.com
curl -s -o /dev/null -w '%{http_code}\n' -H "X-API-Key: $PT_TOKEN" "$PT/api/status"
```

`/api/status` returning 200 validates the token before anything else is attempted.

## What Portainer thinks exists

```bash
curl -s -H "X-API-Key: $PT_TOKEN" "$PT/api/endpoints" | python3 -c '
import sys,json
for e in json.load(sys.stdin): print(e["Id"], e["Name"], e["Type"], e.get("Status"))'

curl -s -H "X-API-Key: $PT_TOKEN" "$PT/api/stacks" | python3 -c '
import sys,json
for s in json.load(sys.stdin):
    print(s["Id"], s["Name"], "type", s["Type"], "path", s.get("ProjectPath"))'
```

Diff that list against `docker stack ls`. Anything present in Swarm but absent
from `/api/stacks` is the limited/external case: Portainer has no compose file
for it, so it can render the services and nothing more.

Fetch a working stack's compose to copy its conventions before writing a new one:

```bash
curl -s -H "X-API-Key: $PT_TOKEN" "$PT/api/stacks/<id>/file" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["StackFileContent"])'
```

## Check the registry credential before recreating

A stack recreated through Portainer pulls with Portainer's credentials, not the
manager's `docker login`. If the image is private, confirm the registry is
registered and authenticated first, or the new stack deploys and then fails to
pull.

```bash
curl -s -H "X-API-Key: $PT_TOKEN" "$PT/api/registries" | python3 -c '
import sys,json
for r in json.load(sys.stdin):
    print(r["Id"], r["Name"], r.get("URL"), "auth=", r.get("Authentication"))'
```

## Adoption order

1. Back up the live spec: `docker service inspect <svc> > backup/service-spec.json`, plus the stack file.
2. Confirm external Docker secrets already exist — they survive the stack being removed and recreated, and must be declared `external: true` in the new compose.
3. Recreate through Portainer (UI or `POST /api/stacks`), reusing the compose that is already in git.
4. Verify from the public hostname, not from the host.

Prefer doing this while the app has no production data. The window between
removing the Swarm stack and the Portainer one converging is real downtime.
