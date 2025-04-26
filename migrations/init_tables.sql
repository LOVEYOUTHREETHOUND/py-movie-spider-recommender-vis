-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建电影类型表
CREATE TABLE IF NOT EXISTS movie_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type_id INT UNIQUE,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- 创建电影表
CREATE TABLE IF NOT EXISTS movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    douban_id VARCHAR(20) UNIQUE,
    title VARCHAR(200) NOT NULL,
    year INT,
    rate FLOAT,
    director VARCHAR(200),
    description TEXT,
    poster_url VARCHAR(500),
    poster_path VARCHAR(200),
    region VARCHAR(50),
    cast TEXT,
    genres TEXT,
    rating_avg FLOAT DEFAULT 0,
    rating_count INT DEFAULT 0,
    summary TEXT,
    screenwriter TEXT,
    language VARCHAR(100),
    duration INT,
    poster_data LONGBLOB,
    poster_mimetype VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建电影类型关联表
CREATE TABLE IF NOT EXISTS movie_type_association (
    movie_id INT,
    type_id INT,
    PRIMARY KEY (movie_id, type_id),
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    FOREIGN KEY (type_id) REFERENCES movie_types(id) ON DELETE CASCADE
);

-- 创建评分表
CREATE TABLE IF NOT EXISTS ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_movie (user_id, movie_id)
); 