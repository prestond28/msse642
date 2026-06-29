# Hiking Club Web App — Project Brief

## Context
This is a rebuild of the Hiking Club website for a graduate cybersecurity course
assignment (Hands-On Project #4: Penetration Testing, Part 2). The original site
was hit by ransomware; this is a from-scratch redesign that will later be
deployed to a pen-testing lab VM (Kali Linux + target VM) and tested with
OWASP ZAP. The architecture below is trimmed down from a more elaborate
Assignment #2 design doc — only build what's listed here. Anything marked
"out of scope" should NOT be implemented; just leave it out cleanly.

## Stack
- **Backend:** Python 3 + Flask
- **Database:** SQLite (single file, no external DB server)
- **Frontend:** Server-rendered HTML templates (Jinja2) + minimal CSS. No
  frontend framework, no build step — keep it simple enough to deploy on a
  bare Ubuntu VM with just `pip install flask`.
- **Auth:** Session-based login (Flask sessions), passwords hashed
  (werkzeug.security or similar)

## Roles
1. **Guest** (not logged in)
2. **Member** (logged-in regular user)
3. **Trip Leader** (admin subtype — manages their own events)
4. **System Admin** (admin subtype — manages accounts)

For this prototype, Trip Leader and System Admin can be combined into a
single `role = "admin"` field on the user model if that's simpler — don't
over-engineer a permissions system. Document in code comments where the
real app would eventually split these into separate roles.

## Features to build

### Guest
- Public trip listing page (no login required) — list of trips with name,
  date, short description

### Auth
- Register (member signup)
- Login / logout
- Passwords stored hashed, never plaintext

### Member
- View trip listing (same as guest, but logged in)
- Register for a trip (adds member to that trip's roster)
- Edit own profile (name, email, emergency contact field)
- View own profile

### Admin (Trip Leader functions)
- Create a new trip/event
- Edit/delete a trip they created
- View list of members registered for their trip

### Admin (System Admin functions)
- View list of all user accounts
- Disable/enable a user account

## Explicitly OUT of scope
Do not build any of the following — they exist in the original architecture
doc but are intentionally excluded from this prototype:
- Treasury/payment portal
- Wait-list logic or auto-promotion from wait list
- Reporting/analytics (e.g. no-show stats, cancellation stats)
- Medical info fields / "private notes" on members (the emergency contact
  field on profile stands in for "sensitive data" instead)

## Security notes (read carefully)
This app will be deliberately tested with OWASP ZAP as part of the
assignment, and the results should tie back to an existing STRIDE/OWASP
threat model for this same app. Build it as a **reasonably normal,
not-deliberately-broken** app — i.e., don't add intentional backdoors — but
also don't over-harden it with defenses beyond what a typical first-pass
implementation would have. The goal is to produce a realistic app where
ZAP can surface findings naturally (e.g., testing whether access control on
admin routes and the profile-edit route is properly enforced server-side,
not just hidden in the UI), not a CTF-style app full of planted flaws.

## Project structure preferences
- Keep it in a single Flask app with a clear file layout (e.g. `app.py`,
  `models.py`, `templates/`, `static/`) — no need for blueprints or
  packages at this scale.
- Include a `requirements.txt`.
- Include a short `README.md` with setup/run instructions, since this will
  be deployed on a separate VM and I'll need to follow my own setup steps
  there.
- Seed the database with a few sample trips and at least one admin account
  and one member account on first run, so the app is testable immediately
  without manual data entry.

## What I'll do with this after it's built
I will deploy this on a fresh VM/container in my pen-testing lab (separate
from my Kali attack box) and then run OWASP ZAP against it from Kali. So:
favor anything that makes deployment to a plain Ubuntu VM simple over
anything that optimizes for local dev convenience.
