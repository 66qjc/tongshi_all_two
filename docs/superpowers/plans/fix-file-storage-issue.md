# 文件存储消失问题：诊断与修复方案

## 问题描述

**现象**：服务器上执行 `git pull` 后，之前上传的文件（课程资料、学生作品等）全部消失。

**影响**：
- ❌ 课程资料无法访问
- ❌ 学生作品丢失
- ❌ 用户头像丢失
- ❌ 数据库中有记录，但文件不存在

---

## 根本原因

### ❌ 错误架构：文件存储在项目目录内

```
tongshi/
├── backend/
│   ├── uploads/          ← 文件存储在这里（错误）
│   │   ├── xxx.pdf
│   │   └── yyy.jpg
│   ├── .gitignore        ← uploads/ 被忽略
│   └── ...
└── .git/
```

**问题：**
1. `backend/.gitignore` 忽略了 `uploads/`
2. 执行 `git pull` 或 `git clean -fd` 时可能清理未跟踪文件
3. 文件与代码混在一起，备份困难

### ✅ 正确架构：文件存储在独立目录

```
/data/tongshi/uploads/     ← 独立存储目录（正确）
    ├── xxx.pdf
    └── yyy.jpg

/opt/tongshi/              ← 项目代码目录
    ├── backend/
    │   ├── .env           ← LOCAL_UPLOAD_DIR=/data/tongshi/uploads
    │   └── ...
    └── .git/
```

---

## 服务器配置检查清单

### Step 1：检查当前配置

SSH 登录服务器后执行：

```bash
# 1. 检查 .env 配置
cd /opt/tongshi/backend  # 或你的项目路径
cat .env | grep LOCAL_UPLOAD_DIR

# 2. 检查目录是否存在
ls -la /data/tongshi/uploads/

# 3. 检查目录内文件数量
find /data/tongshi/uploads/ -type f | wc -l

# 4. 检查后端进程实际使用的路径
ps aux | grep uvicorn
# 或
systemctl status tongshi-backend
```

### Step 2：诊断问题

**情况 A：`.env` 配置错误**
```bash
# 如果输出是相对路径或为空
LOCAL_UPLOAD_DIR=./uploads           # ❌ 错误
LOCAL_UPLOAD_DIR=backend/uploads     # ❌ 错误
LOCAL_UPLOAD_DIR=                    # ❌ 未配置

# 应该是绝对路径
LOCAL_UPLOAD_DIR=/data/tongshi/uploads  # ✅ 正确
```

**情况 B：目录不存在**
```bash
ls -la /data/tongshi/uploads/
# 如果返回：No such file or directory
```

**情况 C：权限不足**
```bash
ls -la /data/tongshi/
# 检查 uploads 目录的所有者和权限
drwxr-xr-x 2 root root  # ❌ 后端进程无权限写入
drwxrwxr-x 2 www-data www-data  # ✅ 正确
```

---

## 修复步骤

### Step 1：创建独立存储目录

```bash
# 1. 创建目录
sudo mkdir -p /data/tongshi/uploads

# 2. 设置所有者（假设后端以 www-data 用户运行）
sudo chown -R www-data:www-data /data/tongshi/uploads

# 3. 设置权限
sudo chmod -R 755 /data/tongshi/uploads

# 4. 验证
ls -la /data/tongshi/
```

### Step 2：迁移现有文件（如果有）

```bash
# 如果项目目录内还有残留文件
cd /opt/tongshi/backend

# 检查是否有文件
if [ -d "uploads" ] && [ "$(ls -A uploads)" ]; then
    echo "发现旧文件，开始迁移..."
    
    # 复制文件到新目录
    sudo cp -r uploads/* /data/tongshi/uploads/
    
    # 修复权限
    sudo chown -R www-data:www-data /data/tongshi/uploads
    
    # 验证迁移
    echo "新目录文件数："
    find /data/tongshi/uploads/ -type f | wc -l
    
    echo "旧目录文件数："
    find uploads/ -type f | wc -l
    
    # ⚠️ 验证无误后再删除旧文件
    # sudo rm -rf uploads/
else
    echo "项目目录无旧文件"
fi
```

### Step 3：修改 .env 配置

```bash
cd /opt/tongshi/backend

# 备份原配置
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 修改配置
sudo vim .env
```

**确保以下配置正确：**
```bash
# 文件存储配置
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=/data/tongshi/uploads
```

### Step 4：修改 Nginx 配置（如果使用）

```bash
# 检查 Nginx 配置
sudo cat /etc/nginx/sites-available/tongshi
```

**确保路径一致：**
```nginx
# ✅ 正确配置
location /_protected_uploads/ {
    internal;
    alias /data/tongshi/uploads/;  # ← 与 .env 一致
    sendfile on;
    tcp_nopush on;
    aio threads;
    add_header Accept-Ranges bytes;
    add_header Cache-Control "private, max-age=0";
}
```

如果需要修改：
```bash
sudo vim /etc/nginx/sites-available/tongshi
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

### Step 5：重启后端服务

```bash
# 使用 systemd
sudo systemctl restart tongshi-backend

