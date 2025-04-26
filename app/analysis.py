from app.models import Rating
from app import db
from sqlalchemy import func

def get_user_rating_stats(user_id):
    """
    获取用户的评分统计信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含用户评分统计信息的字典
        {
            'total_ratings': 评分总数,
            'avg_rating': 平均评分,
            'rating_distribution': 评分分布 {1: 数量, 2: 数量, ...}
        }
    """
    # 获取用户评分总数
    total_ratings = Rating.query.filter_by(user_id=user_id).count()
    
    # 获取用户平均评分
    avg_rating = db.session.query(func.avg(Rating.rating))\
        .filter(Rating.user_id == user_id)\
        .scalar() or 0.0
    
    # 获取评分分布
    rating_distribution = {}
    ratings = db.session.query(Rating.rating, func.count(Rating.rating))\
        .filter(Rating.user_id == user_id)\
        .group_by(Rating.rating)\
        .all()
    
    for rating in range(1, 6):  # 1-5分
        rating_distribution[rating] = 0
    
    for rating, count in ratings:
        rating_distribution[rating] = count
    
    return {
        'total_ratings': total_ratings,
        'avg_rating': round(float(avg_rating), 1),
        'rating_distribution': rating_distribution
    } 