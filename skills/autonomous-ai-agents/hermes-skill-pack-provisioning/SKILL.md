---
name: hermes-skill-pack-provisioning
description: "Install skill packs from Git; rewrite SOUL.md identity. Use when installing a skill pack from a Git repository into a Hermes profile or adapting foreign skill packs to local conventions."
version: 1.0.0
metadata:
  hermes:
    tags: [hermes, skills, install, soul, provisioning, github]
---

# Provisioning a Hermes instance: skill packs and SOUL.md

Use when installing third-party skill packs from a Git repo into `$HERMES_HOME/skills`, adapting foreign-layout skills, or rewriting the instance identity in `$HERMES_HOME/SOUL.md`. Both jobs only take effect in a NEW session — close every report with that gate.

Resolve the home from `$HERMES_HOME` when a profile is active; never hardcode `~/.hermes`.

## Installing a skill pack from GitHub

1. Probe the tarball before extracting — a wrong default branch fails silently mid-pipe:
   ```bash
   curl -sIL -o /dev/null -w "%{http_code} %{url_effective}\n" https://github.com/<owner>/<repo>/archive/main.tar.gz
   ```
2. If the user gave an exact extraction command and the layout matches, run it. Grab ONLY the wanted subtree; `--strip-components` must equal the number of path segments above the directory you name:
   ```bash
   mkdir -p "$HERMES_HOME/skills"
   curl -L https://github.com/<owner>/<repo>/archive/main.tar.gz \
     | tar -xz -C "$HERMES_HOME/skills" --strip-components=3 <repo>-main/.hermes/skills/<pack>
   ```
3. If the repo layout is unknown, extract to `$TMPDIR` first and inspect — never pipe an unknown tree straight into `skills/`:
   ```bash
   cd "$TMPDIR" && mkdir -p dl && curl -sL <tarball> | tar -xz -C dl && find dl -maxdepth 4 | sort
   ```
   Skills are often NOT at `.hermes/skills/`. Locate them by topic, not by path guess: `find . -iname "*<topic>*"` plus `grep -ril "<topic>" .`; the same subject is frequently split across two files in different trees (e.g. an app-facing skill and a raw API-quirks note) — merge them into one SKILL.md plus `references/`.
4. Verify what landed and that nothing extraneous came along:
   ```bash
   find "$HERMES_HOME/skills/<pack>" -maxdepth 2 | sort
   find "$HERMES_HOME/skills/<pack>" -name SKILL.md | wc -l
   ```
5. Validate frontmatter parses before declaring success — a pack with a broken YAML header loads as nothing:
   ```bash
   python3 -c "import yaml;d=yaml.safe_load(open('SKILL.md').read().split('---')[1]);print(d['name'])"
   ```
6. Grep installed skills for overlap with the new pack (`grep -l -i "<distinctive-string>" "$HERMES_HOME"/skills/*/*/SKILL.md`) and report either the conflict or the clean result. Similar names are not conflicts — state why (an OLT skill and a CFTV skill for the same vendor are different domains).
7. Drop a `SOURCE.txt` in the installed directory: origin URL, which upstream files it came from, and every adaptation you made. Without it the next session cannot tell hand-written content from vendored content.
8. Clean up the `$TMPDIR` staging copy.

Adapting a skill written for another runtime: `references/adapting-foreign-skill-packs.md`.

## Rewriting SOUL.md

- Back it up first — `cp SOUL.md SOUL.md.bak.$(date +%Y%m%d_%H%M%S)` — and name the backup path in the report. The default SOUL.md carries the house response-style rules, and overwriting it silently drops them.
- Write plain prose in ALL-CAPS labelled sections (ESPECIALIDADES, ESTILO, SEGURANÇA, AUTONOMIA, BACKUP...). No markdown headers or bullets: it is injected as a system prompt, not rendered.
- Write it in the language the user wants answers in. It is the identity the model reads every turn; a Portuguese-speaking user gets a Portuguese SOUL.md.
- Keep the user's own safety and autonomy clauses verbatim in intent — do not soften a "NUNCA sem confirmação" into a hedge, and do not add consultation gates the user did not ask for.
- Echo the finished file back in the reply. The user cannot see the write and will want to read what now governs every session.

## Reporting

- Finish with the reload gate: run `/reload-skills`, then `/new`. You cannot start a session for the user from inside one — say so plainly instead of claiming it is done.
- List installed skills grouped by domain, not as a raw alphabetical dump — the user is scanning for coverage gaps.
- State every adaptation you made and why. A silently rewritten skill is worse than a missing one.
