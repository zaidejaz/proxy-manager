from functools import wraps
from flask import request, jsonify
from werkzeug.security import check_password_hash
import os

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return jsonify({"message": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated

def check_auth(username, password):
    return username == os.getenv('ADMIN_USERNAME') and \
           check_password_hash(os.getenv('ADMIN_PASSWORD_HASH'), password)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('API_KEY'):
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated