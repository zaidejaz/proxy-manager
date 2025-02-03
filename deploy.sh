#!/bin/bash

set -e  # Exit on error

echo "🔧 Deploying Flask App..."

# Ensure .env exists
if [ ! -f "/home/$USER/flask_app/.env" ]; then
    echo "❌ ERROR: .env file is missing. Create it and rerun the script."
    exit 1
fi

# Load environment variables from .env
set -a
source "/home/$USER/flask_app/.env"
set +a

# Ensure DOMAIN and EMAIL are set in .env
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ ERROR: DOMAIN or EMAIL not set in .env file. Please provide valid values."
    exit 1
fi

echo "🌍 Domain: $DOMAIN"
echo "📧 Email: $EMAIL"

# Step 1: Update System & Install Dependencies
echo "📦 Installing necessary packages..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Step 2: Check if Docker is installed and start the service
echo "🐳 Ensuring Docker is properly set up..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Installing Docker..."
    sudo apt install -y docker.io
fi

sudo systemctl enable docker
sudo systemctl start docker

# Step 3: Stop and Remove Old Flask Container (if exists)
echo "🛑 Stopping previous container (if exists)..."
sudo docker stop flask-app || true
sudo docker rm flask-app || true

# Step 4: Build and Run the Flask App
echo "🚀 Building and running the Flask app..."
cd "/home/$USER/flask_app"
sudo docker build -t flask-app .
sudo docker run -d --name flask-app -p 5000:5000 --env-file .env flask-app

# Step 5: Configure NGINX Dynamically
echo "🔧 Configuring NGINX..."
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

NGINX_CONF="/etc/nginx/sites-available/flask_app"
sudo tee "$NGINX_CONF" > /dev/null <<EOF
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

# Enable NGINX Config
echo "✅ Enabling NGINX configuration..."
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
sudo systemctl restart nginx || sudo systemctl start nginx

# Step 6: Install SSL with Certbot
echo "🔐 Setting up SSL with Certbot..."
if ! sudo certbot --nginx -d "$DOMAIN" --email "$EMAIL" --non-interactive --agree-tos; then
    echo "❌ ERROR: Certbot failed to obtain SSL certificates."
    exit 1
fi

# Step 7: Verify SSL and Restart NGINX
echo "✅ SSL Certificates obtained. Restarting NGINX..."
sudo nginx -t
sudo systemctl restart nginx

# Step 8: Auto-renew SSL
echo "⏳ Setting up SSL auto-renew..."
echo "0 0 * * * certbot renew --quiet" | sudo tee -a /etc/crontab

echo "✅ Deployment Completed! Visit https://$DOMAIN"
