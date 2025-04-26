from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 验证输入
        if not username or not email or not password:
            flash('请填写所有必填字段', 'error')
            return render_template('auth/register.html')
            
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'error')
            return render_template('auth/register.html')
            
        try:
            # 创建新用户
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            db.session.rollback()
            flash('注册失败，请稍后重试', 'error')
            
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('movie.movie_list'))
        else:
            flash('用户名或密码错误', 'error')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            current_user.email = request.form.get('email', current_user.email)
            
            new_password = request.form.get('new_password')
            if new_password:
                current_user.password_hash = generate_password_hash(new_password)
                
            db.session.commit()
            flash('个人资料已更新', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            db.session.rollback()
            flash('更新失败，请稍后重试', 'error')
            
    return render_template('auth/edit_profile.html') 