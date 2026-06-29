# Summit Hiking Club Web App

Flask/SQLite web app for MSSE642 Project 4 (pen-testing target).

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in a browser. The database (`hiking_club.db`) is
created and seeded automatically on first run.

## Seed accounts

| Username | Password   | Role   |
|----------|------------|--------|
| admin    | admin123   | admin  |
| jdoe     | member123  | member |
| bsmith   | member123  | member |

## Deploying to a target VM

```bash
# On the target Ubuntu VM:
sudo apt update && sudo apt install -y python3 python3-pip
pip3 install flask werkzeug
python3 app.py
```

The app listens on `0.0.0.0:5000` by default, so it's reachable from the
Kali attack box at `http://<target-ip>:5000`.

Set `SECRET_KEY` env var to a real random value before deploying:
```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
python3 app.py
```
