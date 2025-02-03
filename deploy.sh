#!/bin/bash

# Load environment variables
set -a
source /home/$USER/flask_app/.env
set +a

echo "Deploying Flask App..."

# Update & Install Dependencies
sudo apt update && sudo apt install -y docker.io nginx certbot python3-certbot-nginx

# Stop and remove old container (if exists)
sudo docker stop flask-app || true
sudo docker rm flask-app || true

# Build & Run the Flask App
cd /home/$USER/flask_app
sudo docker build -t flask-app .
sudo docker run -d --name flask-app -p 5000:5000 --env-file .env flask-app

# Create NGINX Config using ENV variables
NGINX_CONF="/etc/nginx/sites-available/flask_app"
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Enable NGINX config
sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# Obtain SSL Certificate
sudo certbot --nginx -d $DOMAIN --email $EMAIL --non-interactive --agree-tos

# Auto-renew SSL every 90 days
echo "0 0 * * * certbot renew --quiet" | sudo tee -a /etc/crontab

echo "Deployment Completed! Visit https://$DOMAIN"
