<template>
  <div class="mobile-cleanup-tools">
    <div class="page-header">
      <h1 class="page-title">媒体净化清理</h1>
      <p class="page-desc">执行演职员移除或剧集类型重置</p>
    </div>

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
        <div class="mode-row">
          <n-radio-group v-model:value="common.dry_run" size="large">
            <n-radio-button :value="true">预览模式</n-radio-button>
            <n-radio-button :value="false">实调模式</n-radio-button>
          </n-radio-group>
        </div>
      </n-space>
    </n-card>

    <n-card class="action-card" :bordered="false" title="清理工具">
      <n-space vertical>
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-title">演职员信息清空</div>
          <p class="tool-desc">清理因刮削器错误导致的冗余演职员列表</p>
          <n-checkbox-group v-model:value="peopleItemTypes" class="type-select">
            <n-space>
              <n-checkbox value="Movie">电影</n-checkbox>
              <n-checkbox value="Series">剧集</n-checkbox>
            </n-space>
          </n-checkbox-group>
          <n-button 
            block 
            type="error" 
            secondary 
            :loading="loading"
            @click="handleAction('people_remover')"
          >
            执行清空演职员
          </n-button>
        </n-card>

        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-title">集类型(Episode)重置</div>
          <p class="tool-desc">清除"集"层级的 Genres 标签</p>
          <n-button 
            block 
            type="primary" 
            secondary 
            :loading="loading"
            @click="handleAction('episode_deleter')"
          >
            执行修复重置
          </n-button>
        </n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  NCard, NButton, NSelect, NCheckboxGroup, NCheckbox, 
  NRadioGroup, NRadioButton, NIcon, NSpace
} from 'naive-ui'
import {
  PersonRemoveOutlined as DeleteIcon,
  BuildCircleOutlined as FixIcon
} from '@vicons/material'
import { useCleanupTools } from '../../toolkit/cleanup/hooks/useCleanupTools'

const { 
  loading, libOptions, common, peopleItemTypes, 
  fetchLibraries, handleAction 
} = useCleanupTools()

onMounted(fetchLibraries)
</script>

<style scoped>
.mobile-cleanup-tools {
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
.action-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.tool-card {
  background: var(--app-bg-color);
  border-radius: 12px;
}

.tool-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 8px;
}

.tool-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0 0 12px 0;
}

.type-select {
  margin-bottom: 12px;
}

.mode-row {
  padding: 12px 0;
}
</style>
