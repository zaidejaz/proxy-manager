from flask import Blueprint, request, jsonify
from proxy_manager.services.proxy_service import ProxyService
from proxy_manager.api.auth import require_api_key, require_auth

api = Blueprint('api', __name__)

@api.route('/proxy', methods=['GET'])
@require_auth
def get_proxy():
    proxy_type = request.args.get('type')
    proxy = ProxyService.get_random_proxy(proxy_type)
    if not proxy:
        return jsonify({"error": "No proxies available"}), 404
    
    return jsonify(proxy.to_dict())

@api.route('/proxies', methods=['GET'])
@require_api_key
def list_proxies():
    """
    Get a list of all active proxies.
    
    Args:
        type (str, optional): Filter by proxy type (datacenter or residential)
    
    Returns:
        JSON response with a list of proxies
    """
    proxy_type = request.args.get('type')
    active_proxies = ProxyService.get_proxies(proxy_type)
    
    if not active_proxies:
        return jsonify({"error": "No proxies available"}), 404
    
    proxies_list = [proxy.to_dict() for proxy in active_proxies]
    
    return jsonify({
        "count": len(proxies_list),
        "proxies": proxies_list
    })

@api.route('/proxy/import', methods=['POST'])
@require_auth
def import_proxies():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    content = file.read().decode('utf-8')
    
    proxy_type = request.form.get('proxy_type', 'datacenter')
    if proxy_type not in ['datacenter', 'residential']:
        return jsonify({"error": "Invalid proxy type"}), 400
    
    added = ProxyService.import_proxies(content, proxy_type)
    return jsonify({"message": f"Successfully imported {added} proxies"})

@api.route('/proxy/request', methods=['GET', 'POST'])
@require_api_key
def proxy_request():
    """
    Proxy endpoint that forwards requests through rotating proxies
    
    Query Parameters:
        url (str): Target URL to request
        method (str): HTTP method to use (default: GET)
        
    Headers:
        X-Proxy-Type (str, optional): Type of proxy to use ('datacenter' or 'residential', default: 'residential').
                                     If no proxies of specified type are available, will fall back to the other type
                                     only if the specific type wasn't explicitly requested.
    
    Returns:
        Proxied response including status code, headers, content, and proxy information
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
    
    # Get proxy type from headers if specified, default to residential
    proxy_type = request.headers.get('X-Proxy-Type')
    if not proxy_type:
        proxy_type = 'residential'  # Default to residential
    elif proxy_type.lower() not in ['datacenter', 'residential']:
        return jsonify({"error": "Invalid proxy type. Must be 'datacenter' or 'residential'"}), 400
    else:
        # Ensure consistent casing
        proxy_type = proxy_type.lower()
    
    print(f"API request received. URL: {target_url}, Method: {method}, Requested proxy type: {proxy_type}")
    
    data = request.get_data() if method in ['POST', 'PUT', 'PATCH'] else None

    response_data, status_code = ProxyService.make_request(
        url=target_url,
        method=method,
        params=params,
        headers=headers,
        data=data,
        max_retries=3,
        timeout=30,
        proxy_type=proxy_type
    )

    # If we have a note in the response about proxy type fallback, log it
    if 'note' in response_data:
        print(f"Proxy type note: {response_data['note']}")

    return jsonify(response_data), status_code