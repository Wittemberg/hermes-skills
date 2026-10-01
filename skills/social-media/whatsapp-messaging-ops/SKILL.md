---
name: whatsapp-messaging-ops
description: "Use when sending WhatsApp messages. Verify delivery."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [whatsapp, messaging, contacts, hermes-send]
---

# WhatsApp Messaging Operations

Use this skill for outbound WhatsApp messages through a configured Hermes gateway.

## Procedure

1. **Resolve destination before sending.** If the user names a person but no recipient number/JID is available, check configured send targets (`hermes send --list whatsapp`) and relevant connected contact lookup capability. Do not treat the user's own WhatsApp chat as the named recipient.
2. **Do not guess identity from names, chat history fragments, or unrelated session files.** If no trustworthy exact recipient mapping is available, ask for the phone number with country/area code or the recipient's WhatsApp JID; alternatively ask the person to message the connected account first if that exposes a verifiable chat destination.
3. **Preserve requested content literally.** If asked to send only a short word or name, do not add greeting, attribution, explanation, emoji, or assistant signature. When the user changes the message, use the latest exact text.
4. **Send only after both recipient and content are unambiguous.** Use Hermes gateway delivery, for example:

   ```bash
   hermes send --to whatsapp:<phone-or-jid> "Oi"
   ```

   Check `hermes send --help` for the installed CLI's exact syntax and quote message text safely.
5. **Verify the send result.** Require a successful CLI/API result before saying it was sent. A message drafted, a recipient listed as the home channel, or an attempted call is not proof of delivery. If the send fails, report that plainly and do not claim success.
6. **Report minimally:** success → “Enviado para <recipient>: <exact text>.” Failure or missing destination → concise blocker and the one piece of information needed.

## Pitfalls

- A personal WhatsApp gateway target is not a contact directory and must never be substituted for the intended recipient.
- Never infer or fabricate a phone number/JID from a display name; delivery to the wrong person is an external side effect.
- Do not claim a message was sent until the gateway confirms success.
- For a request to send a harmless short message, avoid unnecessary confirmation once recipient and exact text are clear.