---
name: swarm-traefik-app-deploy
description: "Deploy an app to the VPS Docker Swarm + Traefik stack. Use when publishing, updating, rolling back or exposing a service (with or without VPN) on the production Swarm cluster behind Traefik."
version: 1.0.0
metadata:
  hermes:
    tags: [docker, swarm, traefik, ghcr, deploy, vps, letsencrypt, secrets]
---

# Deploying an app to the VPS Swarm + Traefik stack

Use when shipping a containerized app to the user's VPS: Docker Swarm, one shared Traefik, images on GHCR, hostnames under `awecloudsolution.com`.

The VPS runs a shared Docker **Swarm** with a single Traefik fronting every app. New apps join that stack; they do not bring their own reverse proxy, their own TLS, or their own `docker compose up`.

Recon first, always. The live stack is the spec — never write Traefik labels from memory, because a label shape that is correct for Traefik v2 or for plain Compose silently fails to route here.

## 1. Recon before writing anything

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
docker network ls --filter driver=overlay --format '{{.Name}}'
docker service inspect traefik_traefik \
  --format '{{range .Spec.TaskTemplate.ContainerSpec.Args}}{{println .}}{{end}}'
docker service inspect <existing_app> --format '{{json .Spec.Labels}}' | python3 -m json.tool
```

The Traefik args give the real entrypoint and certresolver names; the labels of an already-working service are the canonical template to copy. Check `gh auth status` in this same pass — pushing to GHCR and creating the repo both need it, and discovering it is missing after building the image wastes the build.

Confirm DNS resolves to the VPS **before** relying on Let's Encrypt: HTTP-01 fails closed if the hostname does not already point at the host.

```bash
dig +short <host>.awecloudsolution.com A
curl -s -4 ifconfig.me
```

## 2. Environment facts (verify, don't assume)

| Item | Value observed |
|---|---|
| Orchestrator | Docker Swarm (`docker stack deploy`), not plain Compose |
| Overlay network | `interna`, declared `external: true` |
| Entrypoints | `web` (80, auto-redirects) and `websecure` (443) |
| Cert resolver | `letsencryptresolver`, HTTP-01 challenge |
| Image naming | `ghcr.io/wittemberg/<full-domain>:<tag>` |
| Also running | Portainer EE, Postgres, pgAdmin — reuse the Postgres instead of adding one |

Use `traefik.swarm.network`, not `traefik.docker.network`. Traefik v3's Swarm provider reads the `swarm`-prefixed key; the `docker` one is ignored and the router resolves to the wrong IP or none.

## 3. Stack file rules

- Labels go under `deploy.labels`, not top-level `labels`. In Swarm, top-level labels land on the container and Traefik's swarm provider never sees them.
- Deploy with `--with-registry-auth` so the workers can pull a private GHCR image.
- Pin `replicas: 1` whenever the app holds state in process memory (rate-limit counters, login backoff, caches). Scaling silently multiplies the effective limit by the replica count — write the reason in a comment next to it.
- Add `X-Robots-Tag: noindex, nofollow` for anything sensitive. A public hostname gets crawled.

## 4. Secrets

Inject secrets as Docker secrets read through a `*_FILE` env var, never as plain `environment:` values — `docker service inspect` prints the environment block in cleartext to anyone who can reach the socket, including Portainer users.

```yaml
environment:
  APP_MASTER_KEY_FILE: /run/secrets/app_master_key
secrets:
  - app_master_key
