#!/bin/bash

# run.sh - Docker 컨테이너 개별 실행 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Docker 네트워크 생성
create_network() {
    print_info "Creating Docker network..."
    docker network create board-network 2>/dev/null || print_warning "Network already exists"
}

# 이미지 빌드
build_images() {
    print_info "Building Docker images..."
    
    # 파일 업로드용 볼륨 생성
    docker volume create file-uploads 2>/dev/null || print_warning "Volume file-uploads already exists"
    
    # User Service 빌드
    print_info "Building user-service..."
    docker build -t board-user-service ./user-service
    
    # Post Service 빌드
    print_info "Building post-service..."
    docker build -t board-post-service ./post-service
    
    # File Service 빌드
    print_info "Building file-service..."
    docker build -t board-file-service ./file-service
    
    # Frontend Service 빌드
    print_info "Building frontend..."
    docker build -t board-frontend ./frontend
    
    # Nginx 빌드
    print_info "Building nginx..."
    docker build -t board-nginx ./nginx
}

# 기존 컨테이너 정리
cleanup_containers() {
    print_info "Cleaning up existing containers..."
            docker stop user-service post-service file-service frontend nginx 2>/dev/null || true
            docker rm user-service post-service file-service frontend nginx 2>/dev/null || true
}

# MySQL 컨테이너 실행
run_mysql() {
    print_info "Starting MySQL container..."
    docker run -d \
        --name mysql \
        --network board-network \
        -e MYSQL_ROOT_PASSWORD=password \
        -e MYSQL_DATABASE=board_db \
        -v mysql-data:/var/lib/mysql \
        -v $(pwd)/database/init.sql:/docker-entrypoint-initdb.d/init.sql \
        -v $(pwd)/database/my.cnf:/etc/mysql/conf.d/my.cnf \
        -p 3306:3306 \
        mysql:8.0

    print_info "Waiting for MySQL to be ready..."
    sleep 30
}

# User Service 컨테이너 실행
run_user_service() {
    print_info "Starting User Service container..."
    docker run -d \
        --name user-service \
        --network board-network \
        -e DATABASE_URL="mysql+pymysql://root:password@host.docker.internal:3306/board_db" \
        -e SECRET_KEY="user-service-secret-key" \
        -e JWT_SECRET_KEY="jwt-secret-string" \
        -p 5001:5001 \
        board-user-service

    print_info "Waiting for User Service to be ready..."
    sleep 10
}

# Post Service 컨테이너 실행
run_post_service() {
    print_info "Starting Post Service container..."
    docker run -d \
        --name post-service \
        --network board-network \
        -e DATABASE_URL="mysql+pymysql://root:password@host.docker.internal:3306/board_db" \
        -e SECRET_KEY="post-service-secret-key" \
        -e USER_SERVICE_URL="http://user-service:5001" \
        -p 5002:5002 \
        board-post-service

    print_info "Waiting for Post Service to be ready..."
    sleep 10
}

# File Service 컨테이너 실행
run_file_service() {
    print_info "Starting File Service container..."
    docker run -d \
        --name file-service \
        --network board-network \
        -e SECRET_KEY="file-service-secret-key" \
        -v file-uploads:/app/uploads \
        -p 5003:5003 \
        board-file-service

    print_info "Waiting for File Service to be ready..."
    sleep 10
}

# Frontend 컨테이너 실행
run_frontend() {
    print_info "Starting Frontend container..."
    docker run -d \
        --name frontend \
        --network board-network \
        -e USER_SERVICE_URL="http://user-service:5001" \
        -e POST_SERVICE_URL="http://post-service:5002" \
        -e FILE_SERVICE_URL="http://file-service:5003" \
        -p 5000:5000 \
        board-frontend

    print_info "Waiting for Frontend to be ready..."
    sleep 10
}

# Nginx 컨테이너 실행
run_nginx() {
    print_info "Starting Nginx container..."
    docker run -d \
        --name nginx \
        --network board-network \
        -p 80:80 \
        board-nginx

    print_info "Nginx is ready!"
}

# 헬스체크
health_check() {
    print_info "Performing health check..."
    
    services=("user-service:5001" "post-service:5002" "file-service:5003" "frontend:5000" "nginx:80")
    
    for service in "${services[@]}"; do
        name=${service%:*}
        port=${service#*:}
        
        if docker exec -i $name sh -c "nc -z localhost $port" 2>/dev/null; then
            print_info "$name is running on port $port"
        else
            print_warning "$name might not be fully ready yet"
        fi
    done
}

# 메인 실행 함수
main() {
    case "$1" in
        "start")
            print_info "Starting Board System with MSA architecture..."
            create_network
            build_images
            cleanup_containers
            run_user_service
            run_post_service
            run_file_service
            run_frontend
            run_nginx
            health_check
            print_info "All services started! Access the application at http://localhost"
            ;;
        "stop")
            print_info "Stopping all containers..."
            docker stop user-service post-service file-service frontend nginx 2>/dev/null || true
            print_info "All containers stopped."
            ;;
        "clean")
            print_info "Cleaning up containers, images, and volumes..."
            cleanup_containers
            docker rmi board-user-service board-post-service board-file-service board-frontend board-nginx 2>/dev/null || true
            docker volume rm file-uploads 2>/dev/null || true
            docker network rm board-network 2>/dev/null || true
            print_info "Cleanup completed."
            ;;
        "logs")
            service_name=${2:-""}
            if [ -z "$service_name" ]; then
                print_info "Available services: user-service, post-service, file-service, frontend, nginx"
                print_info "Usage: ./run.sh logs <service-name>"
            else
                docker logs -f $service_name
            fi
            ;;
        "status")
            print_info "Container status:"
            docker ps --filter "name=user-service" --filter "name=post-service" --filter "name=file-service" --filter "name=frontend" --filter "name=nginx" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            ;;
        *)
            echo "Usage: $0 {start|stop|clean|logs|status}"
            echo ""
            echo "Commands:"
            echo "  start  - Build and start all services"
            echo "  stop   - Stop all running containers"
            echo "  clean  - Remove all containers, images, and volumes"
            echo "  logs   - View logs for a specific service"
            echo "  status - Show container status"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"