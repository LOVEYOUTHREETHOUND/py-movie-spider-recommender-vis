from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.visualization import MovieVisualizer

bp = Blueprint('api', __name__, url_prefix='/api')
visualizer = MovieVisualizer(db)

@bp.route('/visualizations/rating-distribution')
@login_required
def rating_distribution_api():
    return jsonify(visualizer.get_rating_distribution())

@bp.route('/visualizations/genre-distribution')
@login_required
def genre_distribution_api():
    return jsonify(visualizer.get_genre_distribution())

@bp.route('/visualizations/year-distribution')
@login_required
def year_distribution_api():
    return jsonify(visualizer.get_year_distribution())

@bp.route('/visualizations/rating-trend')
@login_required
def rating_trend_api():
    return jsonify(visualizer.get_rating_trend())

@bp.route('/visualizations/activity-heatmap')
@login_required
def activity_heatmap_api():
    return jsonify(visualizer.get_activity_heatmap())

@bp.route('/visualizations/top-directors')
@login_required
def top_directors_api():
    return jsonify(visualizer.get_top_directors()) 