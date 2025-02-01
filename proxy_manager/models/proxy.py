# proxy_manager/models/proxy.py
from datetime import datetime, timezone
from proxy_manager import db

class Proxy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)
    last_used = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'is_active': self.is_active,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }