from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from io import BytesIO
from app.models import db, Movie, Rating, User
from app.recommender import MovieRecommender
from app.visualization import MovieVisualizer
from app.douban_spider import DoubanSpider
import logging
from datetime import datetime
from sqlalchemy import func

logger = logging.getLogger(__name__)
movie_bp = Blueprint('movie', __name__)
recommender = MovieRecommender()
visualizer = MovieVisualizer()

@movie_bp.route('/')
@login_required
def movie_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    movies = Movie.query.paginate(page=page, per_page=per_page)
    return render_template('movie/list.html', movies=movies)

@movie_bp.route('/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    user_rating = Rating.query.filter_by(
        user_id=current_user.id,
        movie_id=movie_id
    ).first()
    
    similar_movies = recommender.get_similar_movies(movie_id)
    return render_template(
        'movie/detail.html',
        movie=movie,
        user_rating=user_rating,
        similar_movies=similar_movies
    )

@movie_bp.route('/rate/<int:movie_id>', methods=['POST'])
@login_required
def rate_movie(movie_id):
    """用户对电影进行评分"""
    try:
        data = request.get_json()
        current_app.logger.info(f"Received rating request data: {data}")
        
        if not data or 'rating' not in data:
            return jsonify({
                "success": False,
                "message": "请提供评分",
                "data": None
            }), 400

        # 获取评分值并确保是整数
        try:
            rating = int(data['rating'])
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "无效的评分值",
                "data": None
            }), 400

        # 验证评分范围
        if not 1 <= rating <= 5:
            return jsonify({
                "success": False,
                "message": "评分必须在1-5之间",
                "data": None
            }), 400

        # 获取电影信息
        movie = Movie.query.get_or_404(movie_id)
        
        # 检查是否已经评分
        existing_rating = Rating.query.filter_by(
            user_id=current_user.id, movie_id=movie_id
        ).first()

        if existing_rating:
            # 更新评分
            existing_rating.rating = rating
            existing_rating.updated_at = datetime.utcnow()
        else:
            # 创建新评分
            new_rating = Rating(
                user_id=current_user.id,
                movie_id=movie_id,
                rating=rating
            )
            db.session.add(new_rating)
        
        db.session.commit()

        # 计算新的平均分
        avg_rating = db.session.query(func.avg(Rating.rating)).filter_by(movie_id=movie_id).scalar() or 0
        rating_count = db.session.query(func.count(Rating.id)).filter_by(movie_id=movie_id).scalar() or 0

        return jsonify({
            "success": True,
            "message": "评分成功",
            "data": {
                "avg_rating": round(float(avg_rating), 1),
                "rating_count": rating_count
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in rate_movie: {str(e)}")
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "评分失败，请稍后重试",
            "data": None
        }), 500

@movie_bp.route('/recommendations')
@login_required
def recommendations():
    recommended_movies = recommender.get_recommendations(current_user.id)
    return render_template('movie/recommendations.html', movies=recommended_movies)

@movie_bp.route('/user_ratings')
@login_required
def user_ratings():
    """用户评分记录"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # 获取用户的所有评分记录
    ratings = Rating.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Rating.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'movie/user_ratings.html',
        ratings=ratings,
        title="我的评分"
    )

@movie_bp.route('/visualizations')
@login_required
def visualizations():
    rating_dist = visualizer.get_rating_distribution()
    genre_dist = visualizer.get_genre_distribution()
    year_dist = visualizer.get_year_distribution()
    rating_trend = visualizer.get_rating_trend()
    activity_heatmap = visualizer.get_user_activity_heatmap()
    top_directors = visualizer.get_top_directors()
    rating_correlation = visualizer.get_rating_correlation_matrix()
    
    return render_template('movie/visualizations.html',
                         rating_dist=rating_dist,
                         genre_dist=genre_dist,
                         year_dist=year_dist,
                         rating_trend=rating_trend,
                         activity_heatmap=activity_heatmap,
                         top_directors=top_directors,
                         rating_correlation=rating_correlation)

@movie_bp.route('/movies/search')
@login_required
def search_movies():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('movie.movie_list'))
        
    movies = Movie.query.filter(
        Movie.title.ilike(f'%{query}%') |
        Movie.director.ilike(f'%{query}%') |
        Movie.cast.ilike(f'%{query}%')
    ).all()
    
    return render_template('movie/search_results.html',
                         movies=movies,
                         query=query)

@movie_bp.route('/<int:movie_id>/poster')
def movie_poster(movie_id):
    """从数据库中提供电影海报"""
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        # 如果数据库中存储了海报数据和MIME类型
        if movie.poster_data and movie.poster_mimetype:
            return send_file(
                BytesIO(movie.poster_data),
                mimetype=movie.poster_mimetype,
                as_attachment=False
            )
        
        # 如果有海报URL，重定向到外部URL
        if movie.poster_url:
            return redirect(movie.poster_url)
            
        # 如果既没有海报数据也没有URL，返回404
        logger.warning(f"Movie {movie_id} has no poster data or URL")
        return '', 404
        
    except Exception as e:
        logger.error(f"Error serving movie poster: {str(e)}")
        return '', 500

@movie_bp.route('/api/visualizations/rating-heatmap')
@login_required
def get_rating_heatmap():
    """获取评分热力图数据"""
    try:
        activity_heatmap = visualizer.get_user_activity_heatmap()
        return jsonify({
            "success": True,
            "data": activity_heatmap
        })
    except Exception as e:
        logger.error(f"Error generating rating heatmap: {str(e)}")
        return jsonify({
            "success": False,
            "message": "获取热力图数据失败",
            "error": str(e)
        }), 500 