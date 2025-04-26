from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import Movie, Rating
from app import db
from app.analysis import get_user_rating_stats

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """主页路由，重定向到电影列表页面"""
    return redirect(url_for('movie.movie_list'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """用户仪表板"""
    # 获取用户评分统计
    stats = get_user_rating_stats(current_user.id)
    
    # 获取用户最近的评分记录
    recent_ratings = Rating.query.filter_by(user_id=current_user.id)\
        .order_by(Rating.created_at.desc())\
        .limit(5)\
        .all()
    
    # 获取最新电影
    latest_movies = Movie.query.order_by(Movie.created_at.desc()).limit(6).all()
    
    # 获取高分电影
    top_rated_movies = Movie.query.order_by(Movie.rating_avg.desc()).limit(6).all()
    
    return render_template('main/dashboard.html',
                         stats=stats,
                         recent_ratings=recent_ratings,
                         latest_movies=latest_movies,
                         top_rated_movies=top_rated_movies) 