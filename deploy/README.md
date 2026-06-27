# 部署上传脚本

这个目录放的是上线辅助文件，不是完整发布系统。

## 上传辅助文件到服务器

脚本会把本次上线需要的配置和说明文件同步到服务器的目标目录，不会上传 `.env`、不会写入密码，也不会自动重启服务。

PowerShell 7：

```powershell
pwsh -File .\deploy\upload-local-storage-deploy.ps1 `
  -Host 1.2.3.4 `
  -User deploy `
  -RemoteRoot /opt/tongshi `
  -IdentityFile C:\Users\ASUS\.ssh\id_rsa `
  -DryRun
```

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\upload-local-storage-deploy.ps1 `
  -Host 1.2.3.4 `
  -User deploy `
  -RemoteRoot /opt/tongshi `
  -IdentityFile C:\Users\ASUS\.ssh\id_rsa `
  -DryRun
```

去掉 `-DryRun` 后执行真实上传。

## 会上传哪些文件

- `deploy/nginx.conf`
- `deploy/README.md`
- `backend/scripts/check_deploy_env.py`
- `backend/.env.example`
- `backend/README.md`
- `frontend/.env.production.example`
- `frontend/README.md`
- `docs/superpowers/project-map.md`

## 说明

- 如果你只是想把这次上线相关文件同步到服务器，这个脚本够用。
- 如果你想把完整代码更新到服务器，更稳妥的做法还是合回 `main` 后在服务器执行 `git pull`。
