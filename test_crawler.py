from app import create_app, db
from app.douban_spider import DoubanSpider, MOVIE_TYPES
from app.models import Movie, MovieType
import time
import random
import logging

def test_crawler():
    """测试爬虫功能"""
    print("开始测试爬虫功能...")
    
    # 创建应用上下文
    app = create_app()
    with app.app_context():
        # 清理现有数据
        print("清理现有数据...")
        # 首先删除所有电影和类型之间的关联
        db.session.execute(db.text('DELETE FROM movie_type_association'))
        # 然后删除电影和类型数据
        Movie.query.delete()
        MovieType.query.delete()
        db.session.commit()
        print("已清空现有电影数据和类型数据")
        
        # 创建爬虫实例
        spider = DoubanSpider()
        
        try:
            print("\n开始爬取电影数据...")
            # 直接调用爬虫方法，它会自动遍历所有类型
            total_movies = spider.crawl_without_login()
            print(f"\n爬取完成，共获取 {total_movies} 部电影")
                
        except Exception as e:
            print(f"爬取过程中出错: {str(e)}")
        finally:
            # 关闭浏览器
            if hasattr(spider, 'driver'):
                spider.driver.quit()
                
        # 显示爬取结果统计
        movie_count = Movie.query.count()
        type_count = MovieType.query.count()
        print(f"\n数据库统计:")
        print(f"- 电影总数: {movie_count}")
        print(f"- 类型总数: {type_count}")

if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    test_crawler() 