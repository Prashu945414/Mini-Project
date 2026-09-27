from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_socketio import join_room
from cryptography.fernet import Fernet

from extensions import db, socketio
from chat.models import User, Message, ConversationRead

chat = Blueprint("chat", __name__)

# Learning-project key. Move this to an environment variable for real deployment.
FERNET_KEY = b"wQ0wGQJYxwY5QJw3s1m7qJtR2Kk8Vd0n8wFh4Qy9cYQ="
cipher = Fernet(FERNET_KEY)

# In-memory set of usernames with at least one open Socket.IO connection.
# Simple presence tracking for this learning project: it resets whenever the
# server restarts, and doesn't distinguish "two tabs open" from "one tab" —
# any disconnect (even a stray one from a second tab) marks the user offline.
# Good enough to demo real-time online/offline status; a production version
# would count connections per user instead of just tracking membership.
online_users = set()


def format_time(dt):
    if not dt:
        return ""
    # Strip a leading zero from the hour ("09:15 AM" -> "9:15 AM").
    return dt.strftime("%I:%M %p").lstrip("0")


def get_last_message(user_a, user_b):
    return (
        Message.query.filter(
            ((Message.sender == user_a) & (Message.receiver == user_b))
            | ((Message.sender == user_b) & (Message.receiver == user_a))
        ).order_by(Message.timestamp.desc()).first()
    )


def get_unread_count(username, contact_username):
    read_state = ConversationRead.query.filter_by(
        username=username,
        contact_username=contact_username,
    ).first()
    last_read_id = read_state.last_read_message_id if read_state else 0

    return Message.query.filter(
        Message.sender == contact_username,
        Message.receiver == username,
        Message.id > last_read_id,
    ).count()


def mark_conversation_read(username, contact_username, through_message_id):
    read_state = ConversationRead.query.filter_by(
        username=username,
        contact_username=contact_username,
    ).first()

    if read_state is None:
        read_state = ConversationRead(
            username=username,
            contact_username=contact_username,
            last_read_message_id=through_message_id,
        )
        db.session.add(read_state)
    else:
        read_state.last_read_message_id = max(
            read_state.last_read_message_id,
            through_message_id,
        )

    db.session.commit()


def build_contact_list(current_user):
    """Sidebar data: every other registered user, plus a preview of the
    last message between them and the current user (if any), plus whether
    they're currently online."""
    other_users = User.query.filter(User.username != current_user).all()
    contacts = []

    for u in other_users:
        last = get_last_message(current_user, u.username)
        preview = "Say hi \U0001F44B"
        last_time = ""

        if last:
            preview = cipher.decrypt(last.message.encode()).decode()
            last_time = format_time(last.timestamp)

        contacts.append({
            "username": u.username,
            "preview": preview,
            "time": last_time,
            "online": u.username in online_users,
            "unread_count": get_unread_count(current_user, u.username),
        })

    return contacts


@chat.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("chat.login"))

    contacts = build_contact_list(session["user"])
    return render_template("home.html", user=session["user"], contacts=contacts)


@chat.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if not username:
            flash("Enter a username.")
            return redirect(url_for("chat.login"))

        if len(username) > 24:
            flash("Username must be 24 characters or fewer.")
            return redirect(url_for("chat.login"))

        user = User.query.filter_by(username=username).first()

        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        session["user"] = username
        session["last_username"] = username
        return redirect(url_for("chat.home"))

    return render_template(
        "login.html",
        previous_username=session.get("last_username"),
    )


@chat.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("chat.login"))


@chat.route("/chat/<username>")
def chat_page(username):
    if "user" not in session:
        return redirect(url_for("chat.login"))

    current_user = session["user"]

    if username == current_user:
        flash("You can't start a chat with yourself.")
        return redirect(url_for("chat.home"))

    if not User.query.filter_by(username=username).first():
        flash(f'No user named "{username}" found.')
        return redirect(url_for("chat.home"))

    received_message = Message.query.filter_by(
        sender=username,
        receiver=current_user,
    ).order_by(Message.id.desc()).first()
    if received_message:
        mark_conversation_read(current_user, username, received_message.id)
        socketio.emit(
            "conversation_read",
            {"contact_username": username},
            room=f"user_{current_user}",
        )

    messages = Message.query.filter(
        ((Message.sender == current_user) & (Message.receiver == username))
        | ((Message.sender == username) & (Message.receiver == current_user))
    ).order_by(Message.timestamp).all()

    chat_messages = []
    for msg in messages:
        chat_messages.append({
            "sender": msg.sender,
            "message": cipher.decrypt(msg.message.encode()).decode(),
            "time": format_time(msg.timestamp),
        })

    return render_template(
        "chat.html",
        user=current_user,
        other_user=username,
        other_user_online=username in online_users,
        messages=chat_messages,
        contacts=build_contact_list(current_user),
    )


@chat.route("/send/<username>", methods=["POST"])
def send_message(username):
    if "user" not in session:
        return {"error": "Not logged in"}, 401

    if not User.query.filter_by(username=username).first():
        return {"error": "Recipient does not exist"}, 404

    text = request.form.get("message", "").strip()

    if not text:
        return {"error": "Empty message"}, 400

    current_user = session["user"]
    encrypted_message = cipher.encrypt(text.encode()).decode()

    new_message = Message(
        sender=current_user,
        receiver=username,
        message=encrypted_message
    )

    db.session.add(new_message)
    db.session.commit()

    # Deliver the message to the open chat and notify the recipient's tabs.
    socketio.emit(
        "new_message",
        {
            "sender": current_user,
            "receiver": username,
            "message": text,
            "time": format_time(new_message.timestamp),
            "message_id": new_message.id,
        },
        room=f"chat_{min(current_user, username)}_{max(current_user, username)}"
    )
    socketio.emit(
        "message_notification",
        {
            "sender": current_user,
            "message": text,
            "time": format_time(new_message.timestamp),
            "message_id": new_message.id,
        },
        room=f"user_{username}",
    )

    return {"success": True}


@socketio.on("connect")
def handle_connect():
    user = session.get("user")
    if user:
        join_room(f"user_{user}")
        online_users.add(user)
        socketio.emit("presence_update", {"online_users": list(online_users)})


@socketio.on("disconnect")
def handle_disconnect():
    user = session.get("user")
    if user:
        online_users.discard(user)
        socketio.emit("presence_update", {"online_users": list(online_users)})


@socketio.on("join_chat")
def join_chat(data):
    user = session.get("user")
    other_user = data.get("other_user")

    if not user or not other_user:
        return

    room = f"chat_{min(user, other_user)}_{max(user, other_user)}"
    join_room(room)


@socketio.on("mark_chat_read")
def handle_mark_chat_read(data):
    if not isinstance(data, dict):
        return

    user = session.get("user")
    other_user = data.get("other_user")
    message_id = data.get("message_id")

    if not user or not isinstance(other_user, str) or not isinstance(message_id, int):
        return

    received_message = Message.query.filter(
        Message.id <= message_id,
        Message.sender == other_user,
        Message.receiver == user,
    ).order_by(Message.id.desc()).first()

    if not received_message:
        return

    mark_conversation_read(user, other_user, received_message.id)
    socketio.emit(
        "conversation_read",
        {"contact_username": other_user},
        room=f"user_{user}",
    )
