from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from io import BytesIO
from app.models import db, Movie, Rating, User, Favorite
from app.recommender import MovieRecommender
from app.visualization import MovieVisualizer
from app.douban_spider import DoubanSpider
import logging

logger = logging.getLogger(__name__)
movie_bp = Blueprint('movie', __name__, url_prefix='/movies')
visualizer = MovieVisualizer(db)

def get_recommender():
    """获取推荐器实例"""
    if not hasattr(current_app, 'recommender'):
        current_app.recommender = MovieRecommender()
    return current_app.recommender

@movie_bp.route('/')
@login_required
def movie_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    movies = Movie.query.paginate(page=page, per_page=per_page)
    
    # 获取用户收藏的电影ID列表
    favorite_movie_ids = {f.movie_id for f in current_user.favorites} if current_user.is_authenticated else set()
    
    return render_template('movie/list.html', 
                         movies=movies,
                         favorite_movie_ids=favorite_movie_ids)

@movie_bp.route('/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    user_rating = Rating.query.filter_by(
        user_id=current_user.id,
        movie_id=movie_id
    ).first()
    
    # 检查是否已收藏
    is_favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        movie_id=movie_id
    ).first() is not None
    
    similar_movies = get_recommender().get_similar_movies(movie_id)
    return render_template(
        'movie/detail.html',
        movie=movie,
        user_rating=user_rating,
        similar_movies=similar_movies,
        is_favorite=is_favorite
    )

@movie_bp.route('/rate', methods=['POST'])
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
        get_recommender().update_user_similarities()
        
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
    """获取个性化推荐"""
    recommender = get_recommender()
    recommendations = recommender.get_personalized_recommendations(current_user.id)
    return render_template('movie/recommendations.html', recommendations=recommendations)

@movie_bp.route('/movie/<int:movie_id>/similar')
@login_required
def similar_movies(movie_id):
    """获取相似电影推荐"""
    recommender = get_recommender()
    similar_movies = recommender.get_similar_movies(movie_id)
    return render_template('movie/similar_movies.html', 
                         similar_movies=similar_movies,
                         current_movie=Movie.query.get_or_404(movie_id))

@movie_bp.route('/recommendations/favorite-types')
@login_required
def favorite_type_recommendations():
    """基于用户收藏类型的推荐"""
    recommender = get_recommender()
    recommendations = recommender.get_favorite_type_recommendations(current_user.id)
    
    # 获取用户收藏的电影ID列表
    favorite_movie_ids = {f.movie_id for f in current_user.favorites}
    
    # 处理推荐结果，确保每个电影对象包含所需的所有属性
    movies = []
    for rec in recommendations:
        movie = rec['movie']
        movies.append({
            'id': movie.id,
            'title': movie.title,
            'year': movie.year,
            'rating': movie.rating,
            'types': [t.name for t in movie.types],
            'similarity_score': rec['similarity_score'],
            'similar_movie': rec['similar_movie'],
            'similarity_details': rec['similarity_details']
        })
    
    return render_template(
        'movie/favorite_type_recommendations.html',
        movies=movies,
        favorite_movie_ids=favorite_movie_ids,
        title="根据您的收藏推荐"
    )

@movie_bp.route('/visualizations')
@login_required
def visualizations():
    rating_dist = visualizer.get_rating_distribution()
    genre_dist = visualizer.get_genre_distribution()
    year_dist = visualizer.get_year_distribution()
    rating_trend = visualizer.get_rating_trend()
    activity_heatmap = visualizer.get_activity_heatmap()
    top_directors = visualizer.get_top_directors()
    rating_correlation = visualizer.get_rating_correlation_matrix_plot()
    
    return render_template('movie/visualizations.html',
                         rating_dist=rating_dist,
                         genre_dist=genre_dist,
                         year_dist=year_dist,
                         rating_trend=rating_trend,
                         activity_heatmap=activity_heatmap,
                         top_directors=top_directors,
                         rating_correlation=rating_correlation)

@movie_bp.route('/search')
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

@movie_bp.route('/poster/<int:movie_id>')
def movie_poster(movie_id):
    """从数据库中提供电影海报"""
    try:
        movie = Movie.query.get_or_404(movie_id)
        
        # 如果数据库中有海报数据，直接返回
        if movie.poster_data:
            return send_file(
                BytesIO(movie.poster_data),
                mimetype=movie.poster_mimetype or 'image/jpeg'
            )
        
        # 如果有海报URL，重定向到URL
        if movie.poster_url:
            return redirect(movie.poster_url)
            
        # 如果既没有海报数据也没有URL，返回默认海报
        return send_file(
            'static/images/default_poster.jpg',
            mimetype='image/jpeg'
        )
        
    except Exception as e:
        logger.error(f"Error serving poster for movie {movie_id}: {str(e)}")
        # 出错时返回默认海报
        return send_file(
            'static/images/default_poster.jpg',
            mimetype='image/jpeg'
        )

@movie_bp.route('/favorite/<int:movie_id>', methods=['POST'])
@login_required
def toggle_favorite(movie_id):
    """切换电影收藏状态"""
    try:
        logger.info(f"Processing favorite toggle for movie {movie_id} by user {current_user.id}")
        
        movie = Movie.query.get_or_404(movie_id)
        favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()

        if favorite:
            logger.info(f"Removing favorite for movie {movie_id}")
            db.session.delete(favorite)
            message = '已取消收藏'
            is_favorite = False
        else:
            logger.info(f"Adding favorite for movie {movie_id}")
            favorite = Favorite(user_id=current_user.id, movie_id=movie_id)
            db.session.add(favorite)
            message = '已添加到收藏'
            is_favorite = True

        db.session.commit()
        logger.info(f"Successfully processed favorite toggle: {message}")
        
        return jsonify({
            'success': True,
            'message': message,
            'is_favorite': is_favorite
        })

    except Exception as e:
        logger.error(f"Error toggling favorite for movie {movie_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '操作失败，请稍后重试'
        }), 500

@movie_bp.route('/favorites')
@login_required
def favorites():
    """显示用户收藏的电影列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    favorites = Favorite.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Favorite.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'movie/favorites.html',
        favorites=favorites,
        title="我的收藏"
    )

@movie_bp.route('/api/visualizations/rating-distribution')
@login_required
def rating_distribution_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_rating_distribution())

@movie_bp.route('/api/visualizations/genre-distribution')
@login_required
def genre_distribution_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_genre_distribution())

@movie_bp.route('/api/visualizations/year-distribution')
@login_required
def year_distribution_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_year_distribution())

@movie_bp.route('/api/visualizations/rating-trend')
@login_required
def rating_trend_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_rating_trend())

@movie_bp.route('/api/visualizations/activity-heatmap')
@login_required
def activity_heatmap_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_activity_heatmap())

@movie_bp.route('/api/visualizations/top-directors')
@login_required
def top_directors_api():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_top_directors()) 