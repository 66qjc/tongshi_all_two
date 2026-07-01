/// <reference types="vite/client" />

// @wangeditor/editor-for-vue 的 package.json exports 缺少 types，补充模块声明以通过类型检查
declare module '@wangeditor/editor-for-vue' {
    import type { Component } from 'vue'
    export const Editor: Component
    export const Toolbar: Component
}
