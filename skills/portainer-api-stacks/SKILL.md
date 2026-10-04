---
name: portainer-api-stacks
description: "Use when deploying Swarm stacks via Portainer API."
version: 1.0.0
author: Wittemberg, Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [docker, swarm, portainer, traefik, devops, deploy]
    related_skills: [swarm-traefik-app-deploy, docker-ops]
---

# Portainer API Swarm Stacks

## When to Use
Use when deploying, automating, or adopting Docker Swarm stacks through Portainer so the compose files remain fully editable and manageable in the Portainer web UI.

## Workflow: Deploying Editable Swarm Stacks

### 1. Authenticate and Validate Portainer API

Verify the Portainer token before initiating actions. Read the API key from a secure file or environment variable; never pass cleartext tokens directly in command arguments.

```bash
PT_TOKEN=$(tr -d '\r\n' < /root/token.io)
curl -s -o /dev/null -w '%{http_code}\n' -H "X-API-Key: $PT_TOKEN" https://<portainer-domain>/api/status
```

### 2. Discover Swarm Cluster ID and Endpoint

Extract the Swarm Cluster ID directly from the Swarm manager:

```bash
SWARM_ID=$(docker info --format '{{.Swarm.Cluster.ID}}')
```

Identify the target endpoint ID (typically `1` for the primary local Swarm environment):

```bash
curl -s -H "X-API-Key: $PT_TOKEN" https://<portainer-domain>/api/endpoints | jq -r '.[] | [.Id, .Name, .Type] | @tsv'
```

### 3. Deploy Stack via String Endpoint

Send the Compose definition to `/api/stacks/create/swarm/string?endpointId=<id>`:

```python
import json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

with open('/root/token.io') as f:
    token = f.read().strip()

with open('/path/to/stack.yml') as f:
    stack_content = f.read()

endpoint_id = 1
url = f'https://<portainer-domain>/api/stacks/create/swarm/string?endpointId={endpoint_id}'

payload = json.dumps({
    'name': 'stack-name',
    'stackFileContent': stack_content,
    'swarmID': swarm_id,
    'env': [{'name': 'VAR_NAME', 'value': 'value'}]
}).encode('utf-8')

req = urllib.request.Request(url, data=payload, headers={
    'X-API-Key': token,
    'Content-Type': 'application/json'
}, method='POST')

with urllib.request.urlopen(req, context=ctx) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print(f"Stack created with ID: {result.get('Id')}")
```

### 4. Update Existing Stack via API

To update an active Swarm stack while preserving Portainer's editable state and compose path (`/data/compose/<id>`):

1. Fetch current stack details and file content:
   - `GET /api/stacks/{id}` returns current `Env` array.
   - `GET /api/stacks/{id}/file` returns `StackFileContent`.
2. Back up the existing compose file, stack metadata, active image tag/digest, and persistent configuration before a production image change. Confirm the rollback image is present or preserve it as an image archive; a Docker tag alone is not a rollback if the local image has already been pruned.
3. Validate the new image separately (build, isolated startup/health check, application-specific smoke tests, and in-image `npm audit --omit=dev` when applicable). Then submit updated compose content through Portainer's API, retaining `Env` and using `prune:false` unless removing services is explicitly intended:

```python
payload = json.dumps({
    'stackFileContent': updated_compose_yaml,
    'env': stack_details.get('Env') or [],
    'prune': False,
    'pullImage': False
}).encode('utf-8')
```

4. Configure a reversible Swarm rollout in the Compose definition (for a single stateful replica, `order: start-first`, a bounded `monitor`, and `failure_action: rollback` when compatible with the app's resource constraints). With Swarm `update_config.monitor`, the Docker CLI/stack update may wait for the entire monitor window even when the new task is already healthy; inspect task state, health, logs, and public endpoints before interpreting the wait as a hang. After convergence, confirm Portainer's stack state, service image, and health independently.
5. If the renderer cannot reliably reconcile `Status: 3` to final state, poll Portainer, Swarm task state and the service health rather than starting a second stack or issuing blind repeated deployments.


### 5. Verify Stack Portainer Management State

Confirm that Portainer has created the stack file under `/data/compose/<id>` and reports the stack as editable:

```bash
curl -s -H "X-API-Key: $PT_TOKEN" https://<portainer-domain>/api/stacks | jq -r '.[] | [.Id, .Name, .Status, (.ProjectPath != null and .ProjectPath != "")] | @tsv'
```

## Pitfalls

- **Stacks paradas:** uma stack pode continuar cadastrada no Portainer com `Status: 2`, embora esteja ausente de `docker stack ls`. Consulte `/api/stacks` antes de criar outra com o mesmo nome. Após atualizar via PUT, `Status: 3` pode indicar implantação em andamento; releia até confirmar `Status: 1` e valide serviço/healthcheck. Se continuar parada, use `POST /api/stacks/{id}/start?endpointId=<id>`.
- **Imagem local removida:** não prometa rollback para uma tag antiga sem confirmar que a imagem ainda existe ou pode ser obtida do registry. Preserve o compose anterior e explicite quando o rollback disponível é retornar ao estado parado, sem remover dados.

- **Updating via PUT:** Always preserve the current `Env` array; omit it only when intentionally clearing stack variables. Do not set `prune:true` by default: it can remove services omitted from the submitted Compose. Use `prune:false` for routine image/label updates and enable pruning only after reviewing the services that would be removed.
- **Mutable config bind mounts:** Avoid `:ro` on single-file bind mounts (e.g. `/data/app/.env:/app/.env:ro`) when the web UI or application needs to save credentials or runtime settings. Ensure host permissions permit writes by the container user (e.g. `chmod 666` or ownership matching `1000:1000`).

- **Mandatory `swarmID`:** `POST /api/stacks/create/swarm/string` fails with `400 Bad Request` (`Invalid Swarm ID`) if `swarmID` is missing from the request payload. Always query and supply `docker info --format '{{.Swarm.Cluster.ID}}'`.
- **External vs Portainer stacks:** Stacks created via CLI `docker stack deploy` show up in Portainer as external read-only stacks without an editable compose file. Deploy through Portainer API to persist `/data/compose/<id>`.
- **Registry credentials:** Portainer Swarm deployments do not inherit host Docker CLI login credentials. Ensure registries are registered in Portainer (`/api/registries`) or images are pre-pulled on the manager before triggering the stack creation.
- **Image pre-pull on single-node Swarm:** For large images (e.g. desktop/browser GUI containers like Obsidian/WebRTC), trigger a direct `docker pull <image>` before deploying to prevent task timeout or preparing delays in Swarm service convergence.
- **Runtime binaries and package updates in Swarm services:** Attempting ad-hoc `docker exec <container> apt-get ...` inside containers running under unprivileged users (`USER node`, `USER 1000`) fails with `Permission denied`. Always define system dependencies (`python3-psutil`, `pciutils`, symlinks `/usr/bin/python -> /usr/bin/python3`) in the service `Dockerfile`, build the image, and trigger a rolling update with `docker service update --image <tag> --force <service>`.
