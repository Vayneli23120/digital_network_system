<template>
  <div class="system-settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('systemSettings') || '系统设置' }}</span>
          <el-button type="primary" @click="saveSettings" :loading="saving">{{ t('alertSaveSettings') || '保存' }}</el-button>
        </div>
      </template>

      <el-form :model="form" label-width="140px" v-loading="loading">
        <!-- 时区设置 -->
        <div class="form-section">
          <div class="section-header">{{ t('systemTimeSettings') || '时间设置' }}</div>

          <el-form-item :label="t('systemTimezone') || '系统时区'">
            <el-select v-model="form.timezone" placeholder="选择时区" style="width: 300px">
              <el-option
                v-for="tz in timezoneOptions"
                :key="tz.value"
                :label="tz.label"
                :value="tz.value"
              />
            </el-select>
            <span class="form-tip">{{ t('systemTimezoneTip') || '系统全局时区，影响所有时间显示' }}</span>
          </el-form-item>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  timezone: 'Asia/Shanghai',
})

const timezoneOptions = [
  { value: 'UTC', label: 'UTC (UTC+0)' },
  { value: 'Asia/Shanghai', label: '中国标准时间 (UTC+8)' },
  { value: 'Asia/Taipei', label: '台北时间 (UTC+8)' },
  { value: 'Asia/Hong_Kong', label: '香港时间 (UTC+8)' },
  { value: 'Asia/Tokyo', label: '日本标准时间 (UTC+9)' },
  { value: 'Asia/Seoul', label: '韩国标准时间 (UTC+9)' },
  { value: 'Asia/Singapore', label: '新加坡时间 (UTC+8)' },
  { value: 'America/New_York', label: '美国东部时间 (UTC-5)' },
  { value: 'America/Chicago', label: '美国中部时间 (UTC-6)' },
  { value: 'America/Denver', label: '美国山地时间 (UTC-7)' },
  { value: 'America/Los_Angeles', label: '美国太平洋时间 (UTC-8)' },
  { value: 'Europe/London', label: '格林威治标准时间 (UTC+0)' },
  { value: 'Europe/Berlin', label: '欧洲中部时间 (UTC+1)' },
  { value: 'Europe/Paris', label: '法国时间 (UTC+1)' },
  { value: 'Australia/Sydney', label: '澳大利亚东部时间 (UTC+10)' },
  { value: 'Pacific/Auckland', label: '新西兰时间 (UTC+12)' },
]

async function loadSettings() {
  loading.value = true
  try {
    const res = await axios.get('/api/system/config')
    const items = res.data.items || []
    for (const item of items) {
      if (item.key in form) {
        form[item.key] = item.value
      }
    }
  } catch (e) {
    ElMessage.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await axios.put('/api/system/config', {
      key: 'timezone',
      value: form.timezone,
    })
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.system-settings-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #999;
}

.form-section {
  margin-bottom: 24px;
}

.section-header {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}
</style>
