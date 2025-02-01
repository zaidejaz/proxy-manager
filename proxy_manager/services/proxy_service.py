import random
from datetime import datetime, timezone

import requests
from proxy_manager.models.proxy import Proxy
from proxy_manager import db

class ProxyService:
    @staticmethod
    def add_proxy(ip, port, username, password):
        proxy = Proxy.query.filter_by(ip=ip, port=port).first()
        if proxy:
            return None
        
        new_proxy = Proxy(
            ip=ip,
            port=port,
            username=username,
            password=password
        )
        db.session.add(new_proxy)
        db.session.commit()
        return new_proxy

    @staticmethod
    def import_proxies(content):
        added = 0
        for line in content.splitlines():
            if not line.strip():
                continue
            
            try:
                ip, port, username, password = line.strip().split(':')
                if ProxyService.add_proxy(ip, int(port), username, password):
                    added += 1
            except ValueError:
                continue
        
        return added

    @staticmethod
    def get_random_proxy():
        active_proxies = Proxy.query.filter_by(is_active=True).all()
        if not active_proxies:
            return None
        
        proxy = random.choice(active_proxies)
        proxy.last_used = datetime.now(timezone.utc)
        db.session.commit()
        return proxy

    @staticmethod
    def update_proxy_status(proxy_id, success):
        proxy = Proxy.query.get(proxy_id)
        if proxy:
            if success:
                proxy.success_count += 1
            else:
                proxy.failure_count += 1
            proxy.last_used = datetime.now(timezone.utc)
            db.session.commit()

    @staticmethod
    def make_request(url, method='GET', params=None, headers=None, data=None, 
                    max_retries=3, timeout=30):
        """
        Make a request through a proxy with retry logic
        """
        attempt = 0
        errors = []
        used_proxies = set()

        while attempt < max_retries:
            proxy = ProxyService.get_random_proxy()
            
            if not proxy or proxy.id in used_proxies:
                if len(used_proxies) >= Proxy.query.filter_by(is_active=True).count():
                    return {
                        "error": "All proxies exhausted",
                        "details": errors
                    }, 503
                continue

            used_proxies.add(proxy.id)
            
            try:
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }

                # Prepare request
                request_kwargs = {
                    'proxies': proxies,
                    'timeout': timeout,
                    'allow_redirects': True
                }

                if params:
                    request_kwargs['params'] = params
                if headers:
                    request_kwargs['headers'] = headers
                if data:
                    request_kwargs['data'] = data

                response = requests.request(method, url, **request_kwargs)
                
                # Update proxy stats
                ProxyService.update_proxy_status(proxy.id, success=True)
                
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "proxy_used": f"{proxy.ip}:{proxy.port}"
                }, response.status_code

            except (requests.RequestException, Exception) as e:
                ProxyService.update_proxy_status(proxy.id, success=False)
                errors.append(f"Proxy {proxy.ip}:{proxy.port} failed: {str(e)}")
                attempt += 1

        return {
            "error": "All retries failed",
            "details": errors
        }, 503