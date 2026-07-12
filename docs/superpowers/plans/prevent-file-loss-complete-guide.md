# 防止文件消失的完整方案

## 🎯 核心原则

**文件存储与代码完全分离，永不混合！**

---

## ✅ 正确架构（必须遵守）

```bash
# 文件存储目录（独立，不在项目内）
/data/tongshi/uploads/     ← 所有用户上传的文件
    ├── xxx.pdf
    ├── yyy.mp4
    └── zzz.jpg

# 项目代码目录（Git 管理）
~/tongshi_all_two/
    ├── backend/
    │   ├── .env           ← LOCAL_UPLOAD_DIR=/data/tongshi/uploads
    │   ├── .gitignore     ← 必须包含 uploads/
    │   └── app/
    ├── frontend/
    └── .git/
```

---

## 🔧 必须执行的 4 个配置

### **配置 1：.gitignore（防止文件进入 Git）**

**文件位置**: `~/tongshi_all_two/.gitignore`

```gitignore
# 文件上传目录（绝对不能提交）
uploads/
backend/uploads/
frontend/uploads/

# 环境变量（包含密码，绝对不能提交）
.env
*.secret

# 临时文件
*.db
*.sqlite
tmp/
temp/
*.log

# 依赖和构建产物
node_modules/
.venv/
__pycache__/
dist/
build/
```

**验证命令**：
```bash
cd ~/tongshi_all_two
git status | grep uploads
# 应该看不到 uploads 相关内容
```

---

### **配置 2：.env（确保使用独立目录）**

**文件位置**: `~/tongshi_all_two/backend/.env`

```bash
# ✅ 正确配置（绝对路径）
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=/data/tongshi/uploads

# ❌ 错误配置（相对路径）
# LOCAL_UPLOAD_DIR=./uploads
# LOCAL_UPLOAD_DIR=uploads
# LOCAL_UPLOAD_DIR=backend/uploads
```

**验证命令**：
```bash
cd ~/tongshi_all_two/backend
grep LOCAL_UPLOAD_DIR .env
# 必须是：LOCAL_UPLOAD_DIR=/data/tongshi/uploads
```

---

### **配置 3：服务器代码更新规范（安全操作）**

**创建安全更新脚本**: `~/tongshi_all_two/deploy/safe_update.sh`

```bash
#!/bin/bash
# 安全的代码更新脚本

set -e

PROJECT_DIR="$HOME/tongshi_all_two"
BACKUP_DIR="$HOME/tongshi_env_backups"

echo "================================"
echo "  tongshi 安全更新脚本"
echo "================================"

cd "$PROJECT_DIR"

# 1. 检查工作区状态
echo ""
echo "[1/5] 检查工作区状态..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠  工作区有未提交的修改："
    git status --short
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消更新"
        exit 1
    fi
fi

# 2. 备份 .env
echo ""
echo "[2/5] 备份环境配置..."
mkdir -p "$BACKUP_DIR"
if [ -f backend/.env ]; then
    cp backend/.env "$BACKUP_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✓ 已备份 .env"
fi

# 3. 保存本地修改
echo ""
echo "[3/5] 保存本地修改..."
git stash push -m "自动保存 $(date +%Y%m%d_%H%M%S)"

# 4. 拉取代码
echo ""
echo "[4/5] 拉取最新代码..."
git pull origin main || git pull origin master

# 5. 恢复本地修改
echo ""
echo "[5/5] 恢复本地修改..."
if git stash list | grep -q "自动保存"; then
    git stash pop || echo "⚠  有冲突，请手动解决"
fi

# 6. 验证关键文件
echo ""
echo "=== 验证关键配置 ==="
if [ -f backend/.env ]; then
    LOCAL_DIR=$(grep '^LOCAL_UPLOAD_DIR=' backend/.env | cut -d'=' -f2)
    if [[ "$LOCAL_DIR" == /data/tongshi/uploads ]]; then
        echo "✓ .env 配置正确"
    else
        echo "✗ 警告：LOCAL_UPLOAD_DIR 配置可能错误"
        echo "  当前值: $LOCAL_DIR"
        echo "  期望值: /data/tongshi/uploads"
    fi
else
    echo "✗ 警告：.env 文件不存在"
fi

echo ""
echo "================================"
echo "  更新完成"
echo "  下一步："
echo "  1. 检查 backend/.env 配置"
echo "  2. 重启后端服务"
echo "  3. 测试文件上传功能"
echo "================================"
```

