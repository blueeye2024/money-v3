# 청안 시스템 Ubuntu 서버 배포 가이드

Ubuntu 서버를 사용하여 시스템을 배포하는 것이 성능, 안정성, 관리 측면에서 가장 좋습니다. Nginx를 웹 서버 및 리버스 프록시로 사용하여 React 프론트엔드와 Python 백엔드를 하나의 도메인에서 서비스하는 방법을 안내합니다.

## 1. 사전 준비
- Ubuntu Server (20.04 or 22.04 LTS 권장)
- 도메인 (A 레코드가 서버 IP를 가리키도록 설정)
- SSH 접속 가능한 환경

## 2. 서버 기본 설정 및 패키지 설치
서버에 접속하여 필수 패키지를 설치합니다.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx git -y
```

Node.js 설치 (Frontend 빌드용):
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3. 프로젝트 클론 및 설정
서버의 프로젝트 디렉토리로 이동하여 프로젝트를 다운로드합니다.

```bash
mkdir -p /home/blue/blue/my_project
cd /home/blue/blue/my_project
git clone https://github.com/blueeye2024/money.git
cd money
```

### 3-1. 백엔드 설정 (Python)
프로덕션 환경에서는 `gunicorn`과 `uvicorn`을 함께 사용하여 성능을 높입니다.

```bash
cd /home/blue/blue/my_project/money/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

**시스템 서비스 등록 (백그라운드 실행)**
`sudo nano /etc/systemd/system/cheongan-backend.service`

```ini
[Unit]
Description=Cheongan Backend Service
After=network.target

[Service]
User=blue
Group=www-data
WorkingDirectory=/home/blue/blue/my_project/money/backend
Environment="PATH=/home/blue/blue/my_project/money/backend/venv/bin"
ExecStart=/home/blue/blue/my_project/money/backend/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --workers 2

[Install]
WantedBy=multi-user.target
```

서비스 시작:
```bash
sudo systemctl start cheongan-backend
sudo systemctl enable cheongan-backend
```

### 3-2. 프론트엔드 빌드 (React)
React 앱을 정적 파일(HTML/CSS/JS)로 변환합니다.

```bash
cd /home/blue/blue/my_project/money/frontend
npm install
npm run build
```
빌드가 완료되면 `dist` 폴더가 생성됩니다.

## 4. Nginx 설정 (웹 서버 & 리버스 프록시)
Nginx를 통해 외부 요청은 React 앱을 보여주고, `/api` 요청은 백엔드로 전달합니다.

`sudo nano /etc/nginx/sites-available/cheongan`

```nginx
server {
    server_name your-domain.com; # 보유한 도메인 입력

    location / {
        root /home/blue/blue/my_project/money/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

설정 활성화:
```bash
sudo ln -s /etc/nginx/sites-available/cheongan /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # 기본 설정 삭제 (선택)
sudo nginx -t  # 설정 오류 검사
sudo systemctl restart nginx
```

## 5. SSL 인증서 적용 (HTTPS)
무료 SSL 인증서인 Let's Encrypt를 적용하여 보안을 강화합니다.

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

이제 웹 브라우저에서 `https://your-domain.com`으로 접속하면 청안 시스템을 확인할 수 있습니다.