# 或使用 supervisor
sudo supervisorctl restart tongshi-backend

# 验证服务启动
sudo systemctl status tongshi-backend
```

### Step 6：验证修复

```bash
# 1. 检查后端日志
sudo journalctl -u tongshi-backend -n 50

# 2. 测试文件上传
curl -X POST http://localhost:8050/api/upload \
  -H "Authorization: Bearer <your_token>" \
  -F "file=@test.jpg"

# 3. 检查文件是否在正确位置
ls -la /data/tongshi/uploads/

# 4. 检查数据库记录
mysql -u tongshi_user -p tongshi -e "SELECT COUNT(*) FROM stored_files;"
```

---

## 防止文件再次丢失

### 1. 设置自动备份

创建备份脚本 `/data/tongshi/backup_uploads.sh`：

```bash
#!/bin/bash
# 文件存储自动备份脚本

UPLOAD_DIR="/data/tongshi/uploads"
BACKUP_DIR="/data/tongshi/backups/uploads"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uploads_$DATE.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 压缩备份
echo "开始备份上传文件..."
tar -czf "$BACKUP_FILE" -C /data/tongshi uploads/

# 保留最近 7 天的备份
find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_FILE"
echo "备份大小: $(du -h $BACKUP_FILE | cut -f1)"
```

设置定时任务：
```bash
# 编辑 crontab
sudo crontab -e

# 每天凌晨 2 点备份
0 2 * * * /data/tongshi/backup_uploads.sh >> /var/log/tongshi_backup.log 2>&1
```

### 2. 设置文件数量监控

创建监控脚本 `/data/tongshi/check_files.sh`：

```bash
#!/bin/bash
# 文件数量监控脚本

UPLOAD_DIR="/data/tongshi/uploads"
FILE_COUNT=$(find "$UPLOAD_DIR" -type f | wc -l)
ALERT_FILE="/tmp/tongshi_file_count.txt"

# 读取上次记录
if [ -f "$ALERT_FILE" ]; then
    LAST_COUNT=$(cat "$ALERT_FILE")
else
    LAST_COUNT=0
fi

# 检查文件数量是否大幅减少（减少超过 10%）
if [ $FILE_COUNT -lt $((LAST_COUNT * 90 / 100)) ]; then
    echo "警告：文件数量从 $LAST_COUNT 减少到 $FILE_COUNT"
    # 这里可以发送邮件或钉钉通知
fi

# 更新记录
echo $FILE_COUNT > "$ALERT_FILE"
```

设置定时检查：
```bash
# 每小时检查一次
0 * * * * /data/tongshi/check_files.sh >> /var/log/tongshi_monitor.log 2>&1
```

### 3. Git 操作安全规范

**服务器上更新代码时，永远不要使用以下命令：**
```bash
# ❌ 危险命令
git clean -fd              # 会删除未跟踪文件
git reset --hard           # 会丢弃所有本地修改
git checkout -- .          # 会还原工作区
```

**安全的更新流程：**
```bash
# ✅ 安全流程
cd /opt/tongshi

# 1. 查看当前状态
git status

# 2. 如果有本地修改需要保留
git stash

# 3. 拉取最新代码
git pull origin main

# 4. 恢复本地修改（如果需要）
git stash pop

# 5. 重启服务
sudo systemctl restart tongshi-backend
sudo systemctl restart nginx
```

---

## 一键检查脚本

创建 `/opt/tongshi/backend/scripts/check_file_storage.sh`：

```bash
#!/bin/bash
# 文件存储配置检查脚本

echo "================================"
echo "文件存储配置检查"
echo "================================"

