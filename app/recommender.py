import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.models import Movie, Rating, UserSimilarity, db
import pandas as pd
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class MovieRecommender:
    def __init__(self):
        self.min_ratings = 5  # 用户最少需要评价的电影数
        self.n_similar_users = 10  # 选择最相似的用户数量
        self.n_recommendations = 12  # 推荐电影数量

    def _get_user_movie_matrix(self):
        """获取用户-电影评分矩阵"""
        ratings = Rating.query.all()
        df = pd.DataFrame([(r.user_id, r.movie_id, r.rating) for r in ratings],
                         columns=['user_id', 'movie_id', 'rating'])
        return df.pivot(index='user_id', columns='movie_id', values='rating').fillna(0)

    def _calculate_user_similarity(self, user_matrix):
        """计算用户相似度"""
        similarity_matrix = cosine_similarity(user_matrix)
        return pd.DataFrame(
            similarity_matrix,
            index=user_matrix.index,
            columns=user_matrix.index
        )

    def update_user_similarities(self):
        """更新所有用户间的相似度"""
        try:
            # 获取用户-电影矩阵
            user_matrix = self._get_user_movie_matrix()
            if user_matrix.empty:
                logger.warning("No ratings found in database")
                return

            # 计算相似度
            similarity_df = self._calculate_user_similarity(user_matrix)

            # 清除旧的相似度数据
            UserSimilarity.query.delete()

            # 保存新的相似度数据
            for user1 in similarity_df.index:
                for user2 in similarity_df.columns:
                    if user1 < user2:  # 只保存上三角矩阵，避免重复
                        similarity = similarity_df.loc[user1, user2]
                        user_sim = UserSimilarity(
                            user_id1=user1,
                            user_id2=user2,
                            similarity=float(similarity)
                        )
                        db.session.add(user_sim)

            db.session.commit()
            logger.info("Successfully updated user similarities")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user similarities: {str(e)}")

    def get_similar_users(self, user_id):
        """获取与指定用户最相似的用户"""
        similar_users = []
        
        # 查找用户作为user_id1的相似度记录
        similarities1 = UserSimilarity.query.filter_by(user_id1=user_id).all()
        for sim in similarities1:
            similar_users.append((sim.user_id2, sim.similarity))
            
        # 查找用户作为user_id2的相似度记录
        similarities2 = UserSimilarity.query.filter_by(user_id2=user_id).all()
        for sim in similarities2:
            similar_users.append((sim.user_id1, sim.similarity))
            
        # 按相似度排序
        similar_users.sort(key=lambda x: x[1], reverse=True)
        return similar_users[:self.n_similar_users]

    def get_recommendations(self, user_id):
        """为指定用户生成推荐"""
        try:
            # 获取用户已评价的电影
            user_ratings = Rating.query.filter_by(user_id=user_id).all()
            if len(user_ratings) < self.min_ratings:
                return self._get_popular_movies()

            rated_movie_ids = {r.movie_id for r in user_ratings}
            similar_users = self.get_similar_users(user_id)
            
            # 收集相似用户的评分
            movie_scores = defaultdict(list)
            for similar_user_id, similarity in similar_users:
                if similarity <= 0:
                    continue
                    
                similar_user_ratings = Rating.query.filter_by(user_id=similar_user_id).all()
                for rating in similar_user_ratings:
                    if rating.movie_id not in rated_movie_ids:
                        movie_scores[rating.movie_id].append(
                            rating.rating * similarity
                        )

            # 计算加权平均分
            movie_predictions = {}
            for movie_id, scores in movie_scores.items():
                if len(scores) > 0:
                    movie_predictions[movie_id] = sum(scores) / len(scores)

            # 获取推荐电影详情
            recommended_movies = []
            for movie_id, score in sorted(movie_predictions.items(), 
                                        key=lambda x: x[1], 
                                        reverse=True)[:self.n_recommendations]:
                movie = Movie.query.get(movie_id)
                if movie:
                    recommended_movies.append({
                        'id': movie.id,
                        'title': movie.title,
                        'poster_url': movie.poster_url,
                        'rating_avg': movie.rating_avg,
                        'year': movie.year,
                        'predicted_rating': round(score, 2)
                    })

            return recommended_movies

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._get_popular_movies()

    def _get_popular_movies(self):
        """获取热门电影推荐"""
        popular_movies = Movie.query.order_by(
            Movie.rating_avg.desc()
        ).limit(self.n_recommendations).all()
        
        return [{
            'id': movie.id,
            'title': movie.title,
            'poster_url': movie.poster_url,
            'rating_avg': movie.rating_avg,
            'year': movie.year,
            'predicted_rating': None
        } for movie in popular_movies]

    def get_similar_movies(self, movie_id):
        """基于用户行为获取相似电影"""
        try:
            # 获取对该电影有评分的用户
            ratings = Rating.query.filter_by(movie_id=movie_id).all()
            if not ratings:
                return []

            # 获取这些用户对其他电影的评分
            user_ids = [r.user_id for r in ratings]
            other_ratings = Rating.query.filter(
                Rating.user_id.in_(user_ids),
                Rating.movie_id != movie_id
            ).all()

            # 计算电影相似度
            movie_ratings = defaultdict(list)
            for rating in other_ratings:
                movie_ratings[rating.movie_id].append(rating.rating)

            movie_avg_ratings = {}
            for m_id, ratings_list in movie_ratings.items():
                if len(ratings_list) >= 3:  # 至少3个评分
                    movie_avg_ratings[m_id] = sum(ratings_list) / len(ratings_list)

            # 获取相似电影详情
            similar_movies = []
            for movie_id, avg_rating in sorted(
                movie_avg_ratings.items(),
                key=lambda x: x[1],
                reverse=True
            )[:self.n_recommendations]:
                movie = Movie.query.get(movie_id)
                if movie:
                    similar_movies.append({
                        'id': movie.id,
                        'title': movie.title,
                        'poster_url': movie.poster_url,
                        'rating_avg': movie.rating_avg,
                        'year': movie.year
                    })

            return similar_movies

        except Exception as e:
            logger.error(f"Error finding similar movies: {str(e)}")
            return [] 