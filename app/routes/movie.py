from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from io import BytesIO
from app.models import db, Movie, Rating, User, Favorite, MovieType
from app.recommender import MovieRecommender
from app.visualization import MovieVisualizer
from app.douban_spider import DoubanSpider
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

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
    
    # 获取所有电影类型
    all_types = MovieType.query.all()
    
    # 获取用户收藏的电影ID列表
    favorite_movie_ids = {f.movie_id for f in current_user.favorites} if current_user.is_authenticated else set()
    
    return render_template('movie/list.html', 
                         movies=movies,
                         favorite_movie_ids=favorite_movie_ids,
                         all_types=all_types,
                         current_type=None,
                         title="全部电影")

@movie_bp.route('/data_analysis')
@login_required
def data_analysis():
    """电影数据分析页面"""
    visualizer = MovieVisualizer(db)
    data = {
        'rating_distribution': visualizer.get_rating_distribution(),
        'genre_distribution': visualizer.get_genre_distribution(),
        'year_distribution': visualizer.get_year_distribution(),
        'rating_trend': visualizer.get_rating_trend(),
        'activity_heatmap': visualizer.get_activity_heatmap(),
        'top_directors': visualizer.get_top_directors()
    }
    return render_template('movie/data_analysis.html', **data)

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

@movie_bp.route('/search')
@login_required
def search_movies():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('movie.movie_list'))
        
    movies = Movie.query.filter(
        Movie.title.ilike(f'%{query}%') |
        Movie.directors.ilike(f'%{query}%') |
        Movie.actors.ilike(f'%{query}%')
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

@movie_bp.route('/api/visualizations/rating-heatmap')
@login_required
def rating_heatmap():
    """获取电影评分热力图数据"""
    try:
        # 获取所有电影数据和类型
        movies = db.session.query(
            Movie.title,
            Movie.year,
            Movie.rating,
            MovieType.name.label('type_name')
        ).join(
            Movie.types
        ).filter(
            Movie.rating.isnot(None),
            Movie.year.isnot(None),
            Movie.rating >= 0,
            Movie.rating <= 10
        ).order_by(
            Movie.year.asc(),
            MovieType.name.asc()
        ).all()

        # 获取年份范围和类型列表
        years = sorted(list(set(movie.year for movie in movies if movie.year)))
        types = sorted(list(set(movie.type_name for movie in movies if movie.type_name)))

        # 创建年份分组（每4年一组）
        year_groups = []
        current_group = []
        for year in years:
            current_group.append(year)
            if len(current_group) == 4:
                year_groups.append(current_group)
                current_group = []
        if current_group:  # 处理剩余的年份
            year_groups.append(current_group)

        # 创建评分矩阵
        heatmap_data = []
        movie_details = {}  # 存储每个单元格的电影详情

        for type_name in types:
            type_index = types.index(type_name)
            for group_index, year_group in enumerate(year_groups):
                # 获取该年份组和类型的所有电影
                group_movies = [
                    movie for movie in movies 
                    if movie.year in year_group and movie.type_name == type_name
                ]
                
                if group_movies:
                    # 计算平均评分
                    avg_rating = sum(movie.rating for movie in group_movies) / len(group_movies)
                    
                    # 存储该单元格的电影详情
                    cell_key = f"{group_index}_{type_index}"
                    movie_details[cell_key] = {
                        'years': year_group,
                        'avg_rating': round(avg_rating, 1),
                        'movies': [
                            {
                                'title': movie.title,
                                'year': movie.year,
                                'rating': round(float(movie.rating), 1)
                            }
                            for movie in group_movies
                        ]
                    }
                    
                    heatmap_data.append([
                        group_index,
                        type_index,
                        avg_rating
                    ])

        # 创建年份标签（显示年份范围）
        year_labels = [
            f"{group[0]}-{group[-1]}"
            for group in year_groups
        ]

        return jsonify({
            'years': year_labels,
            'types': types,
            'movies': heatmap_data,
            'details': movie_details
        })
    except Exception as e:
        current_app.logger.error(f"Error in rating_heatmap: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@movie_bp.route('/type/<type_name>')
@login_required
def movie_list_by_type(type_name):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 获取指定类型
    movie_type = MovieType.query.filter_by(name=type_name).first_or_404()
    
    # 获取该类型的所有电影
    movies = Movie.query.filter(Movie.types.contains(movie_type)).paginate(page=page, per_page=per_page)
    
    # 获取所有电影类型
    all_types = MovieType.query.all()
    
    # 获取用户收藏的电影ID列表
    favorite_movie_ids = {f.movie_id for f in current_user.favorites} if current_user.is_authenticated else set()
    
    return render_template('movie/list.html',
                         movies=movies,
                         favorite_movie_ids=favorite_movie_ids,
                         all_types=all_types,
                         current_type=movie_type,
                         title=f"{type_name}电影")

# 数据可视化API
@movie_bp.route('/api/visualizations/rating-distribution')
@login_required
def api_rating_distribution():
    data = visualizer.get_rating_distribution()
    # ECharts需要x:评分, y:数量
    x = [d['rating'] for d in data]
    y = [d['count'] for d in data]
    return jsonify({'x': x, 'y': y})

@movie_bp.route('/api/visualizations/genre-distribution')
@login_required
def api_genre_distribution():
    data = visualizer.get_genre_distribution()
    x = [d['name'] for d in data]
    y = [d['count'] for d in data]
    return jsonify({'x': x, 'y': y})

@movie_bp.route('/api/visualizations/year-distribution')
@login_required
def api_year_distribution():
    data = visualizer.get_year_distribution()
    x = [d['year'] for d in data]
    y = [d['count'] for d in data]
    return jsonify({'x': x, 'y': y})

@movie_bp.route('/api/visualizations/rating-trend')
@login_required
def api_rating_trend():
    data = visualizer.get_rating_trend()
    x = [d['year'] for d in data]
    y = [d['avg_rating'] for d in data]
    return jsonify({'x': x, 'y': y})

# @movie_bp.route('/api/visualizations/activity-heatmap')
# @login_required
# def api_activity_heatmap():
#     data = visualizer.get_activity_heatmap()
#     # 直接返回 [{day, hour, count}, ...]
#     return jsonify(data)

@movie_bp.route('/api/visualizations/top-directors')
@login_required
def api_top_directors():
    data = visualizer.get_top_directors()
    x = [d['directors'] for d in data]
    y = [d['avg_rating'] for d in data]
    return jsonify({'x': x, 'y': y})

@movie_bp.route('/api/visualizations/activity-heatmap')
@login_required
def activity_heatmap():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    activities = db.session.query(
        func.dayofweek(Rating.created_at).label('day'),
        func.hour(Rating.created_at).label('hour'),
        func.count(Rating.id).label('count')
    ).filter(Rating.created_at.between(start_date, end_date)
    ).group_by('day', 'hour').all()
    
    # Initialize 7x24 matrix with zeros
    heatmap = [[0 for _ in range(24)] for _ in range(7)]
    
    # Fill in the counts
    for activity in activities:
        day_idx = activity.day - 1  # 1-based to 0-based
        hour = activity.hour
        heatmap[day_idx][hour] = activity.count
    
    data = {
        'x': list(range(24)),  # Hours
        'y': heatmap  # Activity counts per day and hour
    }
    return jsonify(data)