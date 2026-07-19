<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">TMDB ID 深度搜索</n-text></n-h2>
        <n-text depth="3">根据 TMDB ID <b>在您的 Emby 库中</b>递归检索匹配的项目及其所有季、集的完整元数据详情。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要功能区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 搜索配置 -->
            <n-card title="检索配置" size="small">
              <n-space vertical size="medium">
                <n-input-group>
                  <n-input-group-label style="width: 100px">TMDB ID</n-input-group-label>
                  <n-input v-model:value="form.tmdb_id" placeholder="输入 ID (如: 94359)" @keyup.enter="handleSearch" />
                  <n-button type="primary" @click="handleSearch" :loading="loading">
                    执行搜索
                  </n-button>
                </n-input-group>
                <n-space align="center">
                  <n-text depth="3">检索范围:</n-text>
                  <n-checkbox-group v-model:value="searchTypes">
                    <n-space>
                      <n-checkbox value="movies">电影</n-checkbox>
                      <n-checkbox value="series">剧集</n-checkbox>
                    </n-space>
                  </n-checkbox-group>
                </n-space>
              </n-space>
            </n-card>

            <!-- 2. 结果展示区 -->
            <div v-if="results.length > 0" class="results-area">
              <n-h3>搜索结果 ({{ results.length }})</n-h3>
              <n-collapse accordion :default-expanded-names="results[0].Id">
                <n-collapse-item v-for="item in results" :key="item.Id" :name="item.Id">
                  <!-- 剧集标题栏 -->
                  <template #header>
                    <n-space align="center" style="width: 100%" justify="space-between">
                      <n-space align="center">
                        <n-text strong style="font-size: 16px">{{ item.Name }}</n-text>
                        <n-tag size="small" type="primary" round quaternary>{{ item.ProductionYear }}</n-tag>
                        <n-tag size="small" :type="item.Type === 'Series' ? 'info' : 'success'">{{ item.Type }}</n-tag>
                      </n-space>
                      <n-button quaternary circle size="small" type="primary" @click.stop="showJson(item)" title="本体 JSON">
                        <template #icon><n-icon><DocumentTextIcon /></n-icon></template>
                      </n-button>
                    </n-space>
                  </template>
                  
                  <n-card :bordered="false" size="small" embedded style="margin-top: 8px">
                    <!-- 剧集/电影 详情描述 -->
                    <n-descriptions label-placement="left" :column="2" size="small" bordered label-style="width: 120px">
                      <n-descriptions-item label="名称">{{ item.Name }}</n-descriptions-item>
                      <n-descriptions-item label="类型">{{ item.Type }}</n-descriptions-item>
                      <n-descriptions-item label="Emby ID">{{ item.Id }}</n-descriptions-item>
                      <n-descriptions-item label="路径" :span="2">{{ item.Path }}</n-descriptions-item>
                      <n-descriptions-item label="提供者 ID" :span="2">
                        <n-space>
                          <n-tag v-for="(val, key) in item.ProviderIds" :key="key" size="tiny" type="info" quaternary>
                            {{ key }}: {{ val }}
                          </n-tag>
                        </n-space>
                      </n-descriptions-item>
                      <n-descriptions-item label="评分与分级">
                        <n-rate readonly :default-value="Math.round(item.CommunityRating || 0) / 2" size="small" />
                        <n-text depth="3" style="margin-left: 8px">{{ item.CommunityRating }} / {{ item.OfficialRating || 'NR' }}</n-text>
                      </n-descriptions-item>
                      <n-descriptions-item label="发行商/状态">
                        {{ item.Studios?.[0]?.Name || 'N/A' }} | {{ item.Status || 'Ended' }}
                      </n-descriptions-item>
                      <n-descriptions-item label="日期信息" :span="2">
                        首播: {{ item.PremiereDate?.split('T')[0] || 'N/A' }} 
                        <span v-if="item.EndDate"> | 结束: {{ item.EndDate?.split('T')[0] }}</span>
                      </n-descriptions-item>
                    </n-descriptions>

                    <div class="overview-box" style="margin-top: 12px">
                      <n-p depth="3" style="font-size: 13px">{{ item.Overview || '暂无简介' }}</n-p>
                    </div>

                    <!-- 递归层级：季 (Season) -->
                    <div v-if="item.Seasons && item.Seasons.length > 0" style="margin-top: 24px">
                      <n-divider title-placement="left"><n-text type="primary" strong>季与集 详细递归结构</n-text></n-divider>
                      <n-collapse>
                        <n-collapse-item v-for="season in item.Seasons" :key="season.Id" :name="season.Id">
                          <template #header>
                            <n-space justify="space-between" style="width: 100%" align="center">
                              <n-text strong>{{ season.Name }} (ID: {{ season.Id }})</n-text>
                              <n-button quaternary circle size="tiny" type="info" @click.stop="showJson(season)">
                                <template #icon><n-icon><DocumentTextIcon /></n-icon></template>
                              </n-button>
                            </n-space>
                          </template>
                          
                          <!-- 季 详情 -->
                          <n-descriptions label-placement="left" :column="2" size="small" style="padding: 0 16px">
                            <n-descriptions-item label="季号">{{ season.IndexNumber }}</n-descriptions-item>
                            <n-descriptions-item label="父 ID">{{ season.ParentId }}</n-descriptions-item>
                            <n-descriptions-item label="年份">{{ season.ProductionYear }}</n-descriptions-item>
                            <n-descriptions-item label="已观看">{{ season.UserData?.Played ? '是' : '否' }} ({{ season.UserData?.PlayCount }}次)</n-descriptions-item>
                          </n-descriptions>

                          <!-- 递归层级：集 (Episode) -->
                          <n-list size="small" hoverable style="margin-top: 12px">
                            <n-list-item v-for="ep in season.Episodes" :key="ep.Id">
                              <n-thing :title="`EP ${ep.IndexNumber} - ${ep.Name}`">
                                <template #header-extra>
                                  <n-button quaternary circle size="tiny" type="primary" @click="showJson(ep)">
                                    <template #icon><n-icon color="#bb86fc"><DocumentTextIcon /></n-icon></template>
                                  </n-button>
                                </template>
                                <template #description>
                                  <n-descriptions label-placement="left" :column="2" size="tiny" style="margin-top: 4px">
                                    <n-descriptions-item label="Emby ID">{{ ep.Id }}</n-descriptions-item>
                                    <n-descriptions-item label="评分">{{ ep.CommunityRating || 'N/A' }}</n-descriptions-item>
                                    <n-descriptions-item label="首播">{{ ep.PremiereDate?.split('T')[0] || 'N/A' }}</n-descriptions-item>
                                    <n-descriptions-item label="时长">{{ Math.floor((ep.RunTimeTicks || 0) / 10000000 / 60) }} 分钟</n-descriptions-item>
                                    <n-descriptions-item label="路径" :span="2">
                                      <n-text depth="3" style="font-size: 11px">{{ ep.Path }}</n-text>
                                    </n-descriptions-item>
                                  </n-descriptions>
                                  <n-p depth="3" style="font-size: 12px; margin-top: 8px; border-left: 2px solid #333; padding-left: 8px">
                                    {{ ep.Overview || '暂无单集简介' }}
                                  </n-p>
                                </template>
                              </n-thing>
                            </n-list-item>
                          </n-list>
                        </n-collapse-item>
                      </n-collapse>
                    </div>
                  </n-card>
                </n-collapse-item>
              </n-collapse>
            </div>
            <n-empty v-else-if="searched && !loading" description="未找到匹配项目" />
            <n-empty v-else description="请输入 TMDB ID 并启动检索" />
          </n-space>
        </n-gi>

        <!-- 右侧：辅助信息区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="工具说明" size="small" segmented>
              <n-text depth="3">
                此工具会根据您提供的 TMDB ID，在您的 Emby 媒体库中进行深度搜索。
                <br/><br/>
                <b>与普通搜索的区别：</b><br/>
                1. 它是递归的：如果是剧集，会一并抓取所有季、集的信息。<br/>
                2. 它是精准的：直接匹配 ProviderIds 中的 TMDB 字段。<br/>
                3. 它包含元数据详情：方便您检查库中资料是否完整。
              </n-text>
            </n-card>

            <n-card title="检索技巧" size="small" segmented>
              <n-text depth="3">
                - 对于电影，通常只需要一个 ID。<br/>
                - 对于剧集，搜索结果会展示详细的层级结构。<br/>
                - 点击右侧的文档图标可以查看该项目的原始 JSON 元数据。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>

      <!-- JSON 弹窗 -->
      <n-modal v-model:show="jsonModal.show" preset="card" style="width: 900px" title="元数据原始 JSON 快照">
        <div class="json-code-wrapper">
          <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
        </div>
        <template #footer>
          <n-button block type="primary" secondary @click="copyRawJson">
            复制数据
          </n-button>
        </template>
      </n-modal>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { 
  useMessage, NSpace, NH2, NH3, NText, NCard, NInput, NButton, 
  NCheckboxGroup, NCheckbox, NCode, NTag, NEmpty, NCollapse, 
  NCollapseItem, NGrid, NGi, NFormItemGi, NForm, NDescriptions, 
  NDescriptionsItem, NDivider, NList, NListItem, NRate, NModal, NP, NIcon, NThing 
} from 'naive-ui'
import { DocumentTextIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const searched = ref(false)
const results = ref<any[]>([])
const searchTypes = ref(['movies', 'series'])
const form = reactive({ tmdb_id: '' })
const jsonModal = reactive({ show: false, data: {} as any })

const showJson = (item: any) => { jsonModal.data = item; jsonModal.show = true; }
const copyRawJson = () => { 
  const text = JSON.stringify(jsonModal.data, null, 2);
  if (copyToClipboard(text)) {
    message.success('数据已成功复制到剪贴板');
  } else {
    message.error('复制失败，请手动选择文字复制');
  }
}

// 兼容性极强的复制工具函数
const copyToClipboard = (text: string) => {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed"; // 避免滚动条抖动
  textArea.style.left = "-9999px";
  textArea.style.top = "0";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    document.body.removeChild(textArea);
    return false;
  }
}

const handleSearch = async () => {
  if (!form.tmdb_id) return
  loading.value = true; searched.value = true; results.value = []
  try {
    const res = await axios.post('/api/tmdb-search/search-by-id', {
      tmdb_id: form.tmdb_id,
      search_movies: searchTypes.value.includes('movies'),
      search_series: searchTypes.value.includes('series')
    })
    results.value = res.data.results
  } catch (e) { message.error('搜索异常') }
  finally { loading.value = false }
}
</script>

<style scoped>
.json-code-wrapper { 
  background: var(--card-bg-color); 
  padding: 16px; 
  border-radius: 8px; 
  max-height: 65vh; 
  overflow-y: auto; 
  border: 1px solid var(--border-color);
}

.overview-box { 
  background: rgba(255,255,255,0.03); 
  padding: 12px; 
  border-left: 4px solid var(--primary-color); 
  border-radius: 4px; 
}
</style>