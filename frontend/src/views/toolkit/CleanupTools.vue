<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">媒体净化清理</n-text></n-h2>
        <n-text depth="3">支持指定媒体库与媒体类型，执行演职员移除或剧集类型重置，保持媒体库整洁。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要功能区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 全局配置 -->
            <n-card title="通用执行参数" size="small" segmented>
              <n-form label-placement="left" label-width="120">
                <n-form-item label="目标媒体库">
                  <n-select 
                    v-model:value="common.lib_names" 
                    multiple 
                    filterable 
                    :options="libOptions"
                    placeholder="自动拉取媒体库列表中..." 
                  />
                </n-form-item>
                <n-form-item label="执行模式">
                  <n-switch v-model:value="common.dry_run">
                    <template #checked>预览模式</template>
                    <template #unchecked>实调模式</template>
                  </n-switch>
                </n-form-item>
              </n-form>
            </n-card>

            <!-- 2. 原子工具卡片 -->
            <n-grid :cols="2" :x-gap="12" :y-gap="12" item-responsive responsive="screen">
              <n-gi span="2 m:1">
                <n-card title="演职员信息清空" size="small" style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-space vertical>
                    <n-text depth="3" style="font-size: 12px">操作媒体类型：</n-text>
                    <n-checkbox-group v-model:value="peopleItemTypes">
                      <n-space>
                        <n-checkbox value="Movie">电影</n-checkbox>
                        <n-checkbox value="Series">剧集</n-checkbox>
                      </n-space>
                    </n-checkbox-group>
                  </n-space>
                  <div style="margin-top: 16px">
                    <n-divider style="margin: 8px 0" />
                    <n-button block type="error" secondary @click="handleAction('people_remover')" :loading="loading">
                      执行清空演职员
                    </n-button>
                  </div>
                </n-card>
              </n-gi>

              <n-gi span="2 m:1">
                <n-card title="集类型(Episode)重置" size="small" style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-p depth="3" style="font-size: 12px">
                    扫描指定媒体库中的所有剧集，清除“集”层级的 Genres 标签。
                  </n-p>
                  <div style="margin-top: 16px">
                    <n-divider style="margin: 8px 0" />
                    <n-button block type="primary" secondary @click="handleAction('episode_deleter')" :loading="loading">
                      执行修复重置
                    </n-button>
                  </div>
                </n-card>
              </n-gi>
            </n-grid>
          </n-space>
        </n-gi>

        <!-- 右侧：说明区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="工具说明" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                <b>演职员清空：</b><br/>
                主要用于清理因刮削器错误导致的冗余演职员列表，清空后建议在 Emby 中重新识别。<br/><br/>
                <b>集类型重置：</b><br/>
                修复某些剧集的“单集”被错误打上“剧集类型”标签的问题。
              </n-text>
            </n-card>

            <n-card title="操作技巧" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                建议搭配“实时日志”使用。在执行大规模清理前，请务必确认“目标媒体库”选择正确。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  NSpace, NH2, NText, NCard, NP, NButton, NGrid, NGi, 
  NCheckboxGroup, NCheckbox, NSwitch, NForm, NFormItem, NSelect, NDivider, NIcon 
} from 'naive-ui'
// 导入提取的逻辑
import { useCleanupTools } from './cleanup/hooks/useCleanupTools'

const { 
  loading, libOptions, common, peopleItemTypes, 
  fetchLibraries, handleAction 
} = useCleanupTools()

onMounted(fetchLibraries)
</script>

<style scoped>
</style>