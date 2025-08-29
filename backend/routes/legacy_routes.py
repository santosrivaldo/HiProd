
from flask import Blueprint, jsonify

legacy_bp = Blueprint('legacy', __name__)

@legacy_bp.route('/usuario', methods=['GET'])
def get_user_legacy():
    return jsonify({'message': 'Esta rota foi descontinuada. Use /login para autenticação.'}), 410
