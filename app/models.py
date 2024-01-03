from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin
from enum import Enum
from app import db


# Roles available for system users
class UserRole(Enum):
    ADMIN = "Administrator"
    SALES_MANAGER = "Sales Manager"
    READ_ONLY = "Auditor"
    CUSTOMER = "Customer"
    
    @classmethod
    def choices(cls):
        return [(choice, choice.value) for choice in cls]

    @classmethod
    def coerce(cls, item):
        return cls(int(item)) if not isinstance(item, cls) else item

    def __str__(self):
        return str(self.name)


   

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    given_name = db.Column(db.String(64))
    surname = db.Column(db.String(64))
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20))
    last_logon = db.Column(db.DateTime, default=datetime.utcnow)
    # role = db.Column(db.String(20))
    role = db.Column(db.Enum(UserRole), default=UserRole.READ_ONLY, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_sales_manager(self):
        return self.role == UserRole.SALES_MANAGER

    def is_read_only(self):
        return self.role == UserRole.READ_ONLY

    def is_customer(self):
        return self.role == UserRole.CUSTOMER
    

    def last_logon_as_str(self):
        return self.last_logon.strftime('%Y-%m-%d %H:%M:%S') if self.last_logon else 'Never logged in'
    
    def __repr__(self):
        return '<User {}>'.format(self.username)

class Purchases(db.Model):
    __tablename__ = 'purchase_history'
    id = db.Column(db.Integer, primary_key=True)        # unique purchase id
    purchase_code = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # customer who made the purchase
    salesitem_id = db.Column(db.Integer, db.ForeignKey('sales_items.id')) #
    salesitem_code = db.Column(db.String(32), nullable=False)    # unique code of the item
    salesitem_name = db.Column(db.String(128), nullable=False)    # item name
    salesitem_vendor_name = db.Column(db.String(128), nullable=False)    # name of the vendor
    purchase_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    salesitem_item_base_price = db.Column(db.Float)
    # salesitem_sales_margin =db.Column(db.Float)
    salesitem_purchase_price=db.Column(db.Float)
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Float)
    requires_sync = db.Column(db.Boolean, default=True)     # a flag indicating the transaction must be included to sync.       

    # Relationships - access customer and sales item data from purchase history table:
    # purchase_history_item.customer.name
    # backref allows to look tie purchases to sales items or customers: sales_item.purchase_history 
    customer = db.relationship('User', backref='purchase_history')
    sales_item = db.relationship('SalesItem', backref='purchase_history')


class SalesItem(db.Model):
    __tablename__ = 'sales_items'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)    # unique code of the item
    name = db.Column(db.String(128), nullable=False)    # item name
    description = db.Column(db.Text)    # detailed description of the item
    picture = db.Column(db.String(256))  # URL or path to the image
    price_per_unit = db.Column(db.Float)    # price per unit
    units_in_stock = db.Column(db.Integer)  # number of units in stock
    vendor_name = db.Column(db.String(128))    # name of the vendor
    # sales_margin = db.Column(db.Float)      # sales margin added
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    units_purchased = db.Column(db.Integer, default=0)              # number of units purchased so far
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # vendor = db.relationship('Vendor')


# API client privileges
class APIRole(Enum):
    READ_ONLY = "Read-only"
    READ_WRITE = "Read-write"
    WRITE_ONLY = "Write-only"

    def __str__(self):
        return str(self.name)


class APIToken(db.Model):
    
    __tablename__ = 'api_tokens'

    id = db.Column(db.Integer, primary_key=True)
    connection_name = db.Column(db.String(50))                      # just some name for the API token for the convenience of browsing
    token = db.Column(db.String(255), unique=True, nullable=False)
    # system_id = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    # role = db.Column(db.String(50))  # Role or access level
    revoked = db.Column(db.Boolean, default=False)
    last_used_at = db.Column(db.DateTime)
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'))      # user who created or updated the token

    def is_token_valid(self):
        # Check if the token is expired or revoked
        return not self.revoked and (self.expires_at is None or self.expires_at > datetime.utcnow())

    def toggle_token_status(self):
        self.revoked = not self.revoked
        return self.revoked

class ConnectionType(Enum):
    SYNC = "Sync"
    RESET = "Reset"

    def __str__(self):
        return str(self.name)


class SyncHistory(db.Model):
    
    __tablename__ = "sync_history"
    
    id = db.Column(db.Integer, primary_key=True)
    remote_name = db.Column(db.String(50))                  # name of the remote system, based on system_id field in API token.
    timestamp_start = db.Column(db.DateTime, default=datetime.utcnow)
    timestamp_end = db.Column(db.DateTime, default=datetime.utcnow)
    error_code = db.Column(db.Integer, default=0)                   # 0 means a successful session
    connection_type = db.Column(db.Enum(ConnectionType), default=ConnectionType.RESET)
    updates_received = db.Column(db.Integer, default=0)
    updates_sent = db.Column(db.Integer, default=0)
    