```

```bash
openssl rand -hex 32 | docker secret create app_master_key -
```

Implement the `_FILE` reader in **every module that loads the secret**, not only the app entrypoint. A helper that lives in `app.py` while the crypto/DB layer still reads the bare environment variable passes all local tests — where the plain variable is exported — and then kills the container on first deploy with "secret missing". Resolve order: explicit argument, then `NAME_FILE`, then `NAME`; add a regression test that sets only `NAME_FILE`.

Failing hard on a missing secret is correct behaviour, not a bug to soften. Never fall back to an empty or generated key so the process can boot.

## 5. CI to GHCR

GitHub Actions with `permissions: packages: write` and `secrets.GITHUB_TOKEN` is enough to push to `ghcr.io/wittemberg/*` — no PAT needed in the workflow. Gate the build job on tests passing, and tag with `type=ref,event=branch` plus `type=sha` so a stack can be pinned to an exact commit.

Dockerfile: multi-stage with `uv` for Python, and a non-root `USER` in the final stage.

`uv pip install --system` fails on `ubuntu-latest`: the runner's interpreter is externally managed (PEP 668). Use a venv and call its binaries explicitly.

```yaml
- run: |
    uv venv
    uv pip install -e ".[dev]"
- run: .venv/bin/pytest -q
```

Give the test job the real datastore as a `services:` container when any test asserts isolation or persistence. Tests that skip without a DSN report green while proving nothing — a skipped multi-tenant isolation test is indistinguishable from a passing one in the CI summary.

`gh repo edit --visibility` rejects the flag in some builds; `gh api -X PATCH repos/<owner>/<repo> -f private=true` changes visibility reliably. Confirm a repo's visibility before the first push when it will hold infrastructure internals.

## 6. Deploying and reading the failure

A private GHCR package needs the manager logged in *before* the stack deploy; `--with-registry-auth` forwards the existing credential, it does not create one.

```bash
gh auth token | docker login ghcr.io -u <user> --password-stdin
docker stack deploy -c deploy/stack.yml --with-registry-auth <stack>
```

`docker service ls` showing `0/1` carries no diagnosis. Go straight to the task list and the logs — the two answer different questions:

```bash
docker service ps <stack>_<svc> --no-trunc --format 'table {{.CurrentState}}\t{{.Error}}'
docker service logs <stack>_<svc> 2>&1 | tail -20
```

`Rejected ... unauthorized` is a registry problem (login). `Failed ... non-zero exit` is the application's own startup error, and only the logs show it. Expect to iterate here; a first deploy that comes up clean is the exception.

After it reports `1/1`, verify from the public internet rather than from the host — localhost curl proves nothing about Traefik routing or the certificate:

```bash
curl -sI https://<host>/health | head -1
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -issuer -dates
curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}\n' https://<host>/<protected-path>
```

Those checks only prove Traefik routes and TLS works. **They all pass on an app nobody can actually use.** Before reporting success, drive one real end-to-end flow — log in, create one record, read it back — and drive it against the *served HTML*: fetch the form, parse the field names and CSRF token out of the response, and post those. A smoke test that hand-builds the request body tests the route against itself and reproduces whatever assumption the route already makes.

When the flow needs a throwaway account, create it, assert, and delete it in the same script; never leave a test login on an internet-facing service.

Smoke-test auth through the **public HTTPS hostname**, not `127.0.0.1` inside the container. Production session cookies carry `Secure`, so an HTTP client on localhost silently discards them and every subsequent request fails CSRF or redirects to login — a false failure that looks exactly like a broken app.

## 7. Portainer only manages the stacks it created

A stack deployed with `docker stack deploy` shows up in Portainer as external/limited: the services are visible but the compose file cannot be edited and redeploy is greyed out. Portainer's own stacks carry a compose file under `/data/compose/<id>`; Swarm-native ones have nothing for it to edit. `traefik` and `portainer` itself are usually in this state too, which is why nobody notices until a new app lands there.

Decide the ownership up front, because the fix is to recreate the stack through Portainer. Migrate while the app still has no data — after that the recreate window costs a maintenance slot. Query state through the API before touching anything; `references/portainer-stack-adoption.md` has the endpoints and the registry check.

## 8. Removing something that "isn't used"

A plain Compose project and a Swarm stack for the same app coexist happily on this host with nearly identical names (`p3awecloudsolutioncom` the compose project vs `p3` the stack). One serves production. Never match on the name alone.

Establish, in read-only commands, all of: who actually answers the public hostname, whether the target has volumes, which ports it binds, and whether anything references it.

```bash
docker compose ls -a                      # compose projects + their config file paths
docker stack ls && docker stack services <stack>
curl -sI https://<host> | head -1         # who really serves it
docker inspect <container> --format 'Mounts: {{range .Mounts}}{{.Type}}:{{.Source}} {{end}}Networks: {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker volume ls --filter label=com.docker.compose.project=<project>
```

Copy the compose file aside before `docker compose down`, and re-verify the public hostname after. `down` removes containers and the project network but leaves the directory and its compose file, so the removal is reversible only if you know where that file was.

## 9. Exposing to the public internet

When the app holds credentials or the upstream project says "localhost only", do not just add the Traefik labels and move on. Read `references/public-exposure-without-vpn.md` — it has the Cloudflare Tunnel/Route53 constraint and the compensating-control checklist, and it records why hiding the VPS IP is not a real benefit on a shared-IP host.

Register the exception in the project's TRD: what protection the private network was providing, what replaces each piece, and the condition under which the exposure should be withdrawn (usually: once a VPN exists).

When the app is itself a credential store, the data-model and crypto rules live in the `secret-storage-design` skill — read it before designing the schema, not after.
