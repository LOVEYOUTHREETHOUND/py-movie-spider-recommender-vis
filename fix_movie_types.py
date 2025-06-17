from app import create_app, db
from app.models import Movie, MovieType, Favorite
from app.douban_spider import DoubanSpider
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

with app.app_context():
    # 创建爬虫实例
    spider = DoubanSpider()
    
    # 获取用户ID为2的收藏电影
    favorite_movies = Movie.query.join(Favorite).filter(Favorite.user_id == 2).all()
    
    # 删除"总榜"类型
    total_type = MovieType.query.filter_by(name="总榜").first()
    if total_type:
        logger.info("删除'总榜'类型...")
        for movie in total_type.movies:
            movie.types.remove(total_type)
        db.session.delete(total_type)
        db.session.commit()
    
    # 为每部电影重新获取类型
    for movie in favorite_movies:
        logger.info(f"\n处理电影：{movie.title}")
        try:
            # 获取电影详情
            movie_detail = spider.get_movie_detail(movie.douban_id)
            if movie_detail:
                # 获取电影类型
                info_text = movie_detail.get('info_text', '')
                if '类型:' in info_text:
                    type_text = info_text.split('类型:')[1].split('\n')[0].strip()
                    type_names = [t.strip() for t in type_text.split('/')]
                    
                    # 关联类型
                    for type_name in type_names:
                        movie_type = MovieType.query.filter_by(name=type_name).first()
                        if movie_type and movie_type not in movie.types:
                            movie.types.append(movie_type)
                            logger.info(f"添加类型：{type_name}")
                
                db.session.commit()
        except Exception as e:
            logger.error(f"处理电影 {movie.title} 时出错: {str(e)}")
            continue
    
    if spider.driver:
        spider.driver.quit() 