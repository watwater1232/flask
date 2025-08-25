import os
import sqlite3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

DB_FILE = "subs.db"

# --- Инициализация базы данных ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subs (
            hwid TEXT PRIMARY KEY,
            end_date TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# --- Проверка подписки ---
@app.route("/check", methods=["POST"])
def check_sub():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT end_date FROM subs WHERE hwid=?", (hwid,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"status": "no_sub"})

    end_date = datetime.strptime(row[0], "%Y-%m-%d").date()
    days_left = (end_date - datetime.today().date()).days
    if days_left < 0:
        return jsonify({"status": "expired"})

    return jsonify({"status": "active", "days_left": days_left})

# --- Добавление / продление подписки ---
@app.route("/add_sub", methods=["POST"])
def add_sub():
    data = request.json
    hwid = data.get("hwid")
    days = data.get("days")
    if not hwid or not days:
        return jsonify({"status": "error", "message": "Missing HWID or days"}), 400

    try:
        days = int(days)
        end_date = (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    except:
        return jsonify({"status": "error", "message": "Invalid days value"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO subs (hwid, end_date) VALUES (?, ?) "
        "ON CONFLICT(hwid) DO UPDATE SET end_date=excluded.end_date",
        (hwid, end_date)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": f"Subscription added/extended for {hwid}"})

# --- Удаление подписки ---
@app.route("/remove_sub", methods=["POST"])
def remove_sub():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subs WHERE hwid=?", (hwid,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"status": "success", "message": f"Subscription removed for {hwid}"})

# --- Получение списка всех подписок ---
@app.route("/subs_list", methods=["GET"])
def subs_list():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT hwid, end_date FROM subs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    subs = [{"hwid": hwid, "end_date": end_date} for hwid, end_date in rows]
    return {"subs": subs}

# --- Главная страница для теста ---
@app.route("/")
def index():
    return "Flask HWID Server is running!"

# --- Запуск ---
if __name__ == "__main__":
    init_db()
    # на Render нужно использовать порт из переменной окружения PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
