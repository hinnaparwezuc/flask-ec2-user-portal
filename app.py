from pathlib import Path
import re
import sqlite3
import uuid

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"txt"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-to-a-long-random-value"
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
UPLOAD_DIR.mkdir(exist_ok=True)


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                address TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def count_words(file_path):
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"\b[\w'-]+\b", text))


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.route("/")
def index():
    return redirect(url_for("profile" if session.get("user_id") else "register"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    fields = {
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", ""),
        "first_name": request.form.get("first_name", "").strip(),
        "last_name": request.form.get("last_name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "address": request.form.get("address", "").strip(),
    }
    upload = request.files.get("text_file")

    if not all(fields.values()) or not upload or not upload.filename:
        flash("Please complete every field and choose a text file.", "error")
        return render_template("register.html", form=fields), 400

    original_name = secure_filename(upload.filename)
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in ALLOWED_EXTENSIONS:
        flash("Only .txt files are accepted.", "error")
        return render_template("register.html", form=fields), 400

    stored_name = f"{uuid.uuid4().hex}.txt"
    saved_path = UPLOAD_DIR / stored_name
    upload.save(saved_path)
    word_count = count_words(saved_path)

    try:
        with get_db() as db:
            cursor = db.execute(
                """
                INSERT INTO users
                (username, password_hash, first_name, last_name, email, address,
                 original_filename, stored_filename, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["username"],
                    generate_password_hash(fields["password"]),
                    fields["first_name"],
                    fields["last_name"],
                    fields["email"],
                    fields["address"],
                    original_name,
                    stored_name,
                    word_count,
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        saved_path.unlink(missing_ok=True)
        flash("That username is already registered. Choose another one.", "error")
        return render_template("register.html", form=fields), 409

    session.clear()
    session["user_id"] = user_id
    flash("Registration complete. Your details and file were saved.", "success")
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Incorrect username or password.", "error")
        return render_template("login.html", username=username), 401

    session.clear()
    session["user_id"] = user["id"]
    flash("Welcome back! Your saved information was retrieved.", "success")
    return redirect(url_for("profile"))


@app.route("/profile")
def profile():
    user = current_user()
    if user is None:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for("login"))
    return render_template("profile.html", user=user)


@app.route("/download")
def download_file():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    if not (UPLOAD_DIR / user["stored_filename"]).is_file():
        abort(404)
    return send_from_directory(
        UPLOAD_DIR,
        user["stored_filename"],
        as_attachment=True,
        download_name=user["original_filename"],
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are logged out. Log in again to retrieve your saved profile.", "success")
    return redirect(url_for("login"))


@app.errorhandler(413)
def file_too_large(_error):
    flash("The selected file is too large. Maximum size: 1 MB.", "error")
    return redirect(url_for("register"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
