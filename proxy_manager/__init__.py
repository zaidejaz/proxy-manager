from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import threading
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.pool import QueuePool

load_dotenv()

csrf = CSRFProtect()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
init_lock = threading.Lock()    

def create_app():
    app = Flask(__name__, 
                template_folder='ui/templates',
                static_folder='ui/static')
    
    # Ensure data directory exists
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    os.makedirs(data_dir, exist_ok=True)
    
    # Database configuration with absolute path
    database_path = os.path.join(data_dir, 'proxies.db')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Set SQLAlchemy connection pool settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,  # Increase from default (5)
        'pool_timeout': 30,  # Seconds before timing out
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'max_overflow': 10  # Allow additional connections beyond pool_size
    }
    
    # Initialize extensions
    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'ui.login'
    
    # Register blueprints
    from proxy_manager.api.routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    from proxy_manager.ui.routes import ui
    app.register_blueprint(ui)
    
    # Create database and admin user with lock
    with init_lock:
        with app.app_context():
            db.create_all()
            
            # Create admin user
            from proxy_manager.models.user import User
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'changeme')
            
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                try:
                    admin = User(username=admin_username, password=admin_password)
                    db.session.add(admin)
                    db.session.commit()
                    print(f"Admin user created: {admin_username}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error creating admin user: {str(e)}")
    
    return app