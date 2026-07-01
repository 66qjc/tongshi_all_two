<template>
  <div class="lesson-editor">
    <Toolbar
      class="lesson-editor-toolbar"
      :editor="editorRef"
      :default-config="toolbarConfig"
      mode="default"
    />
    <Editor
      class="lesson-editor-content"
      :model-value="modelValue"
      :default-config="editorConfig"
      mode="default"
      @update:model-value="(val: string) => emit('update:modelValue', val)"
      @on-created="handleCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import {
  Boot,
  type IDomEditor,
  type IEditorConfig,
  type IToolbarConfig,
  type IButtonMenu,
} from '@wangeditor/editor'
import '@wangeditor/editor/dist/css/style.css'

import { uploadFile } from '@/api/upload'

const props = withDefaults(
  defineProps<{
    modelValue?: string
  }>(),
  {
    modelValue: '',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'insert-material'): void
}>()

const lessonEditorMenuState = globalThis as typeof globalThis & {
  __lessonInsertMaterialMenuRegistered?: boolean
}

class InsertMaterialMenu implements IButtonMenu {
  title = '插入资料'
  tag = 'button'
  iconSvg =
    '<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path d="M832 128H192c-35.2 0-64 28.8-64 64v640c0 35.2 28.8 64 64 64h640c35.2 0 64-28.8 64-64V192c0-35.2-28.8-64-64-64zM192 192h640v640H192V192zm128 128h384v64H320v-64zm0 192h384v64H320v-64zm0 192h256v64H320v-64z"/></svg>'

  getValue(editor: IDomEditor): string | boolean {
    editor // 避免未使用参数警告
    return ''
  }

  isActive(): boolean {
    return false
  }

  isDisabled(editor: IDomEditor): boolean {
    editor // 避免未使用参数警告
    return false
  }

  exec(editor: IDomEditor): void {
    if (this.isDisabled(editor)) return
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(editor as any).emit('insert-material')
  }
}

function registerInsertMaterialMenu() {
  if (lessonEditorMenuState.__lessonInsertMaterialMenuRegistered) return
  Boot.registerMenu({
    key: 'insertMaterial',
    factory: () => new InsertMaterialMenu(),
  })
  lessonEditorMenuState.__lessonInsertMaterialMenuRegistered = true
}

registerInsertMaterialMenu()

// 工具栏：标题、加粗、斜体、无序/有序列表、引用、代码块、链接、图片、视频、插入资料
const toolbarConfig: Partial<IToolbarConfig> = {
  toolbarKeys: [
    'headerSelect',
    '|',
    'bold',
    'italic',
    '|',
    'bulletedList',
    'numberedList',
    '|',
    'blockquote',
    'codeBlock',
    '|',
    'insertLink',
    'insertImage',
    'insertVideo',
    '|',
    'insertMaterial',
  ],
  modalAppendToBody: true,
}

const editorConfig: Partial<IEditorConfig> = {
  placeholder: '请输入课时内容，支持图文混排、插入视频/PDF 资料...',
  MENU_CONF: {
    uploadImage: {
      async customUpload(
        file: File,
        insertFn: (src: string, alt: string, href: string) => void,
      ) {
        try {
          const result = await uploadFile(file, 'lesson-image')
          insertFn(result.url, result.filename || file.name, result.url)
        } catch (error) {
          ElMessage.error('图片上传失败，请重试')
        }
      },
    },
  },
}

const editorRef = shallowRef<IDomEditor | null>(null)

const handleInsertMaterial = () => {
  emit('insert-material')
}

function handleCreated(editor: IDomEditor) {
  editorRef.value = editor
  editor.on('insert-material', handleInsertMaterial)
}

/**
 * 在光标处插入资料占位符
 * 父组件监听 insert-material 事件后，选择资料并调用此方法
 */
function insertMaterialPlaceholder(
  materialId: number,
  materialType: 'video' | 'pdf',
) {
  const editor = editorRef.value
  if (!editor || editor.isDestroyed) return

  editor.focus()
  editor.dangerouslyInsertHtml(
    `<div class="lesson-material" data-material-id="${materialId}" data-material-type="${materialType}"></div>`,
  )
}

onBeforeUnmount(() => {
  const editor = editorRef.value
  if (!editor || editor.isDestroyed) return

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(editor as any).off('insert-material', handleInsertMaterial)
  editor.destroy()
})

defineExpose({
  insertMaterialPlaceholder,
})
</script>

<style scoped>
.lesson-editor {
  display: flex;
  flex-direction: column;
  height: 400px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.lesson-editor-toolbar {
  border-bottom: 1px solid #dcdfe6;
}

.lesson-editor-content {
  flex: 1;
  overflow-y: hidden;
}
</style>
