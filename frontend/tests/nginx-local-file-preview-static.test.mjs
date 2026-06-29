import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const nginxConfig = readFileSync(resolve(root, 'deploy/nginx.conf'), 'utf8')

assert.match(nginxConfig, /upstream\s+tongshi_backend\s*\{[\s\S]*127\.0\.0\.1:8050/, 'Nginx 应把后端 upstream 指向本机 8050。')
assert.match(nginxConfig, /location\s+\/api\/\s*\{[\s\S]*proxy_pass\s+http:\/\/tongshi_backend/, 'Nginx 应代理 /api/ 到后端。')
assert.match(nginxConfig, /location\s+\/uploads\/\s*\{[\s\S]*proxy_pass\s+http:\/\/tongshi_backend/, 'Nginx 应代理 /uploads/ 到后端兼容旧文件地址。')
assert.match(nginxConfig, /proxy_set_header\s+Range\s+\$http_range/, 'Nginx 文件代理应透传 Range 请求。')
assert.match(nginxConfig, /proxy_set_header\s+If-Range\s+\$http_if_range/, 'Nginx 文件代理应透传 If-Range 请求。')
assert.match(nginxConfig, /client_max_body_size\s+1024m/, 'Nginx 上传限制应覆盖当前视频上传上限。')

assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*internal;/, 'Nginx 应配置内部受保护上传目录。')
assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*alias\s+\/var\/www\/tongshi\/uploads\//, 'Nginx 内部上传目录应映射到生产上传目录。')
assert.match(nginxConfig, /location\s+\/_protected_uploads\/\s*\{[\s\S]*sendfile\s+on;/, 'Nginx 内部文件传输应启用 sendfile。')

console.log('nginx local file preview static checks passed')