**设置权限并使用**：
```bash
chmod +x ~/tongshi_all_two/deploy/safe_update.sh

# 以后更新代码用这个脚本，不要直接 git pull
~/tongshi_all_two/deploy/safe_update.sh
```

---

### **配置 4：文件目录权限和所有权**

```bash
# 确保独立目录存在且权限正确
sudo mkdir -p /data/tongshi/uploads
sudo chown -R ubuntu:ubuntu /data/tongshi/uploads
sudo chmod 755 /data/tongshi/uploads

# 验证
ls -la /data/tongshi/
# 应该看到：
# drwxr-xr-x ubuntu ubuntu uploads
```

---

## 🚫 永远不要执行的命令

在服务器上**绝对禁止**执行以下命令：

```bash
# ❌ 会删除所有未跟踪文件（包括 uploads/）
git clean -fd
git clean -fdx

# ❌ 会丢弃所有本地修改（包括 .env）
git reset --hard
git checkout -- .

# ❌ 会删除 .gitignore 忽略的文件
git clean -fdX
```

**如果误执行了**：
```bash
# 立即停止
Ctrl + C

# 检查损失
ls -la /data/tongshi/uploads/  # 独立目录应该安全
find . -name "*.pdf" -o -name "*.mp4"  # 检查项目内
```

---

## 📋 每次部署的标准流程

### **步骤 1：更新代码**
```bash
cd ~/tongshi_all_two
~/tongshi_all_two/deploy/safe_update.sh
```

### **步骤 2：检查配置**
```bash
cd ~/tongshi_all_two/backend
cat .env | grep LOCAL_UPLOAD_DIR
# 必须是：LOCAL_UPLOAD_DIR=/data/tongshi/uploads
```

### **步骤 3：更新依赖（如果需要）**
```bash
# 后端
cd ~/tongshi_all_two/backend
source .venv/bin/activate
pip install -r requirements.txt

# 前端
cd ~/tongshi_all_two/frontend
npm install
npm run build
```

### **步骤 4：数据库迁移（如果需要）**
```bash
cd ~/tongshi_all_two/backend
source .venv/bin/activate
alembic upgrade head
```

### **步骤 5：重启服务**
```bash
# 后端
sudo systemctl restart tongshi-backend

# Nginx
sudo systemctl reload nginx

# 验证
sudo systemctl status tongshi-backend
curl http://localhost:8050/api/health || echo "后端未响应"
```

### **步骤 6：验证文件功能**
```bash
# 检查文件数量
find /data/tongshi/uploads -type f | wc -l

# 测试上传（用浏览器或 curl）
# 访问 https://your-domain.com 测试文件上传和预览
```

---

## 🔍 日常检查脚本

**创建检查脚本**: `~/check_storage.sh`

```bash
#!/bin/bash
# 快速检查文件存储状态

echo "=== tongshi 文件存储状态 ==="
echo ""

# 1. .env 配置
echo "[配置]"
LOCAL_DIR=$(grep '^LOCAL_UPLOAD_DIR=' ~/tongshi_all_two/backend/.env | cut -d'=' -f2)
echo "LOCAL_UPLOAD_DIR=$LOCAL_DIR"

# 2. 文件统计
echo ""
echo "[文件统计]"
FILE_COUNT=$(find /data/tongshi/uploads -type f 2>/dev/null | wc -l)
echo "独立目录: $FILE_COUNT 个文件"

PROJECT_COUNT=$(find ~/tongshi_all_two/uploads ~/tongshi_all_two/backend/uploads -type f 2>/dev/null | wc -l)
if [ $PROJECT_COUNT -gt 0 ]; then
    echo "⚠  项目内: $PROJECT_COUNT 个文件（应该为 0）"
else
    echo "✓ 项目内: 0 个文件（正常）"
fi

# 3. 磁盘空间
echo ""
echo "[磁盘空间]"
df -h /data | tail -1 | awk '{print "可用: " $4 " / " $2 " (" $5 " 已用)"}'

# 4. 最近上传
echo ""
echo "[最近上传]"
find /data/tongshi/uploads -type f -printf '%T+ %f\n' 2>/dev/null | sort -r | head -3 | awk '{print "  " $2}'
```

**使用方法**：
```bash
chmod +x ~/check_storage.sh
~/check_storage.sh
```

---

## 🔐 自动备份（强烈推荐）

**创建备份脚本**: `/data/tongshi/backup_uploads.sh`

