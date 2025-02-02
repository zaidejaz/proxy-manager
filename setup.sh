#!/bin/bash

# Create required directories
mkdir -p nginx certbot/conf certbot/www data

# Create Nginx configuration
cat > nginx/app.conf << EOF
server {
    listen 80;
    listen [::]:80;
    server_name \${DOMAIN} www.\${DOMAIN};
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name \${DOMAIN} www.\${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/\${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/\${DOMAIN}/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Initial SSL certificate request
if [ ! -d "certbot/conf/live/\${DOMAIN}" ]; then
    docker-compose up -d nginx
    
    # Wait for nginx to start
    sleep 5
    
    # Request certificate
    docker-compose run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email \${EMAIL} \
        --agree-tos \
        --no-eff-email \
        -d \${DOMAIN} \
        -d www.\${DOMAIN}
        
    # Restart nginx to load the certificates
    docker-compose restart nginx
fi