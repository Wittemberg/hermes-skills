---
name: generic-openai-compatible-cli-providers
description: "Use when configuring AI CLIs through a generic API gateway."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [CLI, OpenAI-compatible, Anthropic, Google, API gateway, provider]
    related_skills: [hermes-agent, codex, claude-code]
---

# Generic API Gateway For AI CLIs

Use this skill when configuring Codex, Claude Code, Antigravity/agy, or another standalone AI CLI against a user-managed OpenAI-compatible gateway.

## Procedure

1. Inspect the installed CLI before changing files:
   ```bash
   command -v <cli>
   <cli> --version
   <cli> --help
   ```
   Look for its supported protocol, base-URL variables, profile/config mechanism, and model allowlist.

2. Read the gateway registration from the active Hermes profile without printing secrets. Confirm the base URL and whether the key environment variable is present.

3. Probe the exact protocol endpoint with the registered key, never relying on a successful website response. For OpenAI-compatible gateways test `/models` and the relevant generation route; for Anthropic-compatible clients test `/messages` with `x-api-key` and `anthropic-version`; for Google clients test the exact Google protocol and model route. Redact the key from every output.

4. Test a model returned by the gateway catalog. Do not assume a model name from another provider is available. A successful `/models` call followed by a minimal generation request is the acceptance criterion.

5. Keep standalone CLI profiles separate from existing OAuth or subscription logins. Use a named profile, wrapper, or environment file so the user can switch explicitly and roll back without destroying the current authentication. For a deliberate global switch, back up the existing files first and document the rollback paths.

6. For Hermes `custom_providers`, preserve the API suffix required by the gateway. A dashboard root may be reachable while the API only works at `/v1`; validate the exact URL before saving it.

7. For Codex CLI versions with `model_providers`, back up `~/.codex/config.toml` and define a named provider with `base_url`, `env_key`, `wire_api = "responses"`, and `requires_openai_auth = false`; use the gateway's exact model ID. Do not use the legacy `wire_api = "chat"` value when the installed version rejects it.

8. Prefer a dedicated Codex profile when the default provider remains effective as `openai` or a managed configuration overrides `model_provider`. Write `~/.codex/<profile>.config.toml` with the model, `model_provider`, and provider block, then invoke `codex --profile <profile> ...`; confirm the startup banner says `provider: <profile-id>` before declaring success.

9. For Claude Code, set `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` through a protected environment file or shell profile, but first verify that the CLI's local model catalog accepts the selected model. A valid `/v1/messages` response does not bypass a client-side unknown-model check.

10. After writing a profile, run the CLI itself with a minimal prompt and a bounded timeout. A raw HTTP 200 is insufficient: the CLI must parse the response and complete a request. For Codex, test both the explicit profile invocation and the startup banner; `codex exec` without `--profile` can silently use the default OpenAI provider.

11. Report the exact tested CLI, endpoint family, model, effective provider, and whether the CLI-level test passed. Do not claim a provider switch until the running CLI confirms it.

## Protocol Decision Table

| Client | Verify first | Common configuration path |
|---|---|---|
| Codex CLI | OpenAI Responses (`/v1/responses`) and/or its documented provider config | `~/.codex/config.toml`, profile, or supported environment variables |
| Claude Code | Anthropic Messages (`/v1/messages`) with `x-api-key` | `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, or documented settings |
| Google/Antigravity CLI | Google-native route or its own gateway configuration | Inspect `--help`, config, and model catalog; do not infer OpenAI compatibility |

## Pitfalls

- Treat `HTTP 200` from the gateway root or `/models` as connectivity only; an HTML dashboard or a catalog response does not prove the generation protocol works.
- Preserve `/v1` when the gateway routes API traffic there; a root URL may serve the web dashboard and still return HTTP 200 while API calls fail.
- Test both endpoint path and authentication header because OpenAI uses `Authorization: Bearer`, while Anthropic-compatible endpoints commonly use `x-api-key`; a working one does not prove the other.
- Keep provider-specific keys separate when the gateway issues keys by model group; a general key can authenticate successfully while a provider-specific key is required for the requested model family.
- Treat `model_not_found` or `No available channel` after successful authentication as a routing/catalog problem, not as proof that the key is invalid; query the gateway's model catalog with that exact key and use one of its returned IDs.
- Do not claim Claude Code is configured merely because `/v1/messages` works; Claude Code may reject a model locally before making the HTTP request, so the installed CLI must pass its own model validation and generate a response.
- Use a model actually returned by the gateway catalog; a valid key can still produce `model_not_found` for a model group unavailable to that key.
- Do not claim a generic provider is supported by a standalone CLI just because Hermes supports it; each CLI may hard-code protocol, model, or endpoint behavior.
- If a Codex config file visibly contains `model_provider = "<custom>"` but the startup banner and doctor still report `provider: openai`, inspect managed or invocation-level configuration and switch to a named profile; file presence alone does not prove the effective provider.
- Never place an API key in a command line, transcript, skill file, or shell history; resolve it through an environment variable, vault, or protected file.

## Reusable probe

The supporting script `scripts/probe-openai-anthropic.py` performs redacted `/models`, OpenAI Responses, and Anthropic Messages checks against a configured base URL. Run it only with the key supplied through the environment.
