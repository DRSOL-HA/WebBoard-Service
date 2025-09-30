from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config import Config
from io import BytesIO

app = Flask(__name__)
app.config.from_object(Config)

# S3 클라이언트 초기화
def get_s3_client():
    try:
        if app.config['S3_ENDPOINT_URL']:
            # MinIO 등 다른 S3 호환 서비스 사용~!
            return boto3.client(
                's3',
                aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
                endpoint_url=app.config['S3_ENDPOINT_URL'],
                region_name=app.config['AWS_DEFAULT_REGION']
            )
        else:
            # AWS S3 사용
            return boto3.client(
                's3',
                aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
                region_name=app.config['AWS_DEFAULT_REGION']
            )
    except Exception as e:
        app.logger.error(f"S3 클라이언트 초기화 실패: {e}")
        raise e

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
            
            # S3에 파일 업로드
            s3_client = get_s3_client()
            file_data = file.read()
            file.seek(0)  # 파일 포인터를 처음으로 되돌림
            
            # S3 업로드 경로 구성
            s3_key = f"{app.config['S3_UPLOADS_PATH'].rstrip('/')}/{unique_filename}"
            
            s3_client.put_object(
                Bucket=app.config['S3_BUCKET_NAME'],
                Key=s3_key,
                Body=file_data,
                ContentType=file.content_type or 'application/octet-stream'
            )
            
            return jsonify({
                'message': '파일이 S3에 업로드되었습니다',
                'file_id': unique_filename,
                'original_name': original_filename
            }), 200
        else:
            return jsonify({'error': '허용되지 않는 파일 형식입니다'}), 400
    except NoCredentialsError:
        return jsonify({'error': 'S3 인증 정보가 올바르지 않습니다'}), 500
    except ClientError as e:
        return jsonify({'error': f'S3 업로드 실패: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        s3_client = get_s3_client()
        
        # S3에서 파일 다운로드 (uploads 디렉토리에서)
        s3_key = f"{app.config['S3_UPLOADS_PATH'].rstrip('/')}/{file_id}"
        response = s3_client.get_object(
            Bucket=app.config['S3_BUCKET_NAME'],
            Key=s3_key
        )
        
        file_data = response['Body'].read()
        
        # BytesIO 객체로 변환하여 Flask에서 처리
        file_obj = BytesIO(file_data)
        
        return send_file(
            file_obj,
            as_attachment=True,
            download_name=file_id,
            mimetype=response.get('ContentType', 'application/octet-stream')
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return jsonify({'error': '파일을 찾을 수 없습니다'}), 404
        else:
            return jsonify({'error': f'S3 다운로드 실패: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files/<file_id>')
def get_file_info(file_id):
    try:
        s3_client = get_s3_client()
        
        # S3에서 파일 정보 확인 (uploads 디렉토리에서)
        s3_key = f"{app.config['S3_UPLOADS_PATH'].rstrip('/')}/{file_id}"
        response = s3_client.head_object(
            Bucket=app.config['S3_BUCKET_NAME'],
            Key=s3_key
        )
        
        return jsonify({
            'file_id': file_id,
            'exists': True,
            'size': response['ContentLength'],
            'last_modified': response['LastModified'].isoformat(),
            'content_type': response.get('ContentType', 'application/octet-stream')
        }), 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return jsonify({
                'file_id': file_id,
                'exists': False
            }), 404
        else:
            return jsonify({'error': f'S3 파일 정보 조회 실패: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
