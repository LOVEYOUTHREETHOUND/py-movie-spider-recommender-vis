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
            Rating.rating,
            func.count(Rating.id).label('count')
        ).group_by(Rating.rating).all()
        return [self._row_to_dict(row) for row in results]

    def get_genre_distribution(self):
        """获取电影类型分布数据"""
        results = self.db.session.query(
            MovieType.name,
            func.count(Movie.id).label('count')
        ).join(Movie.types).group_by(MovieType.name).all()
        return [self._row_to_dict(row) for row in results]

    def get_year_distribution(self):
        """获取电影年份分布数据"""
        results = self.db.session.query(
            Movie.year,
            func.count(Movie.id).label('count')
        ).group_by(Movie.year).order_by(Movie.year).all()
        return [self._row_to_dict(row) for row in results]

    def get_rating_trend(self):
        """获取评分趋势"""
        results = self.db.session.query(
            Movie.year,
            func.avg(Movie.rating).label('avg_rating')
        ).group_by(Movie.year).order_by(Movie.year).all()
        return [
            {
                'year': row.year,
                'avg_rating': float(row.avg_rating) if row.avg_rating else 0
            }
            for row in results
        ]

    def get_activity_heatmap(self):
        """获取用户活动时间分布热力图数据"""
        results = self.db.session.query(
            func.dayofweek(Rating.created_at).label('day'),
            func.hour(Rating.created_at).label('hour'),
            func.count(Rating.id).label('count')
        ).group_by(
            func.dayofweek(Rating.created_at),
            func.hour(Rating.created_at)
        ).all()
        return [self._row_to_dict(row) for row in results]

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
        return [
            {
                'directors': row.directors,
                'movie_count': row.movie_count,
                'avg_rating': float(row.avg_rating) if row.avg_rating else 0
            }
            for row in results
        ]

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
        
        fig = px.histogram(
            ratings_df,
            x='rating',
            nbins=10,
            title='用户评分分布',
            labels={'rating': '评分', 'count': '数量'},
            template='plotly_white'
        )
        return json.loads(fig.to_json())

    def get_genre_distribution_plot(self):
        """获取电影类型分布图"""
        movies = Movie.query.with_entities(Movie.genres).all()
        genres = []
        for movie in movies:
            if movie[0]:  # 确保genres不为空
                genres.extend([g.strip() for g in movie[0].split(',')])
        
        genre_df = pd.DataFrame(genres, columns=['genre'])
        genre_counts = genre_df['genre'].value_counts()
        
        fig = px.pie(
            values=genre_counts.values,
            names=genre_counts.index,
            title='电影类型分布',
            template='plotly_white'
        )
        return json.loads(fig.to_json())

    def get_year_distribution_plot(self):
        """获取电影年份分布图"""
        movies = Movie.query.with_entities(Movie.year).all()
        years_df = pd.DataFrame([y[0] for y in movies], columns=['year'])
        
        fig = px.histogram(
            years_df,
            x='year',
            title='电影年份分布',
            labels={'year': '年份', 'count': '数量'},
            template='plotly_white'
        )
        return json.loads(fig.to_json())

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
        
        fig = px.line(
            daily_ratings,
            x='date',
            y='rating',
            title='每日平均评分趋势',
            labels={'date': '日期', 'rating': '平均评分'},
            template='plotly_white'
        )
        return json.loads(fig.to_json())

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
        
        # 创建透视表
        pivot_table = activity.pivot(
            index='day',
            columns='hour',
            values='count'
        ).fillna(0)
        
        # 设置星期几的顺序
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        pivot_table = pivot_table.reindex(days_order)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='Viridis'
        ))
        
        fig.update_layout(
            title='用户活动时间分布热力图',
            xaxis_title='小时',
            yaxis_title='星期',
            template='plotly_white'
        )
        
        return json.loads(fig.to_json())

    def get_top_directors_plot(self):
        """获取评分最高的导演统计图"""
        movies = Movie.query.with_entities(
            Movie.director, Movie.rating_avg
        ).filter(Movie.director != '').all()
        
        movies_df = pd.DataFrame(
            movies,
            columns=['director', 'rating']
        )
        
        # 计算每个导演的平均评分和电影数量
        director_stats = movies_df.groupby('director').agg({
            'rating': ['mean', 'count']
        }).reset_index()
        director_stats.columns = ['director', 'avg_rating', 'movie_count']
        
        # 筛选出电影数量大于1的导演
        director_stats = director_stats[director_stats['movie_count'] > 1]
        director_stats = director_stats.sort_values('avg_rating', ascending=False).head(10)
        
        fig = px.bar(
            director_stats,
            x='director',
            y='avg_rating',
            title='评分最高的导演 (至少2部电影)',
            labels={'director': '导演', 'avg_rating': '平均评分'},
            template='plotly_white'
        )
        
        return json.loads(fig.to_json())

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