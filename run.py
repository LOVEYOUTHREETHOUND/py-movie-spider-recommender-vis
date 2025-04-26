from app import create_app, db
from app.models import User, Movie, MovieType, Rating, UserSimilarity
from app.douban_spider import init_movies

app = create_app()

# 创建应用上下文
with app.app_context():
    # 创建所有数据库表
    db.create_all()
    
    # 如果没有任何用户，创建一个管理员账号
    if not User.query.first():
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Movie': Movie,
        'Rating': Rating,
        'UserSimilarity': UserSimilarity,
        'init_movies': init_movies
    }

if __name__ == '__main__':
    app.run(debug=True) 