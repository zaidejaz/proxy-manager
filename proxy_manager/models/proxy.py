from datetime import datetime, timezone
from proxy_manager import db

class Proxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    webshare_id = db.Column(db.String(50), unique=True) 
    ip = db.Column(db.String(50), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    last_used = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    country_code = db.Column(db.String(2))  
    city_name = db.Column(db.String(100))   
    created_at = db.Column(db.DateTime(timezone=True)) 

    @property
    def failure_rate(self):
        total = self.success_count + self.failure_count
        if total == 0:
            return 0
        return (self.failure_count / total) * 100

    def to_dict(self):
        return {
            'id': self.id,
            'webshare_id': self.webshare_id,
            'ip': self.ip,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'is_active': self.is_active,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'failure_rate': self.failure_rate,
            'country_code': self.country_code,
            'city_name': self.city_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }