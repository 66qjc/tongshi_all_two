# AI 通识教育课程平台前端

本目录是 Vue 3 + TypeScript + Vite + Element Plus 前端工程，包含学生端和教师端页面。

## 主要页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/learn` | `src/views/LearnView.vue` | 学生端课程列表 |
| `/learn/course/:courseId` | `src/views/CourseDetailView.vue` | 学生端课程详情页 |
| `/learn/:chapterId` | `src/views/ChapterView.vue` | 章节学习页，展示视频和 PDF |
| `/teacher/materials` | `src/views/teacher/TeacherMaterials.vue` | 教师端资料、课程、章节和排课管理 |

## API 封装

| 文件 | 说明 |
|------|------|
| `src/api/course.ts` | 课程列表、课程详情、课程增删改 |
| `src/api/chapter.ts` | 章节列表、章节增删改、章节排课 |
| `src/api/material.ts` | 学习资料列表、上传后登记、删除 |
| `src/api/upload.ts` | 通用文件上传 |

课程体系的前端关系：

- 教师端在“资料管理”页维护课程、章节、资料和课程时间安排。
- 学生端先进入课程列表，再进入课程详情查看章节。
- 章节学习仍复用原 `/learn/:chapterId` 页面。

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```
