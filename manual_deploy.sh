#!/bin/bash
echo "🚀 [Deploy Helper] Starting Deployment Process..."

# 1. Update Frontend
echo "📦 Building Frontend (Vite)..."
cd /home/blue/blue/my_project/money/frontend
npm run build
if [ $? -eq 0 ]; then
    echo "✅ Frontend Build Success!"
    echo "📂 Copying files to /var/www/html..."
    sudo cp -r dist/* /var/www/html/
else
    echo "❌ Frontend Build Failed!"
    exit 1
fi
cd ..

# 2. Restart Backend
echo "🔄 Restarting Backend Service..."
echo "🔒 Sudo password might be required."

sudo systemctl restart cheongan-backend

if [ $? -eq 0 ]; then
    echo "✅ Backend Restarted Successfully!"
    echo "🎉 Deployment Complete! Please Refresh your Browser (Ctrl+Shift+R)."
else
    echo "❌ Backend Restart Failed. Please check password or permissions."
fi
