import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """
    Configuration parameters for the app.
    Accessed as current_app.config['PARAMETER'] or current_app.config.get('PARAMETER')
    """
  
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'storefront.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'store-key-extremely-secret-just-'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    ITEMS_PER_PAGE = 10
    MIN_PASSWORD_LENGTH = 8
    MAX_UNITS_PER_PURCHASE = 10
    DEFAULT_SALES_MARGIN = 1.15     # 15% margin on top of the price at the warehouse.
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    SESSION_COOKIE_NAME = "storefront-cookie"
    APP_ID = "StoreFront-001"
    TOKEN_MAX_VALIDITY_DAYS = 60
    # DEFAULT_PROTOCOL = "http"   # "https"
    USE_HTTPS = True                # determines if to use HTTP or HTTPS
    PROD_ENV = False      # If False, SSL certificates will not be verified. Set to True for production.
    USE_PORT = 5050     # port number that the system will run on    