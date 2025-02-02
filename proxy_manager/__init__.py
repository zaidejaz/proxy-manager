from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, 
                template_folder='ui/templates',
                static_folder='ui/static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'ui.login'
    
    # Register blueprints
    from proxy_manager.api.routes import api
    app.register_blueprint(api, url_prefix='/api')
    
    from proxy_manager.ui.routes import ui
    app.register_blueprint(ui)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        from proxy_manager.models.user import User
        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if admin_username and admin_password:
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                admin = User(username=admin_username, password=admin_password)
                db.session.add(admin)
                db.session.commit()
                print(f"Admin user '{admin_username}' created successfully")
            else:
                # Update password if it changed
                admin.set_password(admin_password)
                db.session.commit()
                print(f"Admin user '{admin_username}' password updated")
    
    return app