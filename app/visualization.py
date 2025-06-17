import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from app.models import Movie, Rating, User, MovieType
import json
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_, text
import numpy as np
from app import db

class MovieVisualizer:
    def __init__(self, db):
        self.db = db

    def _row_to_dict(self, row):
        """将 SQLAlchemy Row 对象转换为字典"""
        return {key: getattr(row, key) for key in row._fields}

    def get_rating_distribution(self):
        """获取评分分布数据"""
        results = self.db.session.query(
            Movie.rating,
            func.count(Movie.id).label('count')
        ).filter(Movie.rating.isnot(None))\
         .group_by(Movie.rating)\
         .order_by(Movie.rating)\
         .all()
        
        # 确保有所有评分（1-5分）
        ratings = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for row in results:
            if row.rating in ratings:
                ratings[row.rating] = row.count
        
        return {
            'x': list(ratings.keys()),
            'y': list(ratings.values())
        }

    def get_genre_distribution(self):
        """获取电影类型分布数据"""
        results = self.db.session.query(
            MovieType.name,
            func.count(Movie.id).label('count')
        ).join(Movie.types)\
         .group_by(MovieType.name)\
         .having(func.count(Movie.id) > 0)\
         .order_by(func.count(Movie.id).desc())\
         .all()
        
        return {
            'labels': [row.name for row in results],
            'values': [row.count for row in results]
        }

    def get_year_distribution(self):
        """获取电影年份分布数据"""
        results = self.db.session.query(
            Movie.year,
            func.count(Movie.id).label('count')
        ).filter(Movie.year.isnot(None))\
         .group_by(Movie.year)\
         .order_by(Movie.year)\
         .all()
        
        # 填充缺失的年份
        if results:
            min_year = min(row.year for row in results)
            max_year = max(row.year for row in results)
            years = {year: 0 for year in range(min_year, max_year + 1)}
            for row in results:
                years[row.year] = row.count
            
            return {
                'x': list(years.keys()),
                'y': list(years.values())
            }
        return {'x': [], 'y': []}

    def get_rating_trend(self):
        """获取评分趋势"""
        results = self.db.session.query(
            func.date(Rating.created_at).label('date'),
            func.avg(Rating.rating).label('avg_rating')
        ).group_by(func.date(Rating.created_at))\
         .order_by(func.date(Rating.created_at))\
         .all()
        
        return {
            'x': [row.date.strftime('%Y-%m-%d') for row in results],
            'y': [float(row.avg_rating) if row.avg_rating else 0 for row in results]
        }

    def get_activity_heatmap(self):
        """获取用户活动时间分布热力图数据"""
        results = self.db.session.query(
            func.weekday(Rating.created_at).label('day'),
            func.hour(Rating.created_at).label('hour'),
            func.count(Rating.id).label('count')
        ).filter(Rating.created_at.isnot(None))\
         .group_by(
            func.weekday(Rating.created_at),
            func.hour(Rating.created_at)
        ).all()
        
        # 创建24小时的标签
        hours = list(range(24))
        # 创建7天的数据矩阵
        data = [[0] * 24 for _ in range(7)]
        
        # 填充数据
        for row in results:
            if row.day is not None and row.hour is not None:
                day_idx = int(row.day)
                hour = int(row.hour)
                if 0 <= day_idx < 7 and 0 <= hour < 24:
                    data[day_idx][hour] = row.count
            
        return {
            'x': hours,
            'y': data
        }

    def get_top_directors(self, limit=10):
        """获取评分最高的导演统计"""
        results = self.db.session.query(
            Movie.directors,
            func.count(Movie.id).label('movie_count'),
            func.avg(Movie.rating).label('avg_rating')
        ).filter(Movie.directors != '')\
         .group_by(Movie.directors)\
         .having(func.count(Movie.id) >= 3)\
         .order_by(func.avg(Movie.rating).desc())\
         .limit(limit)\
         .all()
        
        return {
            'x': [row.directors for row in results],
            'y': [float(row.avg_rating) if row.avg_rating else 0 for row in results]
        }

    def get_rating_correlation(self):
        """获取用户评分相关性矩阵"""
        # 获取评分数据
        ratings_data = self.db.session.query(
            Rating.user_id,
            Rating.movie_id,
            Rating.rating
        ).all()
        
        # 转换为DataFrame
        df = pd.DataFrame(ratings_data, columns=['user_id', 'movie_id', 'rating'])
        pivot = df.pivot(index='user_id', columns='movie_id', values='rating')
        
        # 计算相关性矩阵
        corr = pivot.corr()
        
        # 选择前10个电影的相关性
        top_movies = corr.iloc[:10, :10]
        
        # 获取这些电影的标题
        movie_ids = top_movies.index.tolist()
        movies = self.db.session.query(
            Movie.id, Movie.title
        ).filter(Movie.id.in_(movie_ids)).all()
        movie_titles = [m.title for m in movies]
        
        return {
            'z': top_movies.values.tolist(),
            'x': movie_titles,
            'y': movie_titles
        }

    def get_rating_distribution_plot(self):
        """获取评分分布图"""
        ratings = Rating.query.with_entities(Rating.rating).all()
        ratings_df = pd.DataFrame([r[0] for r in ratings], columns=['rating'])
        
        # 计算评分分布
        rating_counts = ratings_df['rating'].value_counts().sort_index()
        
        return {
            'x': rating_counts.index.tolist(),
            'y': rating_counts.values.tolist()
        }

    def get_genre_distribution_plot(self):
        """获取电影类型分布图"""
        movies = Movie.query.with_entities(Movie.genres).all()
        genres = []
        for movie in movies:
            if movie[0]:  # 确保genres不为空
                genres.extend([g.strip() for g in movie[0].split(',')])
        
        genre_df = pd.DataFrame(genres, columns=['genre'])
        genre_counts = genre_df['genre'].value_counts()
        
        return {
            'labels': genre_counts.index.tolist(),
            'values': genre_counts.values.tolist()
        }

    def get_year_distribution_plot(self):
        """获取电影年份分布图"""
        movies = Movie.query.with_entities(Movie.year).all()
        years_df = pd.DataFrame([y[0] for y in movies if y[0]], columns=['year'])
        
        # 计算年份分布
        year_counts = years_df['year'].value_counts().sort_index()
        
        return {
            'x': year_counts.index.tolist(),
            'y': year_counts.values.tolist()
        }

    def get_rating_trend_plot(self):
        """获取评分趋势图"""
        ratings = Rating.query.with_entities(
            Rating.created_at, Rating.rating
        ).order_by(Rating.created_at).all()
        
        ratings_df = pd.DataFrame(
            ratings,
            columns=['date', 'rating']
        )
        ratings_df['date'] = pd.to_datetime(ratings_df['date'])
        
        # 计算每日平均评分
        daily_ratings = ratings_df.groupby(
            ratings_df['date'].dt.date
        )['rating'].mean().reset_index()
        
        return {
            'x': [d.strftime('%Y-%m-%d') for d in daily_ratings['date']],
            'y': daily_ratings['rating'].tolist()
        }

    def get_user_activity_heatmap_plot(self):
        """获取用户活动热力图"""
        ratings = Rating.query.with_entities(
            Rating.created_at
        ).order_by(Rating.created_at).all()
        
        ratings_df = pd.DataFrame(
            ratings,
            columns=['datetime']
        )
        ratings_df['datetime'] = pd.to_datetime(ratings_df['datetime'])
        ratings_df['hour'] = ratings_df['datetime'].dt.hour
        ratings_df['day'] = ratings_df['datetime'].dt.day_name()
        
        # 计算每个时段的活动数量
        activity = ratings_df.groupby(['day', 'hour']).size().reset_index(name='count')
        
        # 设置星期几的顺序
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # 转换为散点图数据
        data = []
        for _, row in activity.iterrows():
            day_index = days_order.index(row['day'])
            data.append({
                'x': int(row['hour']),
                'y': day_index,
                'value': int(row['count'])
            })
        
        return {
            'data': data,
            'days': days_order
        }

    def get_top_directors_plot(self):
        """获取评分最高的导演统计图"""
        movies = Movie.query.with_entities(
            Movie.directors, Movie.rating
        ).filter(Movie.directors != '').all()
        
        movies_df = pd.DataFrame(
            movies,
            columns=['directors', 'rating']
        )
        
        # 计算每个导演的平均评分和电影数量
        director_stats = movies_df.groupby('directors').agg({
            'rating': ['mean', 'count']
        }).reset_index()
        director_stats.columns = ['directors', 'avg_rating', 'movie_count']
        
        # 筛选出电影数量大于1的导演
        director_stats = director_stats[director_stats['movie_count'] > 1]
        director_stats = director_stats.sort_values('avg_rating', ascending=False).head(10)
        
        return {
            'x': director_stats['directors'].tolist(),
            'y': director_stats['avg_rating'].round(2).tolist()
        }

    def get_rating_correlation_matrix_plot(self):
        """获取用户评分相关性矩阵"""
        # 获取评分数据
        ratings = Rating.query.with_entities(
            Rating.user_id, Rating.movie_id, Rating.rating
        ).all()
        
        # 转换为DataFrame
        ratings_df = pd.DataFrame(
            ratings,
            columns=['user_id', 'movie_id', 'rating']
        )
        
        # 创建用户-电影评分矩阵
        rating_matrix = ratings_df.pivot(
            index='user_id',
            columns='movie_id',
            values='rating'
        ).fillna(0)
        
        # 计算相关性矩阵
        corr_matrix = rating_matrix.corr()
        
        # 创建热力图
        fig = px.imshow(
            corr_matrix.values,
            title='用户评分相关性矩阵',
            labels=dict(x='电影ID', y='电影ID', color='相关系数'),
            color_continuous_scale='RdBu',
            template='plotly_white'
        )
        
        return json.loads(fig.to_json()) 