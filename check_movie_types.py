from app import create_app, db
from app.models import Movie, MovieType, Favorite

app = create_app()

with app.app_context():
    # 获取用户ID为2的收藏电影
    favorite_movies = Movie.query.join(Favorite).filter(Favorite.user_id == 2).all()
    
    print("\n收藏的电影及其类型：")
    print("-" * 50)
    for movie in favorite_movies:
        print(f"\n电影：{movie.title}")
        if movie.types:
            print(f"类型：{', '.join(t.name for t in movie.types)}")
        else:
            print("类型：暂无类型信息")
    
    print("\n\n所有电影类型：")
    print("-" * 50)
    movie_types = MovieType.query.all()
    for mt in movie_types:
        print(f"{mt.id}: {mt.name} (关联电影数：{len(mt.movies)})") 