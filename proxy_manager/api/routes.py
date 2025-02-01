from flask import Blueprint, request, jsonify
from proxy_manager.services.proxy_service import ProxyService
from proxy_manager.api.auth import require_api_key, require_auth

api = Blueprint('api', __name__)

@api.route('/proxy', methods=['GET'])
@require_auth
def get_proxy():
    proxy = ProxyService.get_random_proxy()
    if not proxy:
        return jsonify({"error": "No proxies available"}), 404
    
    return jsonify(proxy.to_dict())

@api.route('/proxy/import', methods=['POST'])
@require_auth
def import_proxies():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    content = file.read().decode('utf-8')
    
    added = ProxyService.import_proxies(content)
    return jsonify({"message": f"Successfully imported {added} proxies"})

@api.route('/proxy/request', methods=['GET', 'POST'])
@require_api_key
def proxy_request():
    """
    Proxy endpoint that forwards requests through rotating proxies
    """
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({"error": "URL parameter is required"}), 400

    method = request.args.get('method', 'GET').upper()
    if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']:
        return jsonify({"error": "Invalid HTTP method"}), 400

    params = dict(request.args)
    params.pop('url', None)
    params.pop('method', None)

    headers = {k: v for k, v in request.headers.items()
              if k.lower() not in ['host', 'x-api-key']}

    data = request.get_data() if method in ['POST', 'PUT', 'PATCH'] else None

    response_data, status_code = ProxyService.make_request(
        url=target_url,
        method=method,
        params=params,
        headers=headers,
        data=data,
        max_retries=3,
        timeout=30
    )

    return jsonify(response_data), status_code