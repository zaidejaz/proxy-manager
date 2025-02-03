#!/bin/bash

set -e  # Exit on error

echo "🔧 Deploying Flask App..."

# Ensure .env exists
if [ ! -f "/home/$USER/proxy_manager/.env" ]; then
    echo "❌ ERROR: .env file is missing. Create it and rerun the script."
    exit 1
fi

# Load environment variables from .env
set -a
source "/home/$USER/proxy_manager/.env"
set +a

#Ensure DOMAIN and EMAIL are set in .env
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "❌ ERROR: DOMAIN or EMAIL not set in .env file. Please provide valid values."
    exit 1
fi

echo "🌍 Domain: $DOMAIN"
echo "📧 Email: $EMAIL"

# Step 1: Update System & Install Dependencies
echo "📦 Installing necessary packages..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx python3-pip

# Step 2: Install Poetry (similar to Dockerfile)
echo "📦 Installing Poetry for dependency management..."
sudo apt install python3-poetry

# Step 3: Install app dependencies using Poetry
echo "📦 Installing Flask app dependencies..."
cd "/home/$USER/proxy_manager"
poetry install

# Step 4: Install Gunicorn and Gevent (required for concurrency)
echo "📦 Installing Gunicorn and Gevent..."
poetry add gunicorn gevent

# Step 5: Run Flask App using Gunicorn (with Gevent workers)
echo "🚀 Starting Flask app using Gunicorn..."
nohup poetry run gunicorn --workers=6 --worker-class=gevent --worker-connections=1000 \
  --max-requests=10000 --max-requests-jitter=1000 --backlog=2048 --bind 127.0.0.1:5000 \
  --timeout=30 "proxy_manager:create_app()"

# Step 6: Configure NGINX Dynamically
echo "🔧 Configuring NGINX..."
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

NGINX_CONF="/etc/nginx/sites-available/proxy_manager"
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

# Step 7: Install SSL with Certbot
echo "🔐 Setting up SSL with Certbot..."
if ! sudo certbot --nginx -d "$DOMAIN" --email "$EMAIL" --non-interactive --agree-tos; then
    echo "❌ ERROR: Certbot failed to obtain SSL certificates."
    exit 1
fi

# Step 8: Verify SSL and Restart NGINX
echo "✅ SSL Certificates obtained. Restarting NGINX..."
sudo nginx -t
sudo systemctl restart nginx

# Step 9: Auto-renew SSL
echo "⏳ Setting up SSL auto-renew..."
echo "0 0 * * * certbot renew --quiet" | sudo tee -a /etc/crontab

echo "✅ Deployment Completed! Visit https://$DOMAIN"
