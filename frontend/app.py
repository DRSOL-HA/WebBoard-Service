from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import os

app = Flask(__name__)
app.secret_key = 'frontend-secret-key'

USER_SERVICE_URL = os.environ.get('USER_SERVICE_URL', 'http://user-service:5001')
POST_SERVICE_URL = os.environ.get('POST_SERVICE_URL', 'http://post-service:5002')
FILE_SERVICE_URL = os.environ.get('FILE_SERVICE_URL', 'http://file-service:5003')

@app.before_request
def ensure_session_token_valid():
    try:
        if 'access_token' in session:
            headers = {'Authorization': f"Bearer {session['access_token']}"}
            resp = requests.post(f"{USER_SERVICE_URL}/verify", headers=headers, timeout=2)
            if resp.status_code != 200 or not resp.json().get('valid'):
                session.clear()
                # Avoid flashing during static asset requests
                if request.endpoint not in ('static',):
                    flash('세션이 만료되어 자동으로 로그아웃되었습니다.')
    except Exception:
        # On verification errors (network, etc.), do not force logout
        pass

@app.route('/')
def index():
    try:
        page = request.args.get('page', 1, type=int)
        response = requests.get(f'{POST_SERVICE_URL}/posts?page={page}&per_page=10')
        if response.status_code == 200:
            posts_data = response.json()
        else:
            posts_data = {'posts': [], 'pages': 0, 'current_page': 1}
        
        return render_template('index.html', posts_data=posts_data)
    except Exception as e:
        flash(f'오류가 발생했습니다: {str(e)}')
        return render_template('index.html', posts_data={'posts': [], 'pages': 0, 'current_page': 1})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            response = requests.post(f'{USER_SERVICE_URL}/register', json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 201:
                flash('회원가입이 완료되었습니다. 로그인해주세요.')
                return redirect(url_for('login'))
            else:
                flash(response.json().get('error', '회원가입에 실패했습니다.'))
        except Exception as e:
            flash(f'오류가 발생했습니다: {str(e)}')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            response = requests.post(f'{USER_SERVICE_URL}/login', json={
                'username': username,
                'password': password
            })
            
            if response.status_code == 200:
                data = response.json()
                session['access_token'] = data['access_token']
                session['user_id'] = data['user_id']
                session['username'] = data['username']
                flash('로그인되었습니다.')
                return redirect(url_for('index'))
            else:
                flash(response.json().get('error', '로그인에 실패했습니다.'))
        except Exception as e:
            flash(f'오류가 발생했습니다: {str(e)}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃되었습니다.')
    return redirect(url_for('index'))

@app.route('/write', methods=['GET', 'POST'])
def write():
    if 'access_token' not in session:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        file_id = None
        file_name = None
        
        try:
            # 파일이 제공된 경우에만 업로드 처리
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    files = {'file': (file.filename, file.stream, file.mimetype)}
                    file_response = requests.post(f'{FILE_SERVICE_URL}/upload', files=files)
                    if file_response.status_code == 200:
                        file_data = file_response.json()
                        file_id = file_data.get('file_id')
                        file_name = file_data.get('original_name')
                    else:
                        flash('파일 업로드에 실패했습니다.')
                        return render_template('write.html')
            
            # 게시글 작성
            headers = {'Authorization': f"Bearer {session['access_token']}"}
            post_data = {
                'title': title,
                'content': content,
                'file_id': file_id,
                'file_name': file_name
            }
            
            response = requests.post(f'{POST_SERVICE_URL}/posts', json=post_data, headers=headers)
            
            if response.status_code == 201:
                flash('게시글이 작성되었습니다.')
                return redirect(url_for('index'))
            else:
                flash(response.json().get('error', '게시글 작성에 실패했습니다.'))
        except Exception as e:
            flash(f'오류가 발생했습니다: {str(e)}')
    
    return render_template('write.html')

@app.route('/post/<int:post_id>')
def view_post(post_id):
    try:
        response = requests.get(f'{POST_SERVICE_URL}/posts/{post_id}')
        if response.status_code == 200:
            post = response.json()
            return render_template('post.html', post=post)
        else:
            flash('게시글을 찾을 수 없습니다.')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'오류가 발생했습니다: {str(e)}')
        return redirect(url_for('index'))

@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'access_token' not in session:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))
    
    try:
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        response = requests.delete(f'{POST_SERVICE_URL}/posts/{post_id}', headers=headers)
        
        if response.status_code == 200:
            flash('게시글이 삭제되었습니다.')
        else:
            flash(response.json().get('error', '게시글 삭제에 실패했습니다.'))
    except Exception as e:
        flash(f'오류가 발생했습니다: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        response = requests.get(f'{FILE_SERVICE_URL}/download/{file_id}', stream=True)
        if response.status_code == 200:
            return response.content, 200, {
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Disposition': response.headers.get('Content-Disposition', f'attachment; filename="{file_id}"')
            }
        else:
            flash('파일을 찾을 수 없습니다.')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'오류가 발생했습니다: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
