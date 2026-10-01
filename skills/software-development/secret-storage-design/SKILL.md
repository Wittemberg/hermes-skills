---
name: secret-storage-design
description: "Design vaults and multi-tenant credential stores safely."
version: 1.0.0
metadata:
  hermes:
    tags: [security, cryptography, multi-tenant, vault, credentials, aes-gcm, zero-knowledge]
---

# Designing a service that stores secrets

Use when building or reviewing anything that holds credentials belonging to someone else: an equipment vault, a password manager, a token store, a multi-tenant secret API. The rules here are about the data model and the crypto boundary, not about deployment — for shipping it, see `swarm-traefik-app-deploy`.

## Step 0 — settle the trust model before writing code

Ask one question first: **does the server need to read the secret on its own, with no human present?**

- *Yes* (an agent must SSH into a router at 3am) → server-side encryption. The server can decrypt; accept that and defend the key.
- *No* (a human always initiates) → zero-knowledge. Derive the key in the browser, send the server an opaque blob.

These are mutually exclusive under one key. When a product needs both, build **two vaults with different guarantees in the same app** — never average them into one, which silently drags the human-only data down to the machine-readable tier. State the consequence to the user up front: a zero-knowledge vault has no password recovery, ever.

## Step 1 — key hierarchy

Never encrypt directly with the master key, and never store the master key beside the data.

```
MASTER_KEY (env, from a secret manager — never on disk next to the DB)
   └─ HKDF-SHA256(salt = tenant_id)  →  per-tenant key
        └─ AES-256-GCM(nonce 12B random, AAD = "tenant_id|item_id")
```

Each layer buys a specific property:

- **Master key outside the database** — a stolen dump or a leaked backup decrypts nothing. Shipping `encryption.key` in the same directory as the DB file is the single most common flaw in small vault projects; a `SECURITY.md` admitting "whoever reads both can decrypt" is a design defect, not a disclaimer to inherit.
- **HKDF salted with the tenant id** — compromising one tenant's derived key does not touch the others.
- **AAD binding tenant+item** — an attacker with *write* access to the DB cannot move a ciphertext row to another item or another tenant and have it decrypt; the GCM tag fails instead. Generate the item's UUID *before* sealing so it can go into the AAD, and reuse that exact id on update.

For the zero-knowledge side: PBKDF2-SHA256 at OWASP's current iteration floor (600k as of 2023+) or Argon2id, AES-GCM via WebCrypto, `extractable: false` on the derived key, fresh IV per encryption. Keep the key in a module variable only — never `localStorage`, `sessionStorage`, a cookie, or a URL — and auto-lock on inactivity and `pagehide`.

Decide explicitly **which fields stay in cleartext** in a zero-knowledge store, and say so in the TRD and to the user. Encrypting every column sounds stronger but makes the server unable to list, search, sort, or paginate, so the UI has to unlock the vault on every page load. The workable split — the one Bitwarden and 1Password use — encrypts password and notes while leaving title, URL, username, and folder as cleartext metadata. State the resulting exposure in plain terms ("a database dump reveals that you hold an account at X under login Y, but not the password") and tell the user to put anything sensitive-by-itself into the encrypted notes field. Choosing this silently is the failure: it either over-promises privacy or ships an unusable vault.

## Step 2 — tenant isolation is an authorization rule, not a query habit

- Resolve `tenant_id` **server-side from the authenticated session**, always. No route may accept a tenant from a form field, query string, header, or JSON body.
- Every data-layer method takes `tenant_id` as a parameter and puts it in the `WHERE`. An item id alone is never sufficient to fetch, update, or delete.
- A cross-tenant request must return **404, not 403** — 403 confirms the id exists and turns the endpoint into an enumeration oracle.

## Step 3 — never let a secret reach a place that logs

| Channel | Why it leaks | Do instead |
|---|---|---|
| Command argument (`sshpass -p`) | `/proc/<pid>/cmdline` is world-readable; lands in shell history | `sshpass -f /dev/stdin`, pipe via stdin |
| URL / query string | Reverse proxies log the full path | POST with the value in the body |
| `environment:` in a stack file | `docker service inspect` prints it in cleartext | Docker secret + `*_FILE` |
| Exception messages, audit rows, debug logs | Persisted and shipped to aggregators | Log the action and target id, never the value |
| `__repr__` of a wrapper object | Appears in any traceback | Override it to print a length, not the content |

Audit every secret *read* — who, when, source IP, user-agent, stated reason. Recording the access is how a future leak gets traced; recording the value is how one gets created.

## Step 4 — tests that prove the properties, not the happy path

A vault's test suite earns its keep only if these fail loudly when someone refactors:

- ciphertext does not contain the plaintext
- two encryptions of the same input differ (nonce reuse would break GCM)
- tenant B's key cannot decrypt tenant A's blob
- a blob moved to a different `item_id` fails to decrypt
- flipping one bit is detected
- the same cross-tenant checks again **at the HTTP layer**, not just the storage layer — that is where authorization actually lives
- a grep/AST assertion that no method exists which decrypts the zero-knowledge store; for that vault, *absence of code* is the guarantee, so guard it mechanically

Run these against the real database engine. An isolation test that skips for a missing DSN reports green and proves nothing.

## Step 5 — when upstream says "localhost only" and the user says "expose it"

Explicit user instruction wins, but do not just delete the constraint. Record the exception in the project's TRD: the protection the private network was providing, the control replacing each piece, and the event that ends the exception (usually: a VPN exists). Deployment-side controls and the Cloudflare/Route53 constraint live in `swarm-traefik-app-deploy` → `references/public-exposure-without-vpn.md`.

State the residual risk plainly instead of implying the compensations erase it. For a server-side vault, root on the host with the process running reads the master key from memory — that is inherent to unattended decryption and cannot be engineered away without an HSM. Say so; the zero-knowledge half is what still holds in that scenario.
