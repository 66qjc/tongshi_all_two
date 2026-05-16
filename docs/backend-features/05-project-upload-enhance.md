# 作品上传增强 - 后端需求

## 数据模型修改

### 修改 projects 表
新增字段：
| 字段 | 类型 | 说明 |
|------|------|------|
| link_url | String(512) default "" | 任意外链（GitHub、博客、在线演示等） |

## Schema 修改

ProjectOut 和 ProjectCreate 均新增：
```python
link_url: str = ""
```

## API 端点

### 修改现有端点
- POST /api/projects：请求体新增 link_url 可选字段
- GET /api/projects 系列：响应包含 link_url

### 新增批量下载
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/teacher/projects/batch-download | teacher | 批量下载已通过作品的 PDF 报告（ZIP） |

## 批量下载逻辑

1. 查询所有 status='approved' 且 report_url 非空的 Project
2. 遍历 report_url，从 uploads/ 目录读取对应文件
3. 使用 zipfile 模块打包为 ZIP（内存中）
4. 返回 StreamingResponse，Content-Type 为 application/zip
5. 文件名格式：`作品报告_{日期}.zip`
6. ZIP 内文件命名：`{作者名}_{作品标题}.pdf`

## 前端调用注意

批量下载接口返回二进制文件，前端不能走 Axios 拦截器（会尝试解析 JSON）。
应使用 `window.open(url)` 或 `<a>` 标签直接下载，URL 需带 JWT token 作为 query 参数或使用单独的下载 token 机制。
