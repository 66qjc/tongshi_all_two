import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const uploadApi = readFileSync(resolve(root, 'src/api/upload.ts'), 'utf8')
const uploadComposable = readFileSync(resolve(root, 'src/composables/useUploadWithProgress.ts'), 'utf8')
const teacherPage = readFileSync(resolve(root, 'src/views/teacher/TeacherCourseDetail.vue'), 'utf8')
const adminPage = readFileSync(resolve(root, 'src/views/admin/AdminPublicCourses.vue'), 'utf8')

assert.match(uploadApi, /const VIDEO_UPLOAD_TIMEOUT = 60 \* 60 \* 1000/, '视频上传必须单独使用 60 分钟超时')
assert.match(uploadApi, /videoUpload: boolean = false/, '通用上传默认不得启用长视频策略')
assert.match(uploadApi, /const isVideo = videoUpload && isVideoUpload\(file\)[\s\S]*timeout: isVideo \? VIDEO_UPLOAD_TIMEOUT : undefined/, '普通上传不得覆盖全局 10 秒超时')
assert.match(uploadApi, /formData\.append\('expected_size', String\(file\.size\)\)/, '视频上传必须提交预估文件大小')
assert.match(uploadApi, /MAX_VIDEO_UPLOAD_SIZE = 1024 \* 1024 \* 1024/, '前端视频上限必须保持为 1GiB')
assert.match(uploadComposable, /uploadFile\([\s\S]*file,[\s\S]*bizType,[\s\S]*true,[\s\S]*\)/, '课程资料上传必须显式启用长视频策略')
assert.match(teacherPage, /validateCourseMaterialUpload/, '教师端选取资料时必须校验视频大小')
assert.match(adminPage, /validateCourseMaterialUpload/, '管理员端选取资料时必须校验视频大小')

console.log('video upload static checks passed')
