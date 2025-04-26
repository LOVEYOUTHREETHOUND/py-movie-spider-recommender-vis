from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 用户评分
    ratings = db.relationship('Rating', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 电影与类型的关联表
movie_type_association = db.Table('movie_type_association',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'), primary_key=True),
    db.Column('type_id', db.Integer, db.ForeignKey('movie_types.id'), primary_key=True)
)

# 电影类型表
class MovieType(db.Model):
    __tablename__ = 'movie_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    movies = db.relationship('Movie', secondary='movie_type_association', back_populates='types')

class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    douban_id = db.Column(db.String(20), unique=True)
    title = db.Column(db.String(200), nullable=False)
    original_title = db.Column(db.String(200))
    year = db.Column(db.Integer)
    directors = db.Column(db.String(200))  # 导演列表
    writers = db.Column(db.String(200))    # 编剧列表
    actors = db.Column(db.String(500))     # 演员列表
    countries = db.Column(db.String(200))  # 制片国家/地区
    languages = db.Column(db.String(200))  # 语言
    release_date = db.Column(db.String(200))  # 上映日期，修改为 200 长度
    runtime = db.Column(db.Integer)        # 片长（分钟）
    rating = db.Column(db.Float)           # 豆瓣评分
    rating_count = db.Column(db.Integer)   # 评分人数
    summary = db.Column(db.Text)           # 简介
    poster_url = db.Column(db.String(500)) # 海报URL
    poster_data = db.Column(db.LargeBinary)  # 海报数据
    poster_mimetype = db.Column(db.String(50))  # 海报MIME类型
    tags = db.Column(db.String(500))       # 标签
    
    types = db.relationship('MovieType', secondary='movie_type_association', back_populates='movies')
    ratings = db.relationship('Rating', backref='movie', lazy=True)

    @property
    def user_rating_avg(self):
        """计算用户的平均评分"""
        if not self.ratings:
            return self.rating or 0  # 如果没有用户评分，返回豆瓣评分或0
        return sum(r.rating for r in self.ratings) / len(self.ratings)

    @property
    def user_rating_count(self):
        """获取用户评分数量"""
        return len(self.ratings)

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 创建唯一索引确保每个用户对每部电影只有一个评分
    __table_args__ = (db.UniqueConstraint('user_id', 'movie_id', name='unique_user_movie'),)

class UserSimilarity(db.Model):
    __tablename__ = 'user_similarities'
    id = db.Column(db.Integer, primary_key=True)
    user_id1 = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id2 = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    similarity = db.Column(db.Float, nullable=False)  # 相似度分数
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 