# Exposing a sensitive service publicly, with no VPN

Reached when the user wants remote access to something the upstream project restricts to `127.0.0.1` (a vault, an admin panel, a monitoring console) and there is no VPN yet.

## Cloudflare Tunnel requires the zone on Cloudflare nameservers

Verified in Cloudflare's own docs, and it kills the option whenever DNS lives elsewhere:

- Locally-managed tunnels list as a prerequisite: add the site to Cloudflare and **change the domain nameservers to Cloudflare**. A `CNAME` to `<uuid>.cfargotunnel.com` only resolves through Cloudflare's authoritative NS; pointed from Route53 the tunnel reports healthy while the hostname stays unreachable.
- Keeping an external authoritative DNS and using only the proxy is the *partial / CNAME setup*, and that is **Business or Enterprise plan only**.

So with DNS on Route53 the choices are: migrate the whole zone to Cloudflare, use a separate domain for that one service, or skip the tunnel.

## Hiding the origin IP is worthless on a shared host

Before proposing a tunnel for IP concealment, check whether other hostnames already resolve to the same VPS (`dig +short` each app, compare to `curl -4 ifconfig.me`). On a box where one Traefik fronts several public apps, the address is already published by the neighbours — a tunnel on one hostname hides nothing. What remains on the table is Cloudflare's WAF and DDoS absorption, so argue that benefit or drop the proposal. Do not sell concealment that does not exist.

## Compensating controls when exposing anyway

Each line replaces a specific protection the private network was silently providing:

| Lost | Replacement |
|---|---|
| Network as the perimeter | TLS + HSTS |
| Only a local admin can reach it | TOTP mandatory for every account, no opt-out |
| Brute force bounded by physical access | Rate limit per IP *and* per account, plus lockout persisted in the DB |
| Small attack surface | Strict CSP without inline script, `HttpOnly`/`Secure`/`SameSite` cookies |
| Nothing to detect | Audit every secret access with IP and user-agent |

Edge rate limiting in Traefik (`ratelimit.average` / `burst` / `period`) is the first barrier, but it is not the defence — an in-process limiter dies with the process and resets on redeploy. Persist the lockout counter in the database so it survives restarts and multiple replicas.

## Honest limits to state, not paper over

- **Geo-allowlisting needs a data source.** Plain Traefik injects no country header; `CF-IPCountry` only exists behind Cloudflare. Without a GeoIP database the check is fail-open. Say that rather than listing "geo-blocking" as an active control.
- **Record the withdrawal condition.** A public-exposure exception granted because there is no VPN should name the event that ends it. Write it into the TRD so the temporary state does not quietly become permanent.
