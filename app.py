from flask import Flask
from flask_socketio import SocketIO
from extensions import db, socketio
from chat.routes import chat

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# SocketIO adds real-time communication.
socketio.init_app(app, cors_allowed_origins="*")

app.register_blueprint(chat)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    socketio.run(app, debug=True)
