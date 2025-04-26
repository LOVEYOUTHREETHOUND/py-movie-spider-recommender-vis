# 豆瓣电影数据分析与推荐系统

这是一个基于 Python Flask 的豆瓣电影数据分析与推荐系统，包含电影数据爬取、数据分析、可视化展示和个性化推荐等功能。

## 技术栈

- **后端框架**: Flask
- **数据库**: SQLite + SQLAlchemy ORM
- **爬虫技术**: Selenium + BeautifulSoup4
- **数据分析**: Pandas + NumPy
- **可视化**: Echarts
- **前端技术**: Bootstrap + jQuery
- **推荐算法**: 协同过滤 + 基于内容的推荐

## 目录结构

```
.
├── app/                    # 应用主目录
│   ├── __init__.py        # Flask应用初始化
│   ├── models.py          # 数据库模型
│   ├── routes.py          # 路由控制
│   ├── auth.py           # 用户认证
│   ├── douban_spider.py   # 豆瓣爬虫
│   ├── recommender.py     # 推荐系统
│   ├── visualization.py   # 数据可视化
│   ├── analysis.py        # 数据分析
│   ├── static/           # 静态文件
│   ├── templates/        # HTML模板
│   └── utils/           # 工具函数
├── config.py              # 配置文件
├── requirements.txt       # 项目依赖
├── run.py                # 应用入口
├── init_db.py            # 数据库初始化
└── migrations/           # 数据库迁移文件
```

## 主要功能模块

### 1. 数据爬取 (douban_spider.py)

- 支持多种电影类型的数据爬取
- 自动处理反爬机制
- 支持断点续爬
- 异常处理和日志记录

### 2. 数据分析 (analysis.py)

- 电影评分分析
- 类型分布统计
- 年份分布分析
- 导演/演员作品分析

### 3. 可视化展示 (visualization.py)

- 评分分布图
- 类型占比图
- 年度电影数量趋势
- 评分 TOP 榜单

### 4. 推荐系统 (recommender.py)

- 基于用户的协同过滤
- 基于内容的推荐
- 混合推荐算法
- 个性化推荐结果

## 安装和运行

1. 克隆项目并安装依赖：

```bash
git clone <repository-url>
cd <project-directory>
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. 初始化数据库：

```bash
python init_db.py
```

3. 爬取电影数据（选择特定类型）：

```bash
python app/douban_spider.py --type 剧情
```

4. 运行应用：

```bash
python run.py
```

## 数据爬取说明

1. 支持的电影类型：

- 剧情、喜剧、动作、爱情、科幻、动画、悬疑、惊悚
- 恐怖、纪录片、短片、情色、音乐、歌舞、家庭、儿童
- 传记、历史、战争、犯罪、西部、奇幻、冒险、灾难
- 武侠、古装、运动、黑色电影

2. 爬取单个类型电影：

```bash
python app/douban_spider.py --type 动作
```

3. 爬取所有类型电影：

```bash
python init_db.py
```

## 配置说明

主要配置文件 `config.py` 包含：

- 数据库配置
- 爬虫配置
- 缓存配置
- 日志配置

## 开发说明

1. 数据库迁移：

```bash
flask db init      # 首次使用
flask db migrate   # 生成迁移脚本
flask db upgrade   # 应用迁移
```

2. 运行测试：

```bash
python test_crawler.py    # 爬虫测试
python test_recommender.py # 推荐系统测试
```

## 注意事项

1. 爬虫使用说明：

   - 遵守豆瓣的 robots 协议
   - 建议设置适当的爬取间隔
   - 注意处理反爬机制

2. 数据库：

   - 定期备份数据
   - 注意数据完整性
   - 及时清理缓存数据

3. 推荐系统：
   - 定期更新推荐模型
   - 注意冷启动问题
   - 关注推荐多样性

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License
