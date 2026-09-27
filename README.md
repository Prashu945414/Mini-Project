# ChatHub — Real-Time Secure Chat

A Flask chat application using the concepts learned so far, plus Flask-SocketIO for real-time messaging.

## Features

- Username login
- Previous username suggestion after logout
- Flask sessions
- One-to-one chat
- Real-time messages without page refresh
- SQLite message storage
- Fernet encrypted message storage
- Flask-SQLAlchemy
- Blueprint
- Jinja templates
- Clean responsive UI

## Important security note

This is **encrypted message storage**, not true end-to-end encryption.

Messages are encrypted before being stored in SQLite:

```text
User → Flask → Fernet.encrypt() → SQLite
```

The Flask server has the Fernet key and can therefore decrypt the messages.

True E2EE would require the server to never have the decryption key.

## Note if you're upgrading an existing copy

`Message` now has a `timestamp` column. `db.create_all()` only creates
tables that don't exist yet — it won't add a column to a table you
already have. If you've run this before, delete your old database
(`instance/chat.db`) once before running again, or the app will crash
with `no such column: message.timestamp`.

## Run

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Test real-time messaging

1. Open Chrome and login as one username.
2. Open an Incognito window.
3. Login as another username.
4. Open the same chat in both windows.
5. Send a message from one window.
6. It should appear in the other window immediately without refreshing.

## New concept

The only major new Flask-related concept here is:

**Flask-SocketIO**

Normal Flask request:

```text
Browser → request → Flask → response
```

Real-time chat:

```text
Browser ←→ Socket connection ←→ Flask
             ↓
        instant message
```

The message is also saved to SQLite so it is still available after reopening the chat.
