# proxy_manager/ui/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from proxy_manager.models.user import User
from proxy_manager.models.proxy import Proxy
from proxy_manager.services.proxy_service import ProxyService
from proxy_manager.ui.forms import LoginForm, ProxyForm
from proxy_manager import db

ui = Blueprint('ui', __name__)

@ui.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('ui.proxies'))
    return redirect(url_for('ui.login'))

@ui.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ui.proxies'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('ui.proxies'))
        flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@ui.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('ui.login'))

@ui.route('/proxies')
@login_required
def proxies():
    proxies = Proxy.query.all()
    form = ProxyForm()
    return render_template('proxies.html', proxies=proxies, form=form)

@ui.route('/proxies/add', methods=['POST'])
@login_required
def add_proxy():
    form = ProxyForm()
    if form.validate_on_submit():
        proxy = ProxyService.add_proxy(
            form.ip.data,
            form.port.data,
            form.username.data,
            form.password.data
        )
        if proxy:
            flash('Proxy added successfully', 'success')
        else:
            flash('Proxy already exists', 'error')
    return redirect(url_for('ui.proxies'))

@ui.route('/proxies/<int:proxy_id>/delete', methods=['POST'])
@login_required
def delete_proxy(proxy_id):
    proxy = Proxy.query.get_or_404(proxy_id)
    db.session.delete(proxy)
    db.session.commit()
    flash('Proxy deleted successfully', 'success')
    return redirect(url_for('ui.proxies'))

@ui.route('/proxies/<int:proxy_id>/toggle', methods=['POST'])
@login_required
def toggle_proxy(proxy_id):
    proxy = Proxy.query.get_or_404(proxy_id)
    proxy.is_active = not proxy.is_active
    db.session.commit()
    flash(f'Proxy {"activated" if proxy.is_active else "deactivated"} successfully', 'success')
    return redirect(url_for('ui.proxies'))

@ui.route('/import', methods=['GET', 'POST'])
@login_required
def import_proxies():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('ui.import_proxies'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('ui.import_proxies'))
        
        if not file.filename.endswith('.txt'):
            flash('Only .txt files are allowed', 'error')
            return redirect(url_for('ui.import_proxies'))
        
        content = file.read().decode('utf-8')
        added = ProxyService.import_proxies(content)
        flash(f'Successfully imported {added} proxies', 'success')
        return redirect(url_for('ui.proxies'))
    
    return render_template('import.html')