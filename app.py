import os
import redis
from flask import Flask, request, jsonify
import datetime

# Создание экземпляра Flask-приложения
app = Flask(__name__)

# --- Подключение к Redis ---
# Render автоматически создает переменную окружения REDIS_URL.
# Мы считываем ее, чтобы получить URL для подключения.
try:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    # Используем decode_responses=True, чтобы получать строки, а не байты
    r = redis.from_url(redis_url, decode_responses=True)
    # Проверка соединения с Redis
    r.ping()
    print("Successfully connected to Redis.")
except Exception as e:
    print(f"Error connecting to Redis: {e}")
    # Можно использовать локальное хранилище для отладки, но на Render это не будет работать
    r = None

# --- Роуты API ---

@app.route('/check_sub', methods=['POST'])
def check_sub():
    """
    Проверяет, активна ли подписка по HWID.
    """
    data = request.json
    hwid = data.get('hwid')
    
    if not hwid:
        return jsonify({"status": "error", "message": "HWID not provided"}), 400
    
    if r is None:
        return jsonify({"status": "error", "message": "Database not available"}), 503

    # Получаем дату окончания подписки из Redis
    end_date_str = r.get(hwid)
    
    if end_date_str:
        end_date = datetime.datetime.fromisoformat(end_date_str)
        if end_date > datetime.datetime.now():
            return jsonify({"status": "success", "message": "Subscription active"})
    
    return jsonify({"status": "error", "message": "Subscription not found or expired"})

@app.route('/add_sub', methods=['POST'])
def add_sub():
    """
    Добавляет новую подписку на указанное количество дней.
    """
    data = request.json
    hwid = data.get('hwid')
    days = data.get('days')
    
    if not hwid or not days:
        return jsonify({"status": "error", "message": "HWID or days not provided"}), 400

    if r is None:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    
    try:
        days = int(days)
        # Рассчитываем дату окончания
        end_date = datetime.datetime.now() + datetime.timedelta(days=days)
        # Преобразуем дату в строку для хранения
        end_date_str = end_date.isoformat()
        
        # Сохраняем в Redis: ключ - HWID, значение - дата окончания
        r.set(hwid, end_date_str)
        return jsonify({"status": "success", "message": "Subscription added"})
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
        return jsonify({"status": "error", "message": "HWID not provided"}), 400

    if r is None:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    
    # Удаляем ключ (HWID) из Redis
    if r.delete(hwid) == 1:
        return jsonify({"status": "success", "message": "Subscription removed"})
    else:
        return jsonify({"status": "error", "message": "Subscription not found"}), 404

@app.route('/subs_list', methods=['GET'])
def subs_list():
    """
    Возвращает список всех подписок.
    """
    if r is None:
        return jsonify({"status": "error", "message": "Database not available"}), 503

    try:
        # Получаем все ключи (HWID) из Redis
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
    # Запуск сервера
    app.run(debug=True)
