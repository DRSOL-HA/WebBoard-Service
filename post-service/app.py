from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from models import db, Post
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:5001')

def create_tables():
    db.create_all()

def verify_user_token(token):
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{USER_SERVICE_URL}/verify', headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

@app.route('/posts', methods=['GET'])
def get_posts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        posts = Post.query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        posts_list = []
        for post in posts.items:
            posts_list.append({
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'author_id': post.author_id,
                'author_name': post.author_name,
                'file_id': post.file_id,
                'file_name': post.file_name,
                'created_at': post.created_at.isoformat()
            })
        
        return jsonify({
            'posts': posts_list,
            'total': posts.total,
            'pages': posts.pages,
            'current_page': posts.page,
            'has_next': posts.has_next,
            'has_prev': posts.has_prev
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        return jsonify({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author_id': post.author_id,
            'author_name': post.author_name,
            'file_id': post.file_id,
            'file_name': post.file_name,
            'created_at': post.created_at.isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/posts', methods=['POST'])
def create_post():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_info = verify_user_token(token)
        
        if not user_info:
            return jsonify({'error': '인증이 필요합니다'}), 401
        
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        file_id = data.get('file_id')
        file_name = data.get('file_name')
        
        if not title or not content:
            return jsonify({'error': '제목과 내용을 입력해주세요'}), 400
        
        # 파일 첨부는 선택 사항
        if not file_id:
            file_id = None
            file_name = None
        
        post = Post(
            title=title,
            content=content,
            author_id=user_info['user_id'],
            author_name=user_info['username'],
            file_id=file_id,
            file_name=file_name
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({'message': '게시글이 작성되었습니다', 'post_id': post.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_info = verify_user_token(token)
        
        if not user_info:
            return jsonify({'error': '인증이 필요합니다'}), 401
        
        post = Post.query.get_or_404(post_id)
        
        if post.author_id != user_info['user_id']:
            return jsonify({'error': '본인의 게시글만 삭제할 수 있습니다'}), 403
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({'message': '게시글이 삭제되었습니다'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    with app.app_context():
        create_tables()
    app.run(host='0.0.0.0', port=5002)

