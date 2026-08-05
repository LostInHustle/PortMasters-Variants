"""
PortMasters Multiplayer Server
Flask + SocketIO backend with real-time chat and presence system.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import json, os, re

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "portmasters-prod-key-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portmasters.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

db = SQLAlchemy(app)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    ping_timeout=60,
    ping_interval=25,
)


# =============================================================================
# Database Models
# =============================================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_emoji = db.Column(db.String(10), default="🚢")
    gold = db.Column(db.Integer, default=100)
    score = db.Column(db.Integer, default=0)
    current_round = db.Column(db.Integer, default=1)
    max_rounds = db.Column(db.Integer, default=8)
    phase = db.Column(db.String(50), default="0")
    game_state = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_public(self, online=False):
        return {
            "id": self.id,
            "username": self.username,
            "avatar_emoji": self.avatar_emoji,
            "gold": self.gold,
            "score": self.score,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "phase": self.phase,
            "online": online,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


# =============================================================================
# Presence Tracking (in-memory, survives server restart via last_seen)
# =============================================================================
online_sids = {}  # sid -> user_id
user_sids = {}  # user_id -> sid

AVATAR_POOL = [
    "🚢",
    "⚓",
    "🌊",
    "🧭",
    "🦈",
    "🐙",
    "🐬",
    "🐋",
    "🦀",
    "🐚",
    "🎣",
    "🏴‍☠️",
    "👑",
    "🦅",
    "🐉",
]


def pick_avatar(username):
    h = sum(ord(c) for c in username)
    return AVATAR_POOL[h % len(AVATAR_POOL)]


def broadcast_presence():
    users = []
    for u in User.query.all():
        online = u.id in user_sids
        users.append(u.to_public(online=online))
    socketio.emit("presence_update", {"users": users})


# =============================================================================
# HTTP Routes
# =============================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    d = request.json or {}
    username = (d.get("username") or "").strip()
    password = d.get("password") or ""
    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        return (
            jsonify(
                ok=False, msg="Username: 3-20 chars, letters/numbers/underscore only"
            ),
            400,
        )
    if len(password) < 4:
        return jsonify(ok=False, msg="Password must be at least 4 characters"), 400
    if User.query.filter_by(username=username).first():
        return jsonify(ok=False, msg="Username already taken"), 409

    u = User(username=username, avatar_emoji=pick_avatar(username))
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    session.permanent = True
    session["user_id"] = u.id
    return jsonify(ok=True, user=u.to_public())


@app.route("/api/login", methods=["POST"])
def login():
    d = request.json or {}
    u = User.query.filter_by(username=d.get("username")).first()
    if not u or not u.check_password(d.get("password", "")):
        return jsonify(ok=False, msg="Invalid credentials"), 401
    session.permanent = True
    session["user_id"] = u.id
    u.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify(ok=True, user=u.to_public())


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify(ok=True)


@app.route("/api/me")
def me():
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False), 401
    u = User.query.get(uid)
    if not u:
        return jsonify(ok=False), 401
    return jsonify(
        ok=True,
        user=u.to_public(online=uid in user_sids),
        game_state=json.loads(u.game_state or "{}"),
    )


@app.route("/api/users")
def users_list():
    out = []
    for u in User.query.all():
        out.append(u.to_public(online=u.id in user_sids))
    return jsonify(ok=True, users=out)


@app.route("/api/game/save", methods=["POST"])
def game_save():
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False), 401
    u = db.session.get(User, uid)
    if not u:
        return jsonify(ok=False), 404
    d = request.json or {}
    u.gold = d.get("money", u.gold)
    u.score = d.get("score", u.score)
    u.current_round = d.get("currentRound", u.current_round)
    u.max_rounds = d.get("maxRounds", u.max_rounds)
    u.phase = str(d.get("phase", u.phase))
    u.game_state = json.dumps(d.get("state", {}))
    u.last_seen = datetime.now(timezone.utc)
    db.session.commit()
    broadcast_presence()
    return jsonify(ok=True)


@app.route("/api/game/load")
def game_load():
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False), 401
    u = User.query.get(uid)
    return jsonify(ok=True, game_state=json.loads(u.game_state or "{}"))


@app.route("/api/chat/<int:peer_id>")
def chat_history(peer_id):
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False), 401
    msgs = (
        Message.query.filter(
            ((Message.sender_id == uid) & (Message.receiver_id == peer_id))
            | ((Message.sender_id == peer_id) & (Message.receiver_id == uid))
        )
        .order_by(Message.timestamp.asc())
        .limit(200)
        .all()
    )

    # mark received as read
    Message.query.filter_by(sender_id=peer_id, receiver_id=uid, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()

    out = [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in msgs
    ]
    return jsonify(ok=True, messages=out)


@app.route("/api/chat/unread")
def chat_unread():
    uid = session.get("user_id")
    if not uid:
        return jsonify(ok=False), 401
    rows = (
        db.session.query(Message.sender_id, db.func.count(Message.id))
        .filter(Message.receiver_id == uid, Message.is_read == False)
        .group_by(Message.sender_id)
        .all()
    )
    return jsonify(ok=True, unread={str(s): c for s, c in rows})


# =============================================================================
# SocketIO Events
# =============================================================================
@socketio.on("connect")
def sio_connect(_auth=None):
    uid = session.get("user_id")
    if not uid:
        disconnect()
        return
    online_sids[request.sid] = uid
    user_sids[uid] = request.sid
    join_room(f"user_{uid}")
    u = db.session.get(User, uid)
    if u:
        u.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    broadcast_presence()
    emit("connected", {"uid": uid})


@socketio.on("disconnect")
def sio_disconnect():
    uid = online_sids.pop(request.sid, None)
    if uid:
        user_sids.pop(uid, None)
        broadcast_presence()


@socketio.on("send_message")
def sio_send_message(data):
    uid = session.get("user_id")
    if not uid:
        return
    peer_id = data.get("peer_id")
    content = (data.get("content") or "").strip()
    if not peer_id or not content or len(content) > 1000:
        return
    if not User.query.get(peer_id):
        return

    m = Message(sender_id=uid, receiver_id=peer_id, content=content)
    db.session.add(m)
    db.session.commit()

    payload = {
        "id": m.id,
        "sender_id": uid,
        "receiver_id": peer_id,
        "content": content,
        "timestamp": m.timestamp.isoformat(),
    }
    emit("new_message", payload, room=f"user_{peer_id}")
    emit("new_message", payload, room=f"user_{uid}")

    # unread counter broadcast
    unread = (
        db.session.query(Message.sender_id, db.func.count(Message.id))
        .filter(Message.receiver_id == peer_id, Message.is_read == False)
        .group_by(Message.sender_id)
        .all()
    )
    socketio.emit(
        "unread_update",
        {"user_id": peer_id, "unread": {str(s): c for s, c in unread}},
        room=f"user_{peer_id}",
    )


@socketio.on("typing")
def sio_typing(data):
    uid = session.get("user_id")
    peer_id = data.get("peer_id")
    if not uid or not peer_id:
        return
    u = User.query.get(uid)
    emit(
        "user_typing", {"user_id": uid, "username": u.username}, room=f"user_{peer_id}"
    )


# =============================================================================
# DB init & Run
# =============================================================================
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    print("\n  ⚓ PortMasters Multiplayer Server")
    print("  🌐 Open: http://localhost:2000\n")
    socketio.run(app, host="0.0.0.0", port=2000, debug=True)
