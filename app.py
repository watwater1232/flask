import os
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Получаем строку подключения из переменных окружения Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
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

@app.route("/check", methods=["POST"])
def check_sub():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT end_date FROM subs WHERE hwid=%s", (hwid,))
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

# Эта строка нужна для локального тестирования.
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050)
