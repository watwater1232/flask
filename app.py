import redis
from flask import Flask, jsonify, request
import uuid
from datetime import datetime, timedelta
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration (update with your Redis host)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # Use Render's internal hostname or 'localhost' for local
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # Set in Render dashboard if required

# Initialize Redis with error handling
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Connected to Redis successfully")
    use_redis = True
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None
    use_redis = False
    # In-memory fallback
    keys = {}
    subscriptions = {}

@app.route('/generate_key', methods=['POST'])
def generate_key():
    """Generate a license key with specified duration."""
    try:
        data = request.json
        duration = data.get('duration', 30)  # Default 30 days
        if not isinstance(duration, int) or duration <= 0:
            return jsonify({"status": "error", "message": "Invalid duration"}), 400
        
        key = f"GHST-{str(uuid.uuid4())[:8].upper()}"
        expiry = (datetime.now() + timedelta(days=duration)).timestamp()
        
        if use_redis:
            if redis_client is None:
                return jsonify({"status": "error", "message": "Redis unavailable"}), 500
            redis_client.hset('keys', key, expiry)
        else:
            keys[key] = expiry
            
        logger.info(f"Generated key: {key} with duration {duration} days")
        return jsonify({"status": "success", "key": key, "duration": duration})
    except Exception as e:
        logger.error(f"Error in generate_key: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/check', methods=['POST'])
def check_subscription():
    """Check if a subscription exists for the given HWID."""
    try:
        data = request.json
        hwid = data.get('hwid')
        if not hwid:
            return jsonify({"status": "error", "message": "HWID required"}), 400
        
        sub_data = None
        if use_redis:
            if redis_client is None:
                return jsonify({"status": "error", "message": "Redis unavailable"}), 500
            sub_data = redis_client.hget('subscriptions', hwid)
        else:
            sub_data = subscriptions.get(hwid)
            
        if not sub_data:
            return jsonify({"status": "error", "message": "No active subscription"}), 404
            
        expiry = float(sub_data)
        now = datetime.now().timestamp()
        if now > expiry:
            if use_redis:
                redis_client.hdel('subscriptions', hwid)
            else:
                subscriptions.pop(hwid, None)
            return jsonify({"status": "error", "message": "Subscription expired"}), 404
            
        days_left = int((expiry - now) / (24 * 3600))
        hours_left = int(((expiry - now) % (24 * 3600)) / 3600)
        logger.info(f"Checked subscription for HWID {hwid}: {days_left} days, {hours_left} hours left")
        return jsonify({"status": "success", "days_left": days_left, "hours_left": hours_left})
    except Exception as e:
        logger.error(f"Error in check_subscription: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/add_sub', methods=['POST'])
def add_subscription():
    """Activate a subscription using a license key."""
    try:
        data = request.json
        hwid = data.get('hwid')
        key = data.get('key')
        if not hwid or not key:
            return jsonify({"status": "error", "message": "HWID and key required"}), 400
            
        key_expiry = None
        if use_redis:
            if redis_client is None:
                return jsonify({"status": "error", "message": "Redis unavailable"}), 500
            key_expiry = redis_client.hget('keys', key)
        else:
            key_expiry = keys.get(key)
            
        if not key_expiry:
            return jsonify({"status": "error", "message": "Invalid or used key"}), 404
            
        if use_redis:
            redis_client.hset('subscriptions', hwid, key_expiry)
            redis_client.hdel('keys', key)
        else:
            subscriptions[hwid] = key_expiry
            keys.pop(key, None)
            
        logger.info(f"Activated subscription for HWID {hwid} with key {key}")
        return jsonify({"status": "success", "message": "Subscription activated"})
    except Exception as e:
        logger.error(f"Error in add_subscription: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/keys', methods=['GET'])
def list_keys():
    """List all license keys (for admin panel)."""
    try:
        if use_redis:
            if redis_client is None:
                return jsonify({"status": "error", "message": "Redis unavailable"}), 500
            keys_data = redis_client.hgetall('keys')
            decoded_keys = {key: float(value) for key, value in keys_data.items()}
        else:
            decoded_keys = {key: float(value) for key, value in keys.items()}
            
        formatted_keys = [
            {
                "key": key,
                "expiry": datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S'),
                "days_left": max(0, int((expiry - datetime.now().timestamp()) / (24 * 3600)))
            }
            for key, expiry in decoded_keys.items()
        ]
        logger.info("Retrieved list of keys")
        return jsonify({"status": "success", "keys": formatted_keys})
    except Exception as e:
        logger.error(f"Error in list_keys: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
