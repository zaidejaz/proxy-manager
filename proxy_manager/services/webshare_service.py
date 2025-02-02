import requests
from datetime import datetime, timezone
import os
from proxy_manager import db
from proxy_manager.models.proxy import Proxy

class WebshareService:
    BASE_URL = "https://proxy.webshare.io/api"
    
    def __init__(self):
        self.api_key = os.getenv('WEBSHARE_API_KEY')
        self.headers = {
            "Authorization": f"Token {self.api_key}"
        }

    def fetch_all_proxies(self):
        """Fetch all proxies from Webshare API"""
        url = f"{self.BASE_URL}/v2/proxy/list/"
        params = {
            'mode': 'direct',
            'page_size': 100
        }
        
        all_proxies = []
        next_url = url

        while next_url:
            response = requests.get(next_url, headers=self.headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch proxies: {response.text}")
            
            data = response.json()
            all_proxies.extend(data['results'])
            next_url = data['next']
            
        return all_proxies

    def replace_proxy(self, webshare_id):
        """Request replacement for a specific proxy"""
        url = f"{self.BASE_URL}/v3/proxy/replace/{webshare_id}/"
        response = requests.post(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to replace proxy: {response.text}")
        
        return response.json()

    def sync_proxies(self):
        """Sync proxies from Webshare to local database"""
        webshare_proxies = self.fetch_all_proxies()
        
        existing_ids = {p.webshare_id for p in Proxy.query.all()}
        
        added = 0
        for proxy_data in webshare_proxies:
            if proxy_data['id'] not in existing_ids:
                proxy = Proxy(
                    webshare_id=proxy_data['id'],
                    ip=proxy_data['proxy_address'],
                    port=proxy_data['port'],
                    username=proxy_data['username'],
                    password=proxy_data['password'],
                    country_code=proxy_data['country_code'],
                    city_name=proxy_data['city_name'],
                    created_at=datetime.fromisoformat(proxy_data['created_at'])
                )
                db.session.add(proxy)
                added += 1
        
        db.session.commit()
        return added

    def check_and_replace_failing_proxies(self):
        """Check for proxies with high failure rates and replace them"""
        failing_proxies = Proxy.query.filter(
            Proxy.success_count + Proxy.failure_count > 10, 
            (Proxy.failure_count * 100 / (Proxy.success_count + Proxy.failure_count)) > 50 
        ).all()

        replaced = 0
        for proxy in failing_proxies:
            try:
                replacement = self.replace_proxy(proxy.webshare_id)
                if replacement['state'] == 'completed':
                    # Mark old proxy as inactive
                    proxy.is_active = False
                    db.session.commit()
                    replaced += 1
            except Exception as e:
                print(f"Failed to replace proxy {proxy.webshare_id}: {str(e)}")
                
        return replaced