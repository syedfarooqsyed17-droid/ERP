from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class IncidentLog(db.Model):
    __tablename__ = 'incident_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False) # e.g., ONLINE, CRASHED
    message = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "message": self.message
        }

class ERPRecord(db.Model):
    __tablename__ = 'erp_records'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    stock_qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)