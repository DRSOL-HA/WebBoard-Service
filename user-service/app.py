from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import os
from models import db, User
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt = JWTManager(app)

def create_tables():
    db.create_all()

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': '이미 존재하는 사용자입니다!'}), 400
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'message': '회원가입이 완료되었습니다'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id))
            return jsonify({
                'access_token': access_token,
                'user_id': user.id,
                'username': user.username
            }), 200
        else:
            return jsonify({'error': '아이디 또는 비밀번호가 잘못되었습니다~~'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify', methods=['POST'])
@jwt_required()
def verify_token():
    current_user_id = get_jwt_identity()
    try:
        user_id_int = int(current_user_id)
    except (TypeError, ValueError):
        return jsonify({'valid': False}), 401
    user = User.query.get(user_id_int)
    if user:
        return jsonify({
            'valid': True,
            'user_id': user.id,
            'username': user.username
        }), 200
    return jsonify({'valid': False}), 401

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(host='0.0.0.0', port=5001)
