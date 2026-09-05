#!/bin/bash
echo "Waiting for build to finish..."
while pgrep -f "next build" > /dev/null; do
    sleep 2
done
echo "Build finished! Copying .next folder..."
cp -r /root/ccf-cms-main-final/frontend/.next /root/ccf/frontend/.next-new
mv /root/ccf/frontend/.next /root/ccf/frontend/.next-bak
mv /root/ccf/frontend/.next-new /root/ccf/frontend/.next
pm2 restart ccf-frontend-staging
sleep 3
curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost:3000/
