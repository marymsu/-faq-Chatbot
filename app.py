from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_cors import CORS
import json
import sqlite3
import os

from nlp import get_nlp_response

app = Flask(__name__)

# Simple in-memory cache for NLP responses (key: lowercased question)
# Avoids repeat Gemini API calls for the same question within a session.
_nlp_cache: dict = {}
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")  # set SECRET_KEY in production
CORS(app)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "usiu123")

# Load JSON fallback dataset
with open("database.json", "r") as file:
    database = json.load(file)


# ---------------------------------------------------------------------------
# Bot logic
# ---------------------------------------------------------------------------

def get_response_from_db(user_message: str) -> str:
    """Search the SQLite `responses` table using keyword matching."""
    db_path = "chatbot.db"
    if not os.path.exists(db_path):
        return ""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT input, response FROM responses")
    rows = cursor.fetchall()
    conn.close()

    user_message_lower = user_message.lower()
    for row in rows:
        keywords = (row[0] or "").split()
        for keyword in keywords:
            if keyword and keyword in user_message_lower:
                return row[1] or ""

    return ""


def log_unanswered_question(question: str, nlp_handled: bool = False):
    """
    Log an unanswered question, avoiding case-insensitive duplicates.
    nlp_handled=True means Gemini provided a response; False means total miss.
    """
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM unanswered WHERE LOWER(question) = ?",
        (question.lower(),)
    )
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO unanswered (question, nlp_handled) VALUES (?, ?)",
            (question, 1 if nlp_handled else 0)
        )
    conn.commit()
    conn.close()


def get_bot_response(user_input: str) -> str:
    """
    Response resolution order:
      1. SQLite keyword DB
      2. JSON fallback dataset
      3. Gemini NLP (logged to unanswered so admin can later train the DB)
    """
    if not user_input or not user_input.strip():
        return "Please say something."

    # --- 1. SQLite DB ---
    db_response = get_response_from_db(user_input)
    if db_response:
        return db_response

    # --- 2. JSON fallback ---
    user_keywords = set(user_input.lower().split())
    for entry in database:
        entry_keywords = set(entry.get("input", "").lower().split())
        if entry_keywords & user_keywords:
            return entry.get("response", "")

    # --- 3. NLP fallback (Gemini) ---
    # Log before calling NLP so admin sees it even if Gemini fails
    log_unanswered_question(user_input, nlp_handled=True)

    # Check cache first — avoid hitting Gemini API for repeat questions
    cache_key = user_input.lower().strip()
    if cache_key in _nlp_cache:
        return _nlp_cache[cache_key]

    nlp_response = get_nlp_response(user_input)
    _nlp_cache[cache_key] = nlp_response
    return nlp_response


# ---------------------------------------------------------------------------
# Chat routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "")
    response = get_bot_response(user_input)
    return jsonify({"response": response})


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM responses")
    responses_data = cursor.fetchall()
    cursor.execute("SELECT * FROM unanswered")
    unanswered_data = cursor.fetchall()
    conn.close()

    return render_template("admin.html", data=responses_data, unanswered=unanswered_data)


@app.route("/add", methods=["POST"])
def add():
    if not session.get("admin"):
        return redirect(url_for("login"))

    keywords = request.form.get("keywords", "")
    response = request.form.get("response", "")

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO responses (input, response) VALUES (?, ?)",
        (keywords.lower(), response)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/answer/<int:id>", methods=["POST"])
def answer(id):
    """Promote an unanswered question into the knowledge base."""
    if not session.get("admin"):
        return redirect(url_for("login"))

    keywords = request.form.get("keywords", "")
    response = request.form.get("response", "")

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO responses (input, response) VALUES (?, ?)",
        (keywords.lower(), response)
    )
    cursor.execute("DELETE FROM unanswered WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/delete_unanswered/<int:id>")
def delete_unanswered(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM unanswered WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM responses WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/edit/<int:id>")
def edit(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM responses WHERE id = ?", (id,))
    data = cursor.fetchone()
    conn.close()

    return render_template("edit.html", data=data)


@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    keywords = request.form["keywords"]
    response = request.form["response"]

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE responses SET input = ?, response = ? WHERE id = ?",
        (keywords.lower(), response, id)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/login")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True, use_reloader=False)
