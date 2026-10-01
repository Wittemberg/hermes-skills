---
name: layer-contract-testing
description: "Use when layers are built apart: test their seams."
version: 1.0.0
metadata:
  hermes:
    tags: [testing, integration, delegation, contracts, regression, web]
---

# Testing the seams between separately-built layers

Use when a feature's layers are authored apart from each other: fanned out to parallel subagents, split across sessions, or simply a template written at a different time than the route that renders it. The bugs do not land inside the layers — each one's own tests pass — they land on the **seams**, where one layer's output name meets another layer's input name.

A seam bug is invisible to layer-local tests because each test constructs its inputs in the shape its own layer expects. The route's test posts `password` because the route reads `password`; it never learns the form sends `senha`.

## 1. Write the contract before fanning out

When splitting work, fix the shared vocabulary in the task briefs: exact field names, exact dict keys, exact column names. Give every child the same list. Naming is the whole seam — a child that invents `titulo_claro` while another reads `title` has done nothing wrong locally and has still broken the feature.

Prefer one name end to end. Where a boundary must rename (DB column `blob_ciphertext` vs template variable), write the mapping down in the brief rather than letting each side guess.

## 2. Treat every child's "tests pass" as layer-local

A subagent reporting green has tested its own layer. It has not, and cannot, test a seam with code it never saw. Integration is the parent's job and it is not optional. Budget for it: expect several seam fixes after a clean fan-out, and do not report the feature working until an end-to-end path has actually run.

## 3. Inventory the seams mechanically

Don't eyeball it. Extract both sides and diff the sets. For a server-rendered web app:

```bash
# what each form actually sends
for f in templates/*.html; do
  echo "$(basename $f): $(grep -oE 'name="[a-z_]+"' $f | sort -u | tr '\n' ' ')"
done

# what the routes actually read
grep -oE 'request\.form(\.get\(|\[)"[a-z_]+"' app.py | grep -oE '"[a-z_]+"' | sort -u
```

The same move generalizes: template variables vs the dict the view passes, DB column names vs the attribute the serializer reads, JSON keys the client sends vs the keys the handler pops. Any pair where one side writes a name and the other side reads it by name.

## 4. Turn the inventory into a standing test

A one-time grep finds today's bugs. A test that parses both artifacts and asserts the sets agree prevents the whole class. Read the real files at test time — do not hardcode the expected names, or the test becomes a third place to get them wrong.

```python
def test_route_receives_every_field_it_reads(template, endpoint):
    sent = set(re.findall(r'name="([a-z_]+)"', (TEMPLATES / template).read_text()))
    read = _fields_read_by_view(endpoint) - OPTIONAL
    assert not (read - sent), f"{template} never sends {sorted(read - sent)}"
```

Keep an explicit allowlist for fields that are genuinely optional or injected by JS, so the test stays honest instead of being loosened until it passes.

## 5. Prove the new test actually catches the bug

After writing a regression test, **reintroduce the defect, watch the test fail, then restore it.** A test written against already-fixed code can pass for the wrong reason — matching on something incidental — and a green suite then certifies a guard that guards nothing.

```bash
sed -i 's/name="password"/name="senha"/' templates/login.html
pytest tests/test_contracts.py -q          # must FAIL here
git checkout templates/login.html
pytest tests/test_contracts.py -q          # green again
```

## 6. Client-side validation is part of the seam

A field marked `required` in HTML blocks submission in the browser before any request is sent, so server-side tests never see it. Check that required-ness matches the real flow: a second-factor field marked `required` traps a user whose second factor is not enrolled yet, on the exact screen where they are supposed to enroll it.

The mirror of this: when JS rewrites the form before submit (encrypting fields, stripping `name` attributes), the names that reach the server are the ones JS leaves behind, not the ones in the static HTML. Assert on the post-JS shape, and keep a test that no cleartext-secret field carries a `name` at all.

## 7. Name contracts do not catch flow deadlocks

The seam tests above compare names. They pass completely on a feature that no user can get through, because a deadlock is a property of the *sequence*, not of any field.

The recurring shape: state that the whole feature depends on has no home of its own and is instead derived from the first record. With zero records the state reads as absent, the UI offers to create it, and creating a record requires the state to already exist. The user loops forever, and every layer is individually correct.

Give bootstrap state its own column or row on the owning entity, so the container exists from the moment it is created and not from its first child. Then assert the empty case directly — create the container, add nothing, reload, and check the UI offers the *next* step rather than creation again.

Related: when a client generates such a value (a KDF salt, a nonce, an id), persist it in a dedicated write and read it back from storage on later requests. A hidden form field that is generated and never posted is silently dropped — check the enclosing `<form>` actually has an `action` and `method`. Taking the value from the request on every write is the other failure: a forged field then redefines the record's own key material, so the server should treat the stored copy as authoritative and ignore the submitted one.

Write-once is usually the correct rule for that state; make the update conditional (`WHERE col IS NULL`) so an accidental second "create" cannot rotate it and orphan every existing record.

## 8. Script the user's journey, not the endpoints

Name-diff tests and per-layer tests both miss ordering bugs, so the only thing that proves the feature works is one script that walks the whole path the way a person does: log in, land on the empty state, create the container, create the first record, reload, read it back. Run it against the deployed service over the public hostname, parsing each form out of the served HTML as you go.

Keep that script in CI once it passes. A journey verified by hand once is a journey that regresses on the next refactor — and the three-bugs-in-a-row pattern after a fan-out is exactly what it is for.

## Seam checklist

| Seam | Failure mode |
|---|---|
| form field name ↔ `request.form[...]` | value arrives empty; login rejects a correct password |
| view context dict ↔ template variable | block silently never renders |
| DB column ↔ template attribute | `UndefinedError`, or blank cell |
| id type across layers | `str` from a URL never `==` a `UUID` from the driver; compare as strings |
| route name ↔ `url_for(...)` | build error at render time |
| optional-vs-required per field | `KeyError` 500 on a field the form omits |
| bootstrap state derived from first record | empty state loops: create needs state, state needs a record |
| client-generated value never posted | form has no `action`/`method`; value is regenerated every visit |
