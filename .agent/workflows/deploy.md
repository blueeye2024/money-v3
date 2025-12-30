---
description: Build and deploy the application
---
// turbo-all
1. Bump version in `frontend/package.json`
2. Commit and Push to GitHub: `git add . && git commit -m "chore: deployment" && git push origin main`
3. Build the frontend: `cd frontend && npm run build`
4. Restart the backend service: `sudo systemctl restart cheongan-backend`
5. Reload Nginx: `sudo systemctl reload nginx`
