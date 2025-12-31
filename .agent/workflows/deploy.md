---
description: Build and deploy the application
---
// turbo-all
1. Bump version in `frontend/package.json`
2. Commit and Push to GitHub: `git add . && git commit -m "chore: deployment" && git push origin main`
3. Build the frontend: `cd frontend && npm run build`
4. Deploy to server: Run `web-run100` (User Shortcut) or `bash auto_deploy.sh`
5. Fallback: `sudo systemctl restart cheongan-backend && sudo systemctl reload nginx`

