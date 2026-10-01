---
name: production-infra-rollouts
description: "Use when deploying production apps. Verify DNS and runtime."
metadata:
  hermes:
    tags: [production, infrastructure, rollout, dns, route53, docker, swarm, traefik, security]
---

# Production infrastructure rollouts

Use for introducing an application to an existing production environment when the work crosses resource boundaries (for example domain/DNS, reverse proxy, and Docker Swarm). For an app-only Swarm/Traefik deployment, the narrower `swarm-traefik-app-deploy` skill may also apply; preserve its live-stack conventions.

## Procedure

1. Read the requested rollout plan, the project's write-zone/update rules, and the deployment target. Separate requested end state from the proposed commands and artifacts; do not assume the plan was verified.
2. Collect a read-only baseline from the exact target contexts: cloud identity and account, hosted zone and exact DNS records, public DNS and origin address, host OS/resources, Swarm manager/nodes/networks/stacks, Traefik arguments and working app labels, relevant service mounts and persisted data. Verify the AWS profile instead of assuming `default` and resolve the hostnames through authoritative DNS.
3. Redact secrets before displaying diagnostic output. Do not dump complete container/service environment variables, credentials, token files, `.env`, or authentication stores; request only non-secret fields or filter secrets before output.
4. Test the proposed architecture against actual app requirements before writing deploy artifacts: process entry point, external runtimes/CLI auth, writable paths, ports/WebSockets, UI/control of a local desktop, data persistence, licensing, trust boundary, and authentication of every externally reachable route.
5. Keep changes inside the repository's durable user-owned extension area. Back up modified user settings first. Create reproducible artifacts with secrets outside the repository/build context; validate syntax/build independently before touching the live Swarm. Distinguish static review, syntax validation, build, deployment, public reachability, and authenticated end-to-end tests as separate evidence levels.
6. Before publishing a hostname, prove that the exact target resolves to the intended origin and that an adequate authentication/perimeter control is already enforced. Prefer `CREATE` over `UPSERT` for intended-new DNS records, then re-read exact records after propagation; inspect and reconcile conflicts before changing existing records.
7. Apply one bounded change at a time. Verify service task health, app logs, routing, certificate, auth controls, and a representative user workflow after each rollout. Keep application data separate from the service lifecycle; do not remove volumes or make a destructive rollback without explicit confirmation.
8. Report evidence and limits accurately: current baseline, files/backups, exact changes made, checks actually run, remaining blockers, security risks, and a concrete next action. Never describe an unbuilt or undeployed template as deployed/ready.

See `references/production-preflight.md` for the read-only evidence checklist and validation order. See `references/agent-app-boundaries.md` when the target is an AI agent, desktop automation app, or editor with elevated in-container privileges.