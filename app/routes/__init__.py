# 使 routes 目录成为一个 Python 包 
from .movie import movie_bp
from .auth import auth_bp
 
__all__ = ['movie_bp', 'auth_bp'] 