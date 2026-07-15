# AI Lab Prototype

Created a small local web app (FastAPI + a single HTML chat page) powered by Claude, protected by a basic
login, and meant to run on your machine or an internal server first to then be implemented. 


## 2. Contact Chat Bot (`contact-chat-bot/`)

Plain-text "who do I talk to about this?" router, plus optional meeting
scheduling.

**How it works:** you describe an issue -> Claude matches it against a
directory you maintain yourself in `contacts.json` -> it tells you the
best person/department to contact, optionally, connects to zoom scheduler to schedule a meeting and choose meeting room. 


**Nothing is uploaded anywhere.** `contacts.json` and `rooms.json` are
plain local files you edit by hand as of right now. With cybersecurity in mind, actual contacts and information should be encrypted. The only
network call this app makes is to the Anthropic API to classify the issue
text. There is no calendar integration yet: the "scheduling" step just
generates a standard `.ics` file that downloads to your computer, which
you then attach to an email or drag into Outlook.
Time slots are generic next-business-day suggestions, not pulled from
anyone's real calendar. Needs further integration.

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

## General Info

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
   - Contact Chat Bot: fill in `contacts.json` / `rooms.json` by hand.
3. **Tighten access**, 
   - Put application behind Okta instead of the Basic Auth placeholder.
4. **Deploy somewhere persistent**
   - Collaborate to integrate into Slack

