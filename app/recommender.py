import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from app.models import Movie, Rating, Favorite, User, UserSimilarity, db, MovieType
import pandas as pd
from collections import defaultdict, Counter
import logging
from sqlalchemy import func, desc
from datetime import datetime

logger = logging.getLogger(__name__)

class MovieRecommender:
    def __init__(self):
        self.user_ratings = None
        self.similarity_matrix = None
        self.movie_indices = None

    def calculate_similarity(self, movie1, movie2):
        """计算两部电影的相似度"""
        similarity_details = {
            'type_similarity': 0,
            'year_similarity': 0,
            'rating_similarity': 0,
            'duration_similarity': 0,
            'language_similarity': 0
        }

        # 1. 类型相似度 (35%)
        movie1_types = set([t.name for t in movie1.types])
        movie2_types = set([t.name for t in movie2.types])
        if not movie1_types or not movie2_types:
            similarity_details['type_similarity'] = 0
        else:
            similarity_details['type_similarity'] = len(movie1_types & movie2_types) / len(movie1_types | movie2_types) * 100

        # 2. 年份相似度 (20%)
        try:
            year1 = int(movie1.year) if movie1.year else 0
            year2 = int(movie2.year) if movie2.year else 0
            if year1 and year2:
                year_diff = abs(year1 - year2)
                similarity_details['year_similarity'] = max(0, (1 - year_diff / 50)) * 100  # 50年差距为0相似度
            else:
                similarity_details['year_similarity'] = 0
        except:
            similarity_details['year_similarity'] = 0

        # 3. 评分相似度 (20%)
        try:
            rating1 = float(movie1.rating) if movie1.rating else 0
            rating2 = float(movie2.rating) if movie2.rating else 0
            if rating1 and rating2:
                rating_diff = abs(rating1 - rating2)
                similarity_details['rating_similarity'] = max(0, (1 - rating_diff / 10)) * 100  # 评分差10分为0相似度
            else:
                similarity_details['rating_similarity'] = 0
        except:
            similarity_details['rating_similarity'] = 0

        # 4. 时长相似度 (15%)
        try:
            duration1 = int(movie1.runtime) if movie1.runtime else 0
            duration2 = int(movie2.runtime) if movie2.runtime else 0
            if duration1 and duration2:
                duration_diff = abs(duration1 - duration2)
                similarity_details['duration_similarity'] = max(0, (1 - duration_diff / 180)) * 100  # 差3小时为0相似度
            else:
                similarity_details['duration_similarity'] = 0
        except:
            similarity_details['duration_similarity'] = 0

        # 5. 语言相似度 (10%)
        try:
            languages1 = set(movie1.languages.split(',')) if movie1.languages else set()
            languages2 = set(movie2.languages.split(',')) if movie2.languages else set()
            if languages1 and languages2:
                similarity_details['language_similarity'] = (len(languages1 & languages2) / len(languages1 | languages2)) * 100
            else:
                similarity_details['language_similarity'] = 0
        except:
            similarity_details['language_similarity'] = 0

        # 计算总相似度（加权平均）
        total_similarity = (
            0.35 * similarity_details['type_similarity'] +
            0.20 * similarity_details['year_similarity'] +
            0.20 * similarity_details['rating_similarity'] +
            0.15 * similarity_details['duration_similarity'] +
            0.10 * similarity_details['language_similarity']
        )

        return total_similarity, similarity_details

    def get_similar_movies(self, movie_id, limit=6):
        """获取与指定电影相似的电影"""
        target_movie = Movie.query.get(movie_id)
        if not target_movie:
            return []

        all_movies = Movie.query.filter(Movie.id != movie_id).all()

        similar_movies = []
        for movie in all_movies:
            similarity_score, details = self.calculate_similarity(target_movie, movie)
            if similarity_score > 0:
                similar_movies.append({
                    'id': movie.id,
                    'title': movie.title,
                    'year': movie.year,
                    'rating': movie.rating,
                    'types': [t.name for t in movie.types],
                    'similarity_score': round(similarity_score, 1),
                    'similarity_details': {
                        'type': round(details['type_similarity'], 1),
                        'year': round(details['year_similarity'], 1),
                        'rating': round(details['rating_similarity'], 1),
                        'duration': round(details['duration_similarity'], 1),
                        'language': round(details['language_similarity'], 1)
                    }
                })

        similar_movies.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar_movies[:limit]

    def get_favorite_type_recommendations(self, user_id, limit=20):
        """基于用户收藏电影的特征，推荐相似电影"""
        favorite_movies = Movie.query.join(Favorite).filter(Favorite.user_id == user_id).all()
        
        if not favorite_movies:
            return []

        all_movies = Movie.query.outerjoin(
            Favorite, 
            db.and_(
                Favorite.movie_id == Movie.id,
                Favorite.user_id == user_id
            )
        ).filter(Favorite.id == None).all()

        recommendations = []
        for movie in all_movies:
            max_similarity = 0
            most_similar_movie = None
            best_similarity_details = None
            
            for fav_movie in favorite_movies:
                similarity, details = self.calculate_similarity(movie, fav_movie)
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_movie = fav_movie
                    best_similarity_details = details

            if max_similarity > 0:
                recommendations.append({
                    'movie': movie,
                    'similarity_score': round(max_similarity, 1),
                    'similar_movie': most_similar_movie.title,
                    'similarity_details': {
                        'type': round(best_similarity_details['type_similarity'], 1),
                        'year': round(best_similarity_details['year_similarity'], 1),
                        'rating': round(best_similarity_details['rating_similarity'], 1),
                        'duration': round(best_similarity_details['duration_similarity'], 1),
                        'language': round(best_similarity_details['language_similarity'], 1)
                    }
                })

        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
        return recommendations[:limit] 