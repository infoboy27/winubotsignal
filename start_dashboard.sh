#!/bin/bash
cd /home/ubuntu/winubotsignal/bot && nohup python3 dashboard/app.py > dashboard.log 2>&1 &
echo "Dashboard started in background. Check http://localhost:8000"

