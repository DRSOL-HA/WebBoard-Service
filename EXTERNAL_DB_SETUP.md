# 외부 DB 서버 설정 가이드

## 1. MySQL 서버 설치 및 설정

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

### CentOS/RHEL
```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo mysql_secure_installation
```

## 2. 데이터베이스 및 사용자 생성

```sql
-- MySQL에 root로 접속
mysql -u root -p

-- 데이터베이스 생성
CREATE DATABASE board_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 (선택사항 - 보안상 권장)
CREATE USER 'board_user'@'%' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON board_db.* TO 'board_user'@'%';
FLUSH PRIVILEGES;

-- 또는 root 사용자 사용 시
GRANT ALL PRIVILEGES ON board_db.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

## 3. 테이블 생성

```sql
USE board_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INT NOT NULL,
    author_name VARCHAR(80) NOT NULL,
    file_id VARCHAR(255),
    file_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_author_id (author_id),
    INDEX idx_created_at (created_at)
);
```

## 4. 방화벽 설정

```bash
# MySQL 포트(3306) 열기
sudo ufw allow 3306/tcp

# 또는 특정 IP만 허용
sudo ufw allow from YOUR_DOCKER_HOST_IP to any port 3306
```

## 5. MySQL 설정 파일 수정

```bash
# /etc/mysql/mysql.conf.d/mysqld.cnf 편집
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# 다음 설정 추가/수정
[mysqld]
bind-address = 0.0.0.0  # 모든 IP에서 접속 허용
```

## 6. 환경변수 설정

### 방법 1: run.sh에서 직접 수정
```bash
# run.sh의 DATABASE_URL 부분을 실제 DB 서버 정보로 변경
-e DATABASE_URL="mysql+pymysql://username:password@DB_SERVER_IP:3306/board_db" \
```

### 방법 2: 환경변수 파일 사용
```bash
# .env 파일 생성
echo "DATABASE_URL=mysql+pymysql://username:password@DB_SERVER_IP:3306/board_db" > .env

# run.sh에서 환경변수 로드 추가
source .env
```

## 7. Docker 네트워크 설정 (선택사항)

외부 DB 서버가 Docker 호스트와 다른 네트워크에 있는 경우:

```bash
# Docker 컨테이너에서 외부 DB 접근을 위한 네트워크 설정
docker run --add-host=db-server:DB_SERVER_IP ...
```

## 8. 연결 테스트

```bash
# 컨테이너에서 DB 연결 테스트
docker exec -it user-service python -c "
from app import app, db
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print('DB 연결 성공!')
    except Exception as e:
        print(f'DB 연결 실패: {e}')
"
```

## 9. 보안 권장사항

1. **강력한 비밀번호 사용**
2. **특정 IP만 접속 허용**
3. **SSL/TLS 연결 사용**
4. **정기적인 백업**
5. **방화벽 설정**

## 10. 문제 해결

### 연결 실패 시
- 방화벽 설정 확인
- MySQL bind-address 확인
- 사용자 권한 확인
- 네트워크 연결 확인

### 성능 최적화
- 적절한 인덱스 설정
- 쿼리 최적화
- 연결 풀 설정
