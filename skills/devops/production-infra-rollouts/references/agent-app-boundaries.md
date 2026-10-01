# AI agents, desktop automation, and privileged web applications

Use when deploying a local AI/automation project to a server, or exposing a web UI that can reach credentials, terminals, or a user's files.

## Check execution-boundary compatibility

Before containerizing, trace a user task from HTTP route through the agent/provider subprocess and tool execution to the actual operating system. Determine where the LLM CLI/auth state lives, what user owns it, what machine its commands control, and which paths the app can read/write. A web cockpit in a remote Linux container does not inherit the local Hermes session, Windows desktop, Windows credentials, configured tools, skills, or permissions merely because both products are called agents.

If the app depends on local mouse/keyboard/UI automation or Office/browser profiles, choose explicitly between:

- running the agent on the same OS session it is intended to control;
- designing a narrowly scoped, outbound-authenticated remote worker/bridge on the user's PC; or
- removing the local-computer-use feature from the remote product.

Do not mount the Docker socket or host filesystem as a shortcut for desktop control; this converts a compromised web app into host-level control.

## Treat agent dependencies and prompts as security boundaries

Inventory required provider CLIs, license/auth requirements, subcommands, environment variables, OAuth caches, MCP servers and working directories. Do not copy a personal `auth.json`, provider CLI state, API key, or `.env` into the image or repository. Provision credentials out of band using the platform's secret facility, with least privilege and a documented rotation path. Test startup with secrets mounted only through the intended file mechanism; missing credentials must fail closed rather than quietly select a weaker or unauthenticated path.

Inspect all routes, not just state-changing POSTs. Public GET endpoints, static HTML, SSE and health/config/status routes may disclose account data, tokens, paths, model configuration or initiate expensive work. A localhost-only CORS/token guard is not internet authentication: bind behavior, same-origin assumptions, session token lifetime, CSRF rules, API access control and health endpoints must be reviewed explicitly before proxy exposure.

## GUI applications in containers

A browser-accessible Linux desktop container is a remote desktop, not a safe headless editor. If its embedded terminal can run `sudo` without a password, anyone who reaches the UI effectively has root in that container and a foothold on its attached network. Require strong independent authentication, private/VPN or properly authenticated reverse-proxy ingress, TLS, network segmentation and rate limits before exposing it.

When the same vault/editor is used on more than one host, choose a single writer or define synchronization and conflict behavior before concurrent use. Back up the durable vault/config separately from the container lifecycle. Validate WebSocket and desktop-session traffic through the actual proxy.

## State the proof boundary

Report separately whether you only read the code, validated a config file, built an image, deployed a task, reached the proxy, passed authentication, and completed a real workflow. A healthy container or HTTP 200 alone does not prove a secure, usable agent.