from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
DB_PATH = "subs.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subs (
                hwid TEXT PRIMARY KEY,
                end_date TEXT
            )
        """)

@app.route("/check", methods=["POST"])
def check_sub():
    data = request.json
    hwid = data.get("hwid")

    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT end_date FROM subs WHERE hwid=?", (hwid,))
        row = cur.fetchone()

    if not row:
        return jsonify({"status": "no_sub"})

    end_date = datetime.strptime(row[0], "%Y-%m-%d").date()
    days_left = (end_date - datetime.today().date()).days

    if days_left < 0:
        return jsonify({"status": "expired"})
    
    return jsonify({"status": "active", "days_left": days_left})

# --- Эндпоинты для админки ---

@app.route("/admin/add", methods=["POST"])
def add_sub_api():
    data = request.json
    hwid = data.get("hwid")
    days = data.get("days")

    if not hwid or not days:
        return jsonify({"status": "error", "message": "Missing HWID or days"}), 400

    try:
        days = int(days)
        end_date = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO subs (hwid, end_date) VALUES (?, ?)", (hwid, end_date))
        return jsonify({"status": "success", "message": "Subscription added/extended"})
    except ValueError:
        return jsonify({"status": "error", "message": "Days must be an integer"}), 400

@app.route("/admin/remove", methods=["POST"])
def remove_sub_api():
    data = request.json
    hwid = data.get("hwid")

    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM subs WHERE hwid=?", (hwid,))
    return jsonify({"status": "success", "message": "Subscription removed"})

@app.route("/admin/list", methods=["GET"])
def get_subs_api():
    with sqlite3.connect(DB_PATH) as conn:
        subs = conn.execute("SELECT hwid, end_date FROM subs").fetchall()
    subs_list = [{"hwid": row[0], "end_date": row[1]} for row in subs]
    return jsonify(subs_list)

# Эта строка нужна для локального тестирования. На PythonAnywhere она не нужна.
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050)