from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required, current_user
from app.models import Movie, MovieType, Rating, db
from sqlalchemy import func, text, extract
from datetime import datetime, timedelta
import os
from app.visualization import MovieVisualizer
import pandas as pd
import numpy as np
from collections import defaultdict
import io
from flask import current_app

# 创建蓝图
movie_bp = Blueprint('movie', __name__)

@movie_bp.route('/type/<type_name>')
@login_required
def movie_list_by_type(type_name):
    """按类型显示电影列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # 获取电影类型
    movie_type = MovieType.query.filter_by(name=type_name).first_or_404()
    
    # 获取该类型的所有电影
    movies = Movie.query.join(
        Movie.types
    ).filter(
        MovieType.id == movie_type.id
    ).order_by(
        Movie.rating.desc()
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取所有电影类型供导航使用
    all_types = MovieType.query.order_by(MovieType.name).all()
    
    return render_template(
        'movie/list.html',
        movies=movies,
        current_type=movie_type,
        all_types=all_types,
        title=f"{type_name}电影"
    )

@movie_bp.route('/')
@login_required
def movie_list():
    """显示所有电影列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # 获取所有电影，按评分降序排序
    movies = Movie.query.order_by(Movie.rating.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # 获取所有电影类型供导航使用
    all_types = MovieType.query.order_by(MovieType.name).all()
    
    return render_template(
        'movie/list.html',
        movies=movies,
        current_type=None,
        all_types=all_types,
        title="所有电影"
    )

@movie_bp.route('/movie/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    """显示电影详情"""
    movie = Movie.query.get_or_404(movie_id)
    # 获取用户对这部电影的评分
    user_rating = None
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(
            user_id=current_user.id,
            movie_id=movie_id
        ).first()
    return render_template('movie/detail.html', movie=movie, user_rating=user_rating)

@movie_bp.route('/poster/<int:movie_id>')
def movie_poster(movie_id):
    """获取电影海报"""
    movie = Movie.query.get_or_404(movie_id)
    if movie.poster_data:
        return send_file(
            io.BytesIO(movie.poster_data),
            mimetype='image/jpeg'
        )
    # 如果海报不存在，返回默认图片
    default_poster = os.path.join(os.path.dirname(__file__), 'static', 'images', 'default_poster.jpg')
    return send_file(default_poster)

@movie_bp.route('/search')
@login_required
def search():
    """搜索电影"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    if query:
        # 在标题中搜索
        movies = Movie.query.filter(Movie.title.ilike(f'%{query}%')).paginate(
            page=page, per_page=per_page, error_out=False
        )
    else:
        movies = Movie.query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'movie/search.html',
        movies=movies,
        query=query,
        title=f"搜索：{query}" if query else "搜索电影"
    )

@movie_bp.route('/recommendations')
@login_required
def recommendations():
    """电影推荐"""
    # 获取用户评分过的电影
    user_ratings = Rating.query.filter_by(user_id=current_user.id).all()
    rated_movie_ids = [r.movie_id for r in user_ratings]
    
    # 获取未评分的高分电影
    recommended_movies = Movie.query.filter(
        ~Movie.id.in_(rated_movie_ids)
    ).order_by(Movie.rating.desc()).limit(12).all()
    
    return render_template(
        'movie/recommendations.html',
        movies=recommended_movies,
        title="为您推荐"
    )

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

@movie_bp.route('/visualizations')
@login_required
def visualizations():
    return render_template('movie/visualizations.html')

@movie_bp.route('/api/visualizations/rating-distribution')
@login_required
def rating_distribution():
    ratings = db.session.query(
        func.round(Movie.rating).label('rating'),
        func.count(Movie.id).label('count')
    ).group_by(func.round(Movie.rating)).all()
    
    data = {
        'x': [float(r.rating) for r in ratings],
        'y': [r.count for r in ratings]
    }
    return jsonify(data)

@movie_bp.route('/api/visualizations/genre-distribution')
@login_required
def genre_distribution():
    movie_types = db.session.query(
        MovieType.name,
        func.count(movie_types.c.movie_id).label('count')
    ).join(movie_types).group_by(MovieType.name).all()
    
    data = {
        'x': [t.name for t in movie_types],
        'y': [t.count for t in movie_types]
    }
    return jsonify(data)

@movie_bp.route('/api/visualizations/year-distribution')
@login_required
def year_distribution():
    years = db.session.query(
        extract('year', Movie.release_date).label('year'),
        func.count(Movie.id).label('count')
    ).group_by('year').order_by('year').all()
    
    data = {
        'x': [int(y.year) for y in years if y.year],
        'y': [y.count for y in years if y.year]
    }
    return jsonify(data)

@movie_bp.route('/api/visualizations/rating-trend')
@login_required
def rating_trend():
    days = request.args.get('days', default=30, type=int)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    ratings = db.session.query(
        func.date(Rating.created_at).label('date'),
        func.avg(Rating.rating).label('avg_rating')
    ).filter(Rating.created_at.between(start_date, end_date)
    ).group_by('date').order_by('date').all()
    
    data = {
        'x': [r.date.strftime('%Y-%m-%d') for r in ratings],
        'y': [float(r.avg_rating) for r in ratings]
    }
    return jsonify(data)

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

@movie_bp.route('/api/visualizations/top-directors')
@login_required
def top_directors():
    limit = request.args.get('limit', default=10, type=int)
    
    # Split directors string and unnest
    directors = db.session.query(
        Movie.directors,
        Movie.rating
    ).filter(Movie.directors != None).all()
    
    # Process directors and their ratings
    director_ratings = defaultdict(list)
    for movie in directors:
        if movie.directors:
            for director in movie.directors.split(','):
                director = director.strip()
                if director and movie.rating:
                    director_ratings[director].append(float(movie.rating))
    
    # Calculate average ratings
    avg_ratings = {
        director: np.mean(ratings)
        for director, ratings in director_ratings.items()
        if len(ratings) >= 3  # Only include directors with at least 3 movies
    }
    
    # Sort by average rating and get top N
    top_directors = sorted(
        avg_ratings.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]
    
    data = {
        'x': [d[0] for d in top_directors],
        'y': [float(d[1]) for d in top_directors]
    }
    return jsonify(data)

@movie_bp.route('/api/visualizations/rating-correlation')
@login_required
def rating_correlation():
    visualizer = MovieVisualizer(db)
    return jsonify(visualizer.get_rating_correlation())

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