<template>
  <div class="mobile-metadata-locker">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">元数据锁定管理</h1>
      <p class="page-desc">管理 Emby 的主锁与小锁状态</p>
    </div>

    <!-- 配置卡片 -->
    <n-card class="config-card" :bordered="false" title="执行参数">
      <n-space vertical>
        <n-form-item label="目标媒体库">
          <n-select 
            v-model:value="common.lib_names" 
            multiple 
            filterable 
            :options="libOptions"
            placeholder="选择媒体库" 
          />
        </n-form-item>

        <n-form-item label="媒体类型">
          <n-checkbox-group v-model:value="selectedTypes">
            <n-space>
              <n-checkbox value="Movie">电影</n-checkbox>
              <n-checkbox value="Series">剧集</n-checkbox>
              <n-checkbox value="Season">季</n-checkbox>
              <n-checkbox value="Episode">集</n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-form-item>

        <div class="mode-row">
          <n-radio-group v-model:value="common.dry_run" size="large">
            <n-radio-button :value="true">预览模式</n-radio-button>
            <n-radio-button :value="false">实调模式</n-radio-button>
          </n-radio-group>
        </div>
      </n-space>
    </n-card>

    <!-- 操作卡片 -->
    <n-card class="action-card" :bordered="false" title="锁定操作">
      <n-space vertical>
        <!-- 字段锁解除 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-header">
            <div class="tool-title">元数据字段全解锁</div>
            <n-tag type="error" size="small">深度释放</n-tag>
          </div>
          <p class="tool-desc">清空 LockedFields 列表并设置 LockData = false</p>
          <n-button 
            block 
            type="error" 
            secondary 
            :loading="loading"
            @click="handleAction('metadata_field_unlocker')"
          >
            <template #icon><n-icon><UnlockIcon /></n-icon></template>
            执行字段解锁
          </n-button>
        </n-card>

        <!-- 主锁开启 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-header">
            <div class="tool-title">项目整体锁定</div>
            <n-tag type="info" size="small">主锁保护</n-tag>
          </div>
          <p class="tool-desc">设置 LockData = true，保护整体元数据</p>
          <n-button 
            block 
            type="info" 
            secondary 
            :loading="loading"
            @click="handleAction('item_locker')"
          >
            <template #icon><n-icon><LockIcon /></n-icon></template>
            执行全局锁定
          </n-button>
        </n-card>

        <!-- 全局彻底解锁 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-header">
            <div class="tool-title">项目深度全解锁</div>
            <n-tag type="success" size="small">彻底释放</n-tag>
          </div>
          <p class="tool-desc">主锁、小锁一起解除</p>
          <n-button 
            block 
            type="success" 
            secondary 
            :loading="loading"
            @click="handleAction('item_unlocker')"
          >
            <template #icon><n-icon><ResetIcon /></n-icon></template>
            执行深度解锁
          </n-button>
        </n-card>
      </n-space>
    </n-card>

    <!-- 说明卡片 -->
    <n-card class="info-card" :bordered="false" title="概念区分">
      <n-space vertical>
        <n-alert type="info" :bordered="false">
          <b>主锁 (LockData):</b> Emby 控制面板中"将此项目锁定以防意外更改"的总开关
        </n-alert>
        <n-alert type="warning" :bordered="false">
          <b>小锁 (LockedFields):</b> 各具体字段（标题、简介、海报等）的细粒度锁定列表
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { 
  NCard, NButton, NSelect, NCheckboxGroup, NCheckbox, 
  NRadioGroup, NRadioButton, NIcon, NSpace, NTag, NAlert
} from 'naive-ui'
import {
  LockOpenOutlined as UnlockIcon,
  LockOutlined as LockIcon,
  LockResetOutlined as ResetIcon
} from '@vicons/material'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const libOptions = ref([])
const selectedTypes = ref(['Movie', 'Series', 'Season', 'Episode'])

const savedCommon = localStorage.getItem('lens_lock_common')
const common = reactive(savedCommon ? JSON.parse(savedCommon) : {
  lib_names: [],
  dry_run: true
})

watch(common, (val) => {
  localStorage.setItem('lens_lock_common', JSON.stringify(val))
}, { deep: true })

const fetchLibraries = async () => {
  try {
    const res = await axios.get('/api/server/libraries')
    libOptions.value = res.data
  } catch (e) {}
}

onMounted(fetchLibraries)

const handleAction = async (endpoint: string) => {
  if (common.lib_names.length === 0) {
    message.warning('请选择媒体库')
    return
  }
  loading.value = true
  try {
    const res = await axios.post(`/api/toolkit/${endpoint}`, {
      ...common,
      item_types: selectedTypes.value
    })
    message.success(`任务完成: ${res.data.message} (处理数: ${res.data.processed_count})`)
  } catch (e) {
    message.error('接口请求失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mobile-metadata-locker {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.config-card,
.action-card,
.info-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.tool-card {
  background: var(--app-bg-color);
  border-radius: 12px;
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tool-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
}

.tool-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0 0 12px 0;
}

.mode-row {
  padding: 12px 0;
}
</style>
