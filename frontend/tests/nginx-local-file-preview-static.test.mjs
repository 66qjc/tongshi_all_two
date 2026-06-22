import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const nginxConfig = readFileSync(resolve(root, 'deploy/nginx.conf'), 'utf8')

assert.match(nginxConfig, /upstream\s+backend\s*\{[\s\S]*127\.0\.0\.1:8050/, 'Nginx 应把后端 upstream 指向本机 8050。')
assert.match(nginxConfig, /location\s+\/api\/\s*\{[\s\S]*proxy_pass\s+http:\/\/backend/, 'Nginx 应代理 /api/ 到后端。')
assert.match(nginxConfig, /location\s+\/uploads\/\s*\{[\s\S]*proxy_pass\s+http:\/\/backend/, 'Nginx 应代理 /uploads/ 到后端兼容旧文件地址。')
assert.match(nginxConfig, /proxy_set_header\s+Range\s+\$http_range/, 'Nginx 文件代理应透传 Range 请求。')
assert.match(nginxConfig, /proxy_set_header\s+If-Range\s+\$http_if_range/, 'Nginx 文件代理应透传 If-Range 请求。')
assert.match(nginxConfig, /client_max_body_size\s+1024m/, 'Nginx 上传限制应覆盖当前视频上传上限。')

console.log('nginx local file preview static checks passed')
