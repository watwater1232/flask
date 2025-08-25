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
            end_date TEXT,
            blocked BOOLEAN DEFAULT FALSE
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
    cursor.execute("SELECT end_date, blocked FROM subs WHERE hwid=%s", (hwid,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"status": "no_sub"})

    end_date_str, blocked = row
    if blocked:
        return jsonify({"status": "blocked", "message": "Вы заблокированы"})

    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    days_left = (end_date - datetime.today().date()).days
    if days_left < 0:
        return jsonify({"status": "expired"})

    return jsonify({"status": "active", "days_left": days_left})

@app.route("/subs_list", methods=["GET"])
def subs_list():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT hwid, end_date, blocked FROM subs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    subs = [{"hwid": r[0], "end_date": r[1], "blocked": r[2]} for r in rows]
    return jsonify({"subs": subs})

@app.route("/add_sub", methods=["POST"])
def add_sub():
    data = request.json
    hwid = data.get("hwid")
    days = data.get("days")
    if not hwid or not days:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT end_date FROM subs WHERE hwid=%s", (hwid,))
    row = cursor.fetchone()
    if row:
        end_date = datetime.strptime(row[0], "%Y-%m-%d").date()
        end_date = max(end_date, datetime.today().date()) + timedelta(days=int(days))
        cursor.execute("UPDATE subs SET end_date=%s WHERE hwid=%s", (end_date.strftime("%Y-%m-%d"), hwid))
    else:
        end_date = datetime.today().date() + timedelta(days=int(days))
        cursor.execute("INSERT INTO subs (hwid, end_date) VALUES (%s, %s)", (hwid, end_date.strftime("%Y-%m-%d")))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": f"Подписка для {hwid} обновлена до {end_date}."})

@app.route("/remove_sub", methods=["POST"])
def remove_sub():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subs WHERE hwid=%s", (hwid,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": f"Подписка для {hwid} удалена."})

@app.route("/block_user", methods=["POST"])
def block_user():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE subs SET blocked=TRUE WHERE hwid=%s", (hwid,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": f"{hwid} заблокирован."})

@app.route("/unblock_user", methods=["POST"])
def unblock_user():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"status": "error", "message": "Missing HWID"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE subs SET blocked=FALSE WHERE hwid=%s", (hwid,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success", "message": f"{hwid} разблокирован."})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5050)