```bash
#!/bin/bash
# 文件自动备份脚本

UPLOAD_DIR="/data/tongshi/uploads"
BACKUP_DIR="/data/tongshi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uploads_$DATE.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 压缩备份
echo "开始备份: $UPLOAD_DIR"
tar -czf "$BACKUP_FILE" -C /data/tongshi uploads/

# 验证备份
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ 备份完成: $BACKUP_FILE ($SIZE)"

    # 保留最近 7 天的备份
    find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime +7 -delete
    echo "✓ 已清理 7 天前的旧备份"
else
    echo "✗ 备份失败"
    exit 1
fi
```

**设置定时备份**：
```bash
# 赋予执行权限
chmod +x /data/tongshi/backup_uploads.sh

# 设置 cron（每天凌晨 3 点备份）
crontab -e

# 添加以下行：
0 3 * * * /data/tongshi/backup_uploads.sh >> /var/log/tongshi_backup.log 2>&1

# 验证 cron 任务
crontab -l | grep backup
```

---

## 📊 问题排查清单

### **问题 1：文件上传后访问 404**

**检查步骤**：
```bash
# 1. 检查文件是否存在
ls -la /data/tongshi/uploads/ | tail -5

# 2. 检查 .env 配置
grep LOCAL_UPLOAD_DIR ~/tongshi_all_two/backend/.env

# 3. 检查服务是否使用正确配置
sudo journalctl -u tongshi-backend -n 50 | grep LOCAL_UPLOAD_DIR

# 4. 检查数据库记录
mysql -u tongshi_user -p tongshi -e "SELECT id, stored_name, storage_provider FROM stored_files ORDER BY created_at DESC LIMIT 5;"
```

### **问题 2：git pull 后文件消失**

**原因**：项目内有 uploads 目录被清理

**解决**：
```bash
# 1. 确认 .gitignore 包含 uploads/
grep uploads ~/tongshi_all_two/.gitignore

# 2. 确认项目内没有 uploads/
ls -la ~/tongshi_all_two/ | grep uploads
# 应该看不到

# 3. 恢复文件（如果有备份）
tar -xzf /data/tongshi/backups/uploads_*.tar.gz -C /data/tongshi/
```

### **问题 3：磁盘空间不足**

**检查和清理**：
```bash
# 检查空间
df -h /data

# 查找大文件
find /data/tongshi/uploads -type f -size +100M -exec ls -lh {} \;

# 清理旧备份（保留最近 3 天）
find /data/tongshi/backups -name "*.tar.gz" -mtime +3 -delete
```

---

## ✅ 配置验收清单

完成配置后，逐项检查：

```bash
# □ 1. .env 使用绝对路径
grep LOCAL_UPLOAD_DIR ~/tongshi_all_two/backend/.env
# 期望：LOCAL_UPLOAD_DIR=/data/tongshi/uploads

# □ 2. .gitignore 包含 uploads/
grep uploads ~/tongshi_all_two/.gitignore
# 期望：uploads/

# □ 3. 项目内无 uploads 目录
ls -la ~/tongshi_all_two/ | grep uploads
# 期望：无输出

# □ 4. 独立目录存在且权限正确
ls -la /data/tongshi/
# 期望：drwxr-xr-x ubuntu ubuntu uploads

# □ 5. 服务正常运行
sudo systemctl status tongshi-backend
# 期望：active (running)

# □ 6. 备份任务已设置
crontab -l | grep backup
# 期望：0 3 * * * /data/tongshi/backup_uploads.sh

# □ 7. 文件上传功能正常
# 浏览器测试上传文件，然后检查：
ls -la /data/tongshi/uploads/ | tail -1
# 应该看到刚上传的文件
```

---

## 🎯 总结：永不丢失文件的金规则

1. ✅ **绝对路径**：`.env` 中 `LOCAL_UPLOAD_DIR` 必须是 `/data/tongshi/uploads`
2. ✅ **目录分离**：项目内永远不要有 `uploads/` 目录
3. ✅ **Git 忽略**：`.gitignore` 必须包含 `uploads/`
4. ✅ **安全更新**：用脚本更新代码，不直接 `git pull`
5. ✅ **禁用命令**：永远不执行 `git clean -fd` 或 `git reset --hard`
6. ✅ **定期备份**：每天自动备份文件到独立目录
7. ✅ **定期检查**：用检查脚本验证配置正确

**遵守这 7 条规则，文件永远不会丢失！** 🎉
