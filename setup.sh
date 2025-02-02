#!/bin/bash

# Ensure environment variables are set
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Error: DOMAIN and EMAIL environment variables must be set"
    exit 1
fi

# Create required directories if they don't exist
mkdir -p nginx certbot/conf certbot/www data

# Verify nginx configuration file exists
if [ ! -f "nginx/app.conf" ]; then
    echo "Error: nginx/app.conf file not found"
    exit 1
fi

# Initial SSL certificate request
if [ ! -d "certbot/conf/live/${DOMAIN}" ]; then
    echo "Setting up initial SSL certificate for ${DOMAIN}"
    
    # Start nginx temporarily
    docker-compose up -d nginx
    
    # Wait for nginx to start
    echo "Waiting for nginx to start..."
    sleep 5
    
    # Request certificate
    docker-compose run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email ${EMAIL} \
        --agree-tos \
        --no-eff-email \
        -d ${DOMAIN} \
        -d www.${DOMAIN}
    
    # Check if certificate was obtained successfully
    if [ ! -d "certbot/conf/live/${DOMAIN}" ]; then
        echo "Failed to obtain SSL certificate"
        exit 1
    fi
fi

echo "Setup completed successfully"