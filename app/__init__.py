from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
import base64

# 初始化扩展，但不传入 app
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    
    # 配置应用
    app.config.from_object(config_class)

    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # 设置登录视图
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'

    # 注册 b64encode 过滤器
    def b64encode_filter(data):
        if data is None:
            return ''
        return base64.b64encode(data).decode('utf-8')
    
    app.jinja_env.filters['b64encode'] = b64encode_filter

    # 注册蓝图
    from app.routes.movie import movie_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(movie_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 添加根路由
    @app.route('/')
    def index():
        return redirect(url_for('movie.movie_list'))

    # 配置日志
    if not app.debug and not app.testing:
        # 确保日志文件夹存在
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # 设置日志文件，限制大小为10MB，保留10个备份
        file_handler = RotatingFileHandler(
            'logs/movie_recommender.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Movie Recommender startup')

    return app

# 创建一个默认应用实例，使用Config类
app = create_app() 