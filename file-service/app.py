from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = '/app/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            
            return jsonify({
                'message': '파일이 업로드되었습니다',
                'file_id': unique_filename,
                'original_name': original_filename
            }), 200
        else:
            return jsonify({'error': '허용되지 않는 파일 형식입니다'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        return send_from_directory(UPLOAD_FOLDER, file_id, as_attachment=True)
    except Exception as e:
        return jsonify({'error': '파일을 찾을 수 없습니다'}), 404

@app.route('/files/<file_id>')
def get_file_info(file_id):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file_id)
        if os.path.exists(file_path):
            return jsonify({
                'file_id': file_id,
                'exists': True,
                'size': os.path.getsize(file_path)
            }), 200
        else:
            return jsonify({
                'file_id': file_id,
                'exists': False
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
