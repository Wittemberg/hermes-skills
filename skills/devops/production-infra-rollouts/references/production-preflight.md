# Production rollout preflight and verification

Use this checklist when a new service spans AWS DNS, a reverse proxy, and a live container scheduler. Adapt commands to the actual account and target host; do not execute create/update commands during preflight.

## Evidence-gathering order

1. **Identify the exact AWS account and profile.** Run `aws configure list-profiles`, then `aws sts get-caller-identity --profile <profile>`. Use the returned account to select the intended hosted zone; never infer that profile `default` is configured or belongs to the right account.
2. **Read exact existing DNS data.** Resolve hosted-zone ID by exact domain and list record sets for each intended hostname. Check the apex/NS records and query the zone's authoritative nameserver directly. Distinguish a resolver's cached result from current Route 53 state.
3. **Prove DNS target to origin.** Follow the proposed CNAME chain and compare the final A/AAAA answer against the intended host's actual public IP. A convenience hostname such as `traefik.example` may front another server; same domain does not mean same host.
4. **Inventory the target host and scheduler without mutating it.** Record OS, free space, Docker/server version, Swarm node role/state, stack/service list, overlay network names, and mounts for relevant services. Use narrow `docker service inspect --format` queries; never print `.Spec.TaskTemplate.ContainerSpec.Env` wholesale because environment values frequently include credentials.
5. **Discover reverse-proxy behavior from the running system.** Read proxy arguments and labels from one known working service, including provider type, network label namespace, entrypoints, TLS resolver, backend scheme/port, and auth middleware. Avoid importing labels or network names from a different Traefik version/provider.
6. **Inspect the app before designing the container.** Verify app startup requirements, authentication and CORS/CSRF model, external subprocesses, ports/WebSockets, volume/write paths, health endpoint, desktop/hardware dependencies, and licence. Check whether supposedly harmless GET/status endpoints expose state or credentials before routing the app publicly.
7. **Prepare artifacts separately from deployment.** Keep source, compose/stack, env/config, secrets, and persistent data in distinct paths. Exclude credentials, runtime state and local node_modules from the Docker build context. Validate JSON/YAML, render environment references with placeholders, and run a real Docker build before placing the image into Swarm.
8. **Choose the record action deliberately.** Use `CREATE` for an intended-new DNS record so an unexpected existing record fails closed; inspect and decide explicitly before using `UPSERT` to change an existing record. A Route 53 batch is transactional, but `UPSERT` can still silently replace a working value.
9. **Publish only after the perimeter works.** Verify authentication through the public hostname before the hostname/route becomes an open access path. Check DNS, TLS, HTTPS redirect, auth challenge, CSRF/session behavior, rate-limits and an end-to-end application workflow independently.
10. **Capture evidence and rollback.** Save pre-change record values and app/service configuration. For rollback, remove or restore only the newly introduced route/record/service after checking current references; preserve data volumes and disclose whether the rollback has been tested.

## Useful read-only command shapes

```bash
aws configure list-profiles
aws sts get-caller-identity --profile <profile>
aws route53 list-hosted-zones-by-name --dns-name <zone> --profile <profile>
aws route53 list-resource-record-sets --hosted-zone-id <zone-id> --profile <profile>
dig +short <hostname> A
dig +short <hostname> CNAME

docker info --format '{{.Swarm.LocalNodeState}} {{.Swarm.ControlAvailable}}'
docker stack ls
docker node ls --format '{{.Hostname}} {{.Status}} {{.Availability}} {{.ManagerStatus}}'
docker network ls --filter driver=overlay --format '{{.Name}}'
docker service inspect <proxy-service> --format '{{json .Spec.TaskTemplate.ContainerSpec.Args}}'
docker service inspect <known-service> --format '{{json .Spec.Labels}}'
docker service inspect <service> --format '{{json .Spec.TaskTemplate.ContainerSpec.Mounts}}'
docker system df
```

Avoid unrestricted `docker inspect`, service environment dumps, or shell tracing around commands that may carry credentials. Filter output at the source, not only after it has already been printed or captured.