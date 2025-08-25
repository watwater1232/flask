import os
import redis
from flask import Flask, request, jsonify
import datetime

# Создание экземпляра Flask-приложения
app = Flask(__name__)

# --- Подключение к Redis ---
try:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise ValueError("Переменная окружения REDIS_URL не установлена")
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    print("Успешное подключение к Redis.")
except Exception as e:
    print(f"Ошибка подключения к Redis: {e}")
    r = None

# --- Роуты API ---

@app.route('/check', methods=['POST'])
def check_subscription():
    """
    Проверяет статус подписки по HWID и возвращает оставшееся время.
    """
    data = request.json
    hwid = data.get('hwid')
    
    if not hwid:
        return jsonify({"status": "error", "message": "HWID не предоставлен"}), 400
    
    if r is None:
        return jsonify({"status": "error", "message": "База данных недоступна"}), 503

    end_date_str = r.get(hwid)
    
    if end_date_str:
        end_date = datetime.datetime.fromisoformat(end_date_str)
        now = datetime.datetime.now()
        if end_date > now:
            time_left = end_date - now
            days_left = time_left.days
            hours_left = time_left.seconds // 3600
            return jsonify({
                "status": "success",
                "message": "Подписка активна",
                "end_date": end_date_str,
                "days_left": days_left,
                "hours_left": hours_left
            })
        else:
            return jsonify({"status": "error", "message": "Подписка истекла"})
    
    return jsonify({"status": "error", "message": "Подписка не найдена"})

@app.route('/add_sub', methods=['POST'])
def add_sub():
    """
    Добавляет новую подписку на указанное количество дней с автоматическим удалением.
    """
    data = request.json
    hwid = data.get('hwid')
    days = data.get('days')
    
    if not hwid or not days:
        return jsonify({"status": "error", "message": "HWID или days не предоставлены"}), 400

    if r is None:
        return jsonify({"status": "error", "message": "База данных недоступна"}), 503
    
    try:
        days = int(days)
        end_date = datetime.datetime.now() + datetime.timedelta(days=days)
        end_date_str = end_date.isoformat()
        
        r.set(hwid, end_date_str)
        r.expire(hwid, days * 24 * 60 * 60)
        
        return jsonify({"status": "success", "message": "Подписка добавлена"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/remove_sub', methods=['POST'])
def remove_sub():
    """
    Удаляет подписку по HWID.
    """
    data = request.json
    hwid = data.get('hwid')
    if not hwid:
        return jsonify({"status": "error", "message": "HWID не предоставлен"}), 400

    if r is None:
        return jsonify({"status": "error", "message": "База данных недоступна"}), 503
    
    if r.delete(hwid) == 1:
        return jsonify({"status": "success", "message": "Подписка удалена"})
    else:
        return jsonify({"status": "error", "message": "Подписка не найдена"}), 404

@app.route('/subs_list', methods=['GET'])
def subs_list():
    """
    Возвращает список всех подписок.
    """
    if r is None:
        return jsonify({"status": "error", "message": "База данных недоступна"}), 503

    try:
        keys = r.keys('*')
        subs_data = []
        for hwid in keys:
            end_date_str = r.get(hwid)
            subs_data.append({
                "hwid": hwid,
                "end_date": end_date_str
            })
        return jsonify({"subs": subs_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
