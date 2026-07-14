# AI Lab Prototypes

Two working prototypes built for the AI lab. Both are small local web apps
(FastAPI + a single HTML chat page) powered by Claude, protected by a basic
login, and meant to run on your machine or an internal server first.

## 1. AI Chat Bot (`ai-chat-bot/`)

Plain-text Q&A over your company's IT equipment: computers, monitors,
monitor arms, docks, and cable stock (in that priority order).

**Ask things like:**
- "What computer does Jamie Chen have?"
- "How many monitors do we have left?"
- "What's on Priya Patel's desk?"
- "How many USB-C cables are in stock?"

**How it works:** your question -> Claude writes a safe read-only SQL query
against a SQLite database -> the query runs -> Claude turns the results
back into a plain-English answer. The SQL step is locked down to
`SELECT`-only, single-statement queries.

**Right now it runs on sample data** (20 fake employees, realistic device
mix). Swap in your real inventory once you get export access to your
company's device management system -- see "Connecting real data" below.

### Run it
```
cd ai-chat-bot
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY, set a real login
python seed_data.py         # creates + fills assets.db with sample data
uvicorn app:app --reload --port 8000
```
Open http://localhost:8000 and log in with the username/password from `.env`.

### Connecting real data
Once you can export your device inventory (CSV, API, whatever your
management tool supports), write a loader that inserts rows into the two
tables in `database.py`:
- `assets` -- one row per computer/monitor/monitor arm/dock, with
  `asset_type`, `assigned_to`, `status`, etc.
- `cable_inventory` -- one row per cable type, tracked by quantity instead
  of individually.

Replace the call to `seed_data.seed()` with your loader (or just run your
loader instead of `seed_data.py`). No other code needs to change --
`nl_query.py` only knows about the schema, not where the data came from.

---

## 2. Contact Chat Bot (`contact-chat-bot/`)

Plain-text "who do I talk to about this?" router, plus optional meeting
scheduling.

**How it works:** you describe an issue -> Claude matches it against a
directory you maintain yourself in `contacts.json` -> it tells you the
best person/department to contact, with its confidence and reasoning ->
optionally, pick a suggested time and download a calendar invite (`.ics`)
that has that person as the attendee and (if you pick one) a room as the
location.

**Nothing is uploaded anywhere.** `contacts.json` and `rooms.json` are
plain local files you edit by hand -- fill them in with your real
directory whenever you're ready, no import/upload step needed. The only
network call this app makes is to the Anthropic API to classify the issue
text. There is no calendar integration: the "scheduling" step just
generates a standard `.ics` file that downloads to your computer, which
you then attach to an email or drag into Outlook/Google Calendar yourself.
Time slots are generic next-business-day suggestions, not pulled from
anyone's real calendar.

### Run it
```
cd contact-chat-bot
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY, set a real login
uvicorn app:app --reload --port 8001
```
Open http://localhost:8001 and log in with the username/password from `.env`.

### Filling in your real directory
Edit `contacts.json`: one entry per contact, with a `keywords` field
describing in plain language what kinds of issues they handle (this is
what the AI matches against -- be specific). Edit `rooms.json` the same
way if you want real room names to show up as invite locations.

---

## Both apps, in general

- **Login:** both use HTTP Basic Auth (a username/password prompt in the
  browser) as a lightweight "internal use only" gate -- good enough for a
  lab demo, but not real access control. See below for production.
- **API key:** both need `ANTHROPIC_API_KEY` in their `.env` file. Get one
  from the Anthropic Console. Check the current model names in
  https://docs.claude.com before deploying, in case `ANTHROPIC_MODEL` in
  `.env.example` is out of date by the time you read this.
- **Cost:** each question is 1-2 small Claude API calls. For an internal
  tool used by a department, this is cheap, but worth keeping an eye on
  usage if it gets wider adoption.

## Next steps toward a real rollout

1. **Demo both locally** in the lab with sample/manual data (works today,
   no further setup beyond an API key).
2. **Swap in real data:**
   - AI Chat Bot: a loader script from your device management export.
   - Contact Chat Bot: fill in `contacts.json` / `rooms.json` by hand.
3. **Tighten access**, since you said this should be IT-department-only:
   - Simplest: run it on a machine/server only reachable over your
     company VPN or internal network (no public internet exposure).
   - Better: put it behind your company SSO (e.g. an internal reverse
     proxy with Okta/Azure AD auth) instead of the Basic Auth placeholder.
   - Either way, change the default username/password in `.env` before
     anyone else touches this.
4. **Deploy somewhere persistent** once it's proven out -- options in
   rough order of effort:
   - An internal server/VM you already have, running via `uvicorn` behind
     a process manager (systemd, pm2, etc.) or Docker.
   - A small managed host (Render, Railway, Fly.io) with access
     restricted by IP allowlist or a VPN, if you don't have internal
     server space.
   - Ask your team whether a Cowork connector/plugin makes more sense
     long-term than a standalone web app, if you want this reachable from
     chat tools people already use (e.g. Slack) rather than a separate
     webpage.
5. **Iterate on the lower-priority asset types** (desk/office setups,
   cables) as planned -- the schema already supports all of them, so this
   is just a matter of getting more complete data in.
