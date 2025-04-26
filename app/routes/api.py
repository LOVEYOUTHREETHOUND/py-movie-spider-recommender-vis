from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Food
from app import db

bp = Blueprint('api', __name__)

@bp.route('/nutrition/deficit')
@login_required
def get_nutrition_deficit():
    from app.analysis import calculate_deficit
    deficit = calculate_deficit(current_user.id)
    if deficit:
        return jsonify(deficit)
    return jsonify({'error': '无法计算营养缺口'}), 400

@bp.route('/food/search')
@login_required
def search_food():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    foods = Food.query.filter(Food.name.like(f'%{query}%')).all()
    return jsonify([{
        'id': food.id,
        'name': food.name,
        'calories': food.calories,
        'protein': food.protein,
        'fat': food.fat
    } for food in foods]) 