# 1. 检查 .env 配置
echo -e "\n[1] .env 配置："
if [ -f ".env" ]; then
    LOCAL_UPLOAD_DIR=$(grep "^LOCAL_UPLOAD_DIR=" .env | cut -d'=' -f2)
    echo "LOCAL_UPLOAD_DIR=$LOCAL_UPLOAD_DIR"
    
    if [[ "$LOCAL_UPLOAD_DIR" == /* ]]; then
        echo "✅ 使用绝对路径"
    else
        echo "❌ 警告：应使用绝对路径"
    fi
else
    echo "❌ .env 文件不存在"
fi

# 2. 检查目录是否存在
echo -e "\n[2] 目录检查："
if [ -d "$LOCAL_UPLOAD_DIR" ]; then
    echo "✅ 目录存在: $LOCAL_UPLOAD_DIR"
    
    # 检查权限
    OWNER=$(stat -c '%U:%G' "$LOCAL_UPLOAD_DIR")
    PERMS=$(stat -c '%a' "$LOCAL_UPLOAD_DIR")
    echo "   所有者: $OWNER"
    echo "   权限: $PERMS"
    
    # 检查文件数量
    FILE_COUNT=$(find "$LOCAL_UPLOAD_DIR" -type f | wc -l)
    TOTAL_SIZE=$(du -sh "$LOCAL_UPLOAD_DIR" | cut -f1)
    echo "   文件数量: $FILE_COUNT"
    echo "   总大小: $TOTAL_SIZE"
else
    echo "❌ 目录不存在: $LOCAL_UPLOAD_DIR"
fi

# 3. 检查数据库记录
echo -e "\n[3] 数据库文件记录："
MYSQL_HOST=$(grep "^MYSQL_HOST=" .env | cut -d'=' -f2)
MYSQL_USER=$(grep "^MYSQL_USER=" .env | cut -d'=' -f2)
MYSQL_PASSWORD=$(grep "^MYSQL_PASSWORD=" .env | cut -d'=' -f2)
MYSQL_DATABASE=$(grep "^MYSQL_DATABASE=" .env | cut -d'=' -f2)

if [ -n "$MYSQL_HOST" ]; then
    DB_COUNT=$(mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" \
        -e "SELECT COUNT(*) FROM stored_files;" -sN 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "数据库记录: $DB_COUNT 个文件"
        
        if [ $FILE_COUNT -lt $DB_COUNT ]; then
            echo "⚠️  警告：实际文件少于数据库记录 (差异: $((DB_COUNT - FILE_COUNT)))"
        else
            echo "✅ 文件数量正常"
        fi
    else
        echo "❌ 数据库连接失败"
    fi
fi

# 4. 检查项目目录是否有残留文件
echo -e "\n[4] 项目目录检查："
if [ -d "uploads" ]; then
    PROJECT_FILE_COUNT=$(find uploads -type f | wc -l)
    if [ $PROJECT_FILE_COUNT -gt 0 ]; then
        echo "⚠️  警告：项目目录内发现 $PROJECT_FILE_COUNT 个文件"
        echo "   建议迁移到: $LOCAL_UPLOAD_DIR"
    else
        echo "✅ 项目目录无文件"
    fi
else
    echo "✅ 项目目录无 uploads/"
fi

echo -e "\n================================"
echo "检查完成"
echo "================================"
```

赋予执行权限并运行：
```bash
chmod +x /opt/tongshi/backend/scripts/check_file_storage.sh
cd /opt/tongshi/backend
./scripts/check_file_storage.sh
```

---

## 常见问题

### Q1：文件已经丢失，能恢复吗？

**答案**：取决于是否有备份。

**恢复方法：**
1. 检查服务器备份（如果有快照或自动备份）
2. 检查数据库备份
3. 联系用户重新上传（最差情况）

### Q2：为什么不能用相对路径？

```bash
# ❌ 相对路径的问题
LOCAL_UPLOAD_DIR=./uploads

# 当前目录：/opt/tongshi/backend
# 实际路径：/opt/tongshi/backend/uploads  ← 在项目内

# 如果切换目录后启动服务
cd /opt/tongshi
python backend/main.py
# 实际路径：/opt/tongshi/uploads  ← 路径变了！
```

### Q3：2G2核服务器需要多少存储空间？

**建议配置：**
- 系统盘：20GB（系统 + 代码 + 软件）
- 数据盘：50-100GB（文件存储）

**文件增长预估（教育平台）：**
- 课程资料：每个课程 50-200MB
- 学生作品：每个学生 10-50MB
- 100 个学生 + 10 个课程 = **约 5-10GB**

### Q4：需要升级到 SeaweedFS 吗？

**2G2核服务器：不需要！**

- ✅ 使用 local 存储 + 独立目录
- ✅ 定期备份到对象存储（如阿里云 OSS）
- ✅ 等用户量增长到 1000+ 再考虑

---

## 总结

### ✅ 正确配置

```bash
# 服务器目录结构
/data/tongshi/
├── uploads/              # 文件存储（独立）
│   ├── xxx.pdf
│   └── yyy.jpg
└── backups/
    └── uploads/          # 自动备份

/opt/tongshi/             # 项目代码（独立）
├── backend/
│   ├── .env             # LOCAL_UPLOAD_DIR=/data/tongshi/uploads
│   └── ...
└── frontend/
```

### ❌ 错误配置

```bash
# 危险架构
/opt/tongshi/
├── backend/
│   ├── uploads/         # ❌ 文件在项目内
│   ├── .gitignore       # ❌ uploads/ 被忽略
│   └── .env             # ❌ LOCAL_UPLOAD_DIR=./uploads
└── .git/
```

### 🔑 关键检查点

1. ✅ `.env` 中 `LOCAL_UPLOAD_DIR` 使用绝对路径
2. ✅ 存储目录在项目外（如 `/data/tongshi/uploads`）
3. ✅ 目录权限正确（www-data:www-data 755）
4. ✅ Nginx 配置路径与 `.env` 一致
5. ✅ 设置自动备份
6. ✅ 服务器更新代码时避免 `git clean -fd`

---

## 立即行动

```bash
# 1. SSH 登录服务器
ssh user@your-server

# 2. 执行检查脚本
cd /opt/tongshi/backend
bash scripts/check_file_storage.sh

# 3. 根据输出结果修复问题

# 4. 设置备份（可选但强烈推荐）
```
