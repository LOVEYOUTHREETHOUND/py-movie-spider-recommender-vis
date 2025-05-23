from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from io import BytesIO
from app.models import db, Movie, Rating, User
from app.recommender import MovieRecommender
from app.visualization import MovieVisualizer
from app.douban_spider import DoubanSpider
import logging

logger = logging.getLogger(__name__)
movie_bp = Blueprint('movie', __name__)
recommender = MovieRecommender()
visualizer = MovieVisualizer()

@movie_bp.route('/movies')
@login_required
def movie_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    movies = Movie.query.paginate(page=page, per_page=per_page)
    return render_template('movie/list.html', movies=movies)

@movie_bp.route('/movies/<int:movie_id>')
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

@movie_bp.route('/movies/rate', methods=['POST'])
@login_required
def rate_movie():
    try:
        movie_id = request.form.get('movie_id', type=int)
        rating = request.form.get('rating', type=float)
        comment = request.form.get('comment', '')
        
        if not movie_id or not rating:
            return jsonify({'error': 'Missing required fields'}), 400
            
        # 检查评分是否在有效范围内
        if not 1 <= rating <= 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
            
        # 查找或创建评分记录
        existing_rating = Rating.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()
        
        if existing_rating:
            existing_rating.rating = rating
            existing_rating.comment = comment
        else:
            new_rating = Rating(
                user_id=current_user.id,
                movie_id=movie_id,
                rating=rating,
                comment=comment
            )
            db.session.add(new_rating)
            
        db.session.commit()
        
        # 更新用户相似度
        recommender.update_user_similarities()
        
        return jsonify({
            'success': True,
            'message': 'Rating saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving rating: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save rating'}), 500

@movie_bp.route('/recommendations')
@login_required
def recommendations():
    recommended_movies = recommender.get_recommendations(current_user.id)
    return render_template('movie/recommendations.html', movies=recommended_movies)

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

@movie_bp.route('/movies/<int:movie_id>/poster')
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
        logger.error(f"Error serving poster for movie {movie_id}: {str(e)}")
        return '', 500 