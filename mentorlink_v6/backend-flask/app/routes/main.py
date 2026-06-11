from flask import Blueprint, render_template, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.get('/')
def index():
    return redirect(url_for('main.login_page'))

@main_bp.get('/login')
def login_page():
    return render_template('login.html')

@main_bp.get('/register')
def register_page():
    return render_template('register.html')

@main_bp.get('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@main_bp.get('/annonces')
def annonces_page():
    return render_template('annonces.html')

@main_bp.get('/matching')
def matching_page():
    return render_template('matching.html')

@main_bp.get('/profil')
def profil_page():
    return render_template('profil.html')

@main_bp.get('/messages')
def messages_page():
    return render_template('messages.html')

@main_bp.get('/planning')
def planning_page():
    return render_template('planning.html')

@main_bp.get('/forgot-password')
def forgot_password_page():
    return render_template('forgot_password.html')

@main_bp.get('/reset-password/<token>')
def reset_password_page(token):
    return render_template('reset_password.html')
