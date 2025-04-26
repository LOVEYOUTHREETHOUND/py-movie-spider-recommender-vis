from app import create_app
from app.models import User, Movie, Rating, UserSimilarity, db
from datetime import datetime
import random

def test_recommender():
    """测试推荐系统功能"""
    app = create_app()
    with app.app_context():
        # 创建测试用户
        test_user = User.query.filter_by(username='test_user').first()
        if not test_user:
            test_user = User(username='test_user', email='test@example.com')
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
            print("创建测试用户成功")
        
        # 获取所有电影
        movies = Movie.query.all()
        if not movies:
            print("错误：没有电影数据，请先运行爬虫")
            return
        
        # 为测试用户添加一些随机评分
        print("\n添加测试评分:")
        for movie in random.sample(movies, min(5, len(movies))):
            rating = Rating.query.filter_by(user_id=test_user.id, movie_id=movie.id).first()
            if not rating:
                rating = Rating(
                    user_id=test_user.id,
                    movie_id=movie.id,
                    rating=random.randint(1, 5),
                    comment="测试评论",
                    created_at=datetime.utcnow()
                )
                db.session.add(rating)
                print(f"- 为电影 '{movie.title}' 添加评分: {rating.rating}")
        
        db.session.commit()
        
        # 获取用户的所有评分
        user_ratings = Rating.query.filter_by(user_id=test_user.id).all()
        print(f"\n用户总评分数: {len(user_ratings)}")
        
        # 显示用户的评分历史
        print("\n用户评分历史:")
        for rating in user_ratings:
            movie = Movie.query.get(rating.movie_id)
            print(f"- {movie.title}: {rating.rating}星")
        
        # 计算用户相似度
        print("\n计算用户相似度...")
        other_users = User.query.filter(User.id != test_user.id).all()
        for other_user in other_users:
            # 获取两个用户共同评分的电影
            common_ratings = db.session.query(
                Rating.movie_id,
                Rating.rating
            ).filter_by(
                user_id=test_user.id
            ).join(
                Rating,
                db.and_(
                    Rating.movie_id == Rating.movie_id,
                    Rating.user_id == other_user.id
                )
            ).all()
            
            if common_ratings:
                similarity = UserSimilarity(
                    user_id1=test_user.id,
                    user_id2=other_user.id,
                    similarity=random.random()  # 这里应该使用实际的相似度计算
                )
                db.session.add(similarity)
                print(f"- 与用户 {other_user.username} 的相似度已计算")
        
        db.session.commit()
        
        # 获取相似用户
        similar_users = UserSimilarity.query.filter_by(user_id1=test_user.id)\
            .order_by(UserSimilarity.similarity.desc())\
            .limit(5)\
            .all()
        
        print("\n最相似的用户:")
        for sim in similar_users:
            user = User.query.get(sim.user_id2)
            print(f"- {user.username}: 相似度 {sim.similarity:.2f}")

if __name__ == '__main__':
    print("开始测试推荐系统...")
    test_recommender()
    print("\n推荐系统测试完成！") 