import random
from datetime import datetime, timezone
import base64
import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning
from proxy_manager.models.proxy import Proxy
from proxy_manager import db
from sqlalchemy import func

# Suppress only the specific InsecureRequestWarning, not all warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

class ProxyService:
    @staticmethod
    def add_proxy(ip, port, username, password, proxy_type='datacenter'):
        proxy = Proxy.query.filter_by(ip=ip, port=port).first()
        if proxy:
            return None
        
        new_proxy = Proxy(
            ip=ip,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type
        )
        db.session.add(new_proxy)
        db.session.commit()
        return new_proxy

    @staticmethod
    def import_proxies(content, proxy_type='datacenter'):
        added = 0
        for line in content.splitlines():
            if not line.strip():
                continue
            
            try:
                ip, port, username, password = line.strip().split(':')
                if ProxyService.add_proxy(ip, int(port), username, password, proxy_type):
                    added += 1
            except ValueError:
                continue
        
        return added

    @staticmethod
    def get_random_proxy(proxy_type=None):
        """
        Get a random active proxy of the specified type
        """
        try:
            # Build the base query
            query = Proxy.query.filter_by(is_active=True)
            
            # Filter by proxy type if specified
            if proxy_type:
                query = query.filter_by(proxy_type=proxy_type)
            
            # Count the total number of matching proxies
            count = query.count()
            
            if count == 0:
                return None
            
            # Get a random offset
            random_offset = random.randint(0, count - 1)
            
            # Use offset to get a single random proxy
            proxy = query.offset(random_offset).limit(1).first()
            
            if proxy:
                # Update last_used timestamp
                proxy.last_used = datetime.now(timezone.utc)
                db.session.commit()
                
            return proxy
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def check_proxy_type_availability(proxy_type):
        """
        Check if proxies of a certain type are available
        
        Args:
            proxy_type (str): Type of proxy to check ('datacenter' or 'residential')
            
        Returns:
            bool: True if proxies of the specified type are available, False otherwise
        """
        try:
            return Proxy.query.filter_by(is_active=True, proxy_type=proxy_type).count() > 0
        except Exception as e:
            return False

    @staticmethod
    def get_proxies(proxy_type=None):
        try:
            query = Proxy.query.filter_by(is_active=True)
            
            if proxy_type:
                query = query.filter_by(proxy_type=proxy_type)
                
            active_proxies = query.all()
            if not active_proxies:
                return None
            
            return active_proxies
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def update_proxy_status(proxy_id, success):
        try:
            proxy = Proxy.query.get(proxy_id)
            if proxy:
                if success:
                    proxy.success_count += 1
                else:
                    proxy.failure_count += 1
                proxy.last_used = datetime.now(timezone.utc)
                db.session.commit()
        except Exception as e:
            db.session.rollback()

    @classmethod
    def get_all_proxies(cls):
        """
        Get all active proxies formatted as dictionaries
        
        Returns:
            list: List of dictionaries containing proxy information
        """
        try:
            active_proxies = Proxy.query.filter_by(is_active=True).all()
            if not active_proxies:
                return []
            
            proxies_list = []
            for proxy in active_proxies:
                proxy_dict = {
                    'id': proxy.id,
                    'ip': proxy.ip,
                    'port': proxy.port,
                    'username': proxy.username,
                    'password': proxy.password,
                    'type': proxy.proxy_type,
                    'last_used': proxy.last_used.isoformat() if proxy.last_used else None,
                    'success_count': proxy.success_count,
                    'failure_count': proxy.failure_count
                }
                
                # Only add country if it exists as an attribute
                if hasattr(proxy, 'country'):
                    proxy_dict['country'] = proxy.country
                else:
                    proxy_dict['country'] = None
                
                proxies_list.append(proxy_dict)
            
            return proxies_list
        except Exception as e:
            db.session.rollback()
            return []
    
    @classmethod
    def format_proxy_url(cls, proxy):
        """
        Format a proxy dictionary into a URL for requests
        
        Args:
            proxy (dict): Proxy information dictionary
            
        Returns:
            str: Formatted proxy URL
        """
        if not proxy:
            return None
            
        # Ensure all required fields are present
        required_fields = ['username', 'password', 'ip', 'port']
        for field in required_fields:
            if field not in proxy or proxy[field] is None:
                return None
                
        return f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
    
    @classmethod
    def record_proxy_usage(cls, proxy_id, url, method, status_code, error=None):
        """
        Record proxy usage for analytics
        
        Args:
            proxy_id (int): ID of the proxy used
            url (str): Target URL
            method (str): HTTP method
            status_code (int): Response status code, 0 if error
            error (str, optional): Error message if request failed
        """
        if proxy_id is None:
            print("Warning: Attempted to record proxy usage without a valid proxy ID")
            return
            
        try:
            proxy = Proxy.query.get(proxy_id)
            if proxy:
                if status_code > 0:
                    proxy.success_count += 1
                else:
                    proxy.failure_count += 1
                    
                proxy.last_used = datetime.now(timezone.utc)
                db.session.commit()
                
                # Add analytics logging here if needed in the future
            else:
                print(f"Warning: No proxy found with ID {proxy_id} when recording usage")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error recording proxy usage: {str(e)}")
            
    @classmethod
    def make_request(cls, url, method='GET', params=None, headers=None, data=None, max_retries=3, timeout=30, proxy_type=None):
        """
        Make a request to the given URL through a proxy
        
        Args:
            url (str): Target URL
            method (str): HTTP method (default: GET)
            params (dict): URL parameters
            headers (dict): HTTP headers
            data (bytes): Request body data
            max_retries (int): Maximum number of retries
            timeout (int): Request timeout in seconds
            proxy_type (str): Type of proxy to use ('datacenter' or 'residential', default: 'residential')
            
        Returns:
            tuple: (response_data, status_code)
        """
        proxies = cls.get_all_proxies()
        if not proxies:
            return {"error": "No proxies available"}, 500

        # If proxy_type is not specified, default to residential
        if not proxy_type:
            proxy_type = 'residential'
        
        # Select proxies of the requested type
        requested_type_proxies = [p for p in proxies if p.get('type') == proxy_type]
        other_type = 'datacenter' if proxy_type == 'residential' else 'residential'
        other_type_proxies = [p for p in proxies if p.get('type') == other_type]
        
        # Determine which proxy type to use based on the request and availability
        proxies_to_use = requested_type_proxies
        note = None
        
        # Strict mode: If user explicitly requests datacenter, only use datacenter
        explicitly_requested_datacenter = proxy_type == 'datacenter'
        
        # If no proxies of requested type, and if user didn't explicitly request datacenter proxies,
        # or if they requested residential (which is our preference anyway), we can fall back
        if not proxies_to_use and (not explicitly_requested_datacenter or proxy_type == 'residential'):
            proxies_to_use = other_type_proxies
            if proxies_to_use:  # Only add a note if we're actually falling back
                note = f"No {proxy_type} proxies available, using {other_type} proxies instead"
                print(f"PROXY FALLBACK: {note}")
        
        # If still no proxies to use, return error
        if not proxies_to_use:
            err_msg = f"No {proxy_type} proxies available" + (
                " and fallback to other proxy types is not enabled for this request" 
                if explicitly_requested_datacenter else ""
            )
            print(f"PROXY ERROR: {err_msg}")
            return {"error": err_msg, "details": []}, 503
        
        # Shuffle to avoid using the same proxy repeatedly
        random.shuffle(proxies_to_use)
        
        attempt = 0
        errors = []
        proxy_used = None
        
        while attempt < max_retries:
            attempt += 1
            if not proxies_to_use:
                break
            
            proxy = proxies_to_use.pop(0)
            proxy_used = proxy
            
            proxy_url = cls.format_proxy_url(proxy)
            
            # Skip invalid proxies
            if not proxy_url:
                print(f"Skipping proxy with invalid format: {proxy.get('ip')}:{proxy.get('port')}")
                continue
                
            print(f"Attempt {attempt}: Using {proxy.get('type', 'unknown')} proxy {proxy.get('ip')}:{proxy.get('port')} for {method} {url}")
            
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    proxies={'http': proxy_url, 'https': proxy_url},
                    timeout=timeout,
                    verify=False
                )
                
                # Log the response status
                print(f"Proxy response: {response.status_code} from {proxy.get('type', 'unknown')} proxy {proxy.get('ip')}:{proxy.get('port')}")
                
                # Record successful proxy usage for analytics
                cls.record_proxy_usage(proxy['id'], url, method, response.status_code)
                
                # Use original response format for compatibility
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "proxy_used": f"{proxy.get('ip')}:{proxy.get('port')}"
                }
                
                # Add additional fields for enhanced functionality but maintain backward compatibility
                response_data["proxy_type"] = proxy.get('type')
                
                if note:
                    response_data["note"] = note
                
                return response_data, response.status_code
                
            except Exception as e:
                error_message = str(e)
                print(f"Proxy error: {error_message} with {proxy.get('type', 'unknown')} proxy {proxy.get('ip')}:{proxy.get('port')}")
                errors.append(f"Proxy {proxy.get('ip')}:{proxy.get('port')} failed: {str(e)}")
                
                # Record failed proxy usage
                cls.record_proxy_usage(proxy['id'], url, method, 0, error=error_message)
        
        # If we've exhausted the requested proxy type and it's not a strict datacenter request,
        # try with the other proxy type as a last resort
        if attempt >= max_retries and proxy_type and not explicitly_requested_datacenter:
            other_type_proxies = [p for p in cls.get_all_proxies() if p.get('type') == other_type]
            
            if other_type_proxies and not proxies_to_use:
                fallback_msg = f"All {proxy_type} proxies failed, attempting with {other_type} proxies as last resort"
                print(f"PROXY LAST RESORT: {fallback_msg}")
                
                # Try one proxy of the other type
                proxy = random.choice(other_type_proxies)
                proxy_url = cls.format_proxy_url(proxy)
                
                # Skip invalid proxies
                if not proxy_url:
                    print(f"Skipping last resort proxy with invalid format: {proxy.get('ip')}:{proxy.get('port')}")
                    return {
                        "error": "All retries failed",
                        "details": errors
                    }, 503
                
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers,
                        data=data,
                        proxies={'http': proxy_url, 'https': proxy_url},
                        timeout=timeout,
                        verify=False
                    )
                    
                    # Log the response status
                    print(f"Last resort proxy response: {response.status_code} from {proxy.get('type', 'unknown')} proxy {proxy.get('ip')}:{proxy.get('port')}")
                    
                    # Record successful proxy usage for analytics
                    cls.record_proxy_usage(proxy['id'], url, method, response.status_code)
                    
                    # Use original response format for compatibility
                    response_data = {
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "content": response.text,
                        "proxy_used": f"{proxy.get('ip')}:{proxy.get('port')}"
                    }
                    
                    # Add additional fields but maintain backward compatibility
                    response_data["proxy_type"] = proxy.get('type')
                    response_data["note"] = fallback_msg
                    
                    return response_data, response.status_code
                    
                except Exception as e:
                    error_message = str(e)
                    print(f"Last resort proxy error: {error_message} with {proxy.get('type', 'unknown')} proxy {proxy.get('ip')}:{proxy.get('port')}")
                    errors.append(f"Proxy {proxy.get('ip')}:{proxy.get('port')} failed: {str(e)}")
                    
                    # Record failed proxy usage
                    cls.record_proxy_usage(proxy['id'], url, method, 0, error=error_message)
        
        # If all else fails, return error in the original format
        return {
            "error": "All retries failed",
            "details": errors
        }, 503