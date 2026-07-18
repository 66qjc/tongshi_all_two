import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCheckbox,
  ElCollapse,
  ElCollapseItem,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElRate,
  ElSelect,
  ElSegmented,
  ElSkeleton,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
  provideGlobalConfig,
} from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { Loading } from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

const app = createApp(App)

const elementPlusComponents = [
  ElAlert,
  ElButton,
  ElCard,
  ElCheckbox,
  ElCollapse,
  ElCollapseItem,
  ElDatePicker,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElOption,
  ElPagination,
  ElPopconfirm,
  ElProgress,
  ElRadioButton,
  ElRadioGroup,
  ElRate,
  ElSelect,
  ElSegmented,
  ElSkeleton,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
]

app.use(createPinia())
app.use(router)
elementPlusComponents.forEach(component => {
  app.use(component)
})
app.component('el-radio-group', ElRadioGroup)
app.component('el-radio-button', ElRadioButton)
app.use(ElLoading)
provideGlobalConfig({ locale: zhCn }, app, true)
app.component('Loading', Loading)

app.mount('#app')
