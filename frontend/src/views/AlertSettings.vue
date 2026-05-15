<template>
  <div class="alert-settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('alertTitle') }}</span>
          <el-button type="primary" @click="saveSettings" :loading="saving">{{ t('alertSaveSettings') }}</el-button>
        </div>
      </template>

      <el-form :model="form" label-width="140px" v-loading="loading">
        <!-- 全局开关 -->
        <el-divider content-position="left">{{ t('alertGlobalSettings') }}</el-divider>
        <el-form-item :label="t('alertEnableAlerts')">
          <el-switch v-model="form.enabled" />
          <span class="form-tip">{{ t('alertDisableTip') }}</span>
        </el-form-item>

        <!-- 邮件告警 -->
        <el-divider content-position="left">📧 {{ t('alertEmailSection') }}</el-divider>
        <el-form-item :label="t('alertEnableEmail')">
          <el-switch v-model="form.email_enabled" />
        </el-form-item>
        <el-form-item :label="t('alertSmtpServer')" v-if="form.email_enabled">
          <el-input v-model="form.email_smtp_host" placeholder="smtp.company.com" />
        </el-form-item>
        <el-form-item :label="t('alertSmtpPort')" v-if="form.email_enabled">
          <el-input-number v-model="form.email_smtp_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item :label="t('alertUseTls')" v-if="form.email_enabled">
          <el-switch v-model="form.email_use_tls" />
        </el-form-item>
        <el-form-item :label="t('alertUsername')" v-if="form.email_enabled">
          <el-input v-model="form.email_username" />
        </el-form-item>
        <el-form-item :label="t('alertPassword')" v-if="form.email_enabled">
          <el-input v-model="form.email_password" type="password" show-password />
        </el-form-item>
        <el-form-item :label="t('alertSender')" v-if="form.email_enabled">
          <el-input v-model="form.email_from_addr" placeholder="noreply@company.com" />
        </el-form-item>
        <el-form-item :label="t('alertRecipients')" v-if="form.email_enabled">
          <el-select v-model="form.email_recipients" multiple filterable allow-create placeholder="Enter email address" style="width: 100%">
            <el-option v-for="addr in form.email_recipients" :key="addr" :label="addr" :value="addr" />
          </el-select>
        </el-form-item>

        <!-- 企业微信 -->
        <el-divider content-position="left">💬 {{ t('alertWechatSection') }}</el-divider>
        <el-form-item :label="t('alertEnableWechat')">
          <el-switch v-model="form.wechat_enabled" />
        </el-form-item>
        <el-form-item :label="t('alertWechatUrl')" v-if="form.wechat_enabled">
          <el-input v-model="form.wechat_webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          <span class="form-tip">{{ t('alertWechatTip') }}</span>
        </el-form-item>

        <!-- 钉钉 -->
        <el-divider content-position="left">🔔 {{ t('alertDingtalkSection') }}</el-divider>
        <el-form-item :label="t('alertEnableDingtalk')">
          <el-switch v-model="form.dingtalk_enabled" />
        </el-form-item>
        <el-form-item :label="t('alertDingtalkUrl')" v-if="form.dingtalk_enabled">
          <el-input v-model="form.dingtalk_webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
        </el-form-item>
        <el-form-item :label="t('alertDingtalkSecret')" v-if="form.dingtalk_enabled">
          <el-input v-model="form.dingtalk_secret" placeholder="SECxxxxxxxx" show-password />
          <span class="form-tip">{{ t('alertDingtalkSecretTip') }}</span>
        </el-form-item>

        <!-- 测试按钮 -->
        <el-divider />
        <el-form-item :label="t('alertTestChannel')">
          <el-button @click="testChannel('email')" :disabled="!form.email_enabled">{{ t('alertTestEmail') }}</el-button>
          <el-button @click="testChannel('wechat_work')" :disabled="!form.wechat_enabled">{{ t('alertTestWechat') }}</el-button>
          <el-button @click="testChannel('dingtalk')" :disabled="!form.dingtalk_enabled">{{ t('alertTestDingtalk') }}</el-button>
          <el-button type="warning" @click="testChannel('all')" :disabled="!form.enabled">{{ t('alertTestAll') }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlertSettings, saveAlertSettings, testAlertChannel } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  enabled: false,
  channels: [],
  email_enabled: false,
  email_smtp_host: 'smtp.company.com',
  email_smtp_port: 587,
  email_use_tls: true,
  email_username: '',
  email_password: '',
  email_from_addr: '',
  email_recipients: [],
  wechat_enabled: false,
  wechat_webhook_url: '',
  dingtalk_enabled: false,
  dingtalk_webhook_url: '',
  dingtalk_secret: '',
})

watch([() => form.email_enabled, () => form.wechat_enabled, () => form.dingtalk_enabled], () => {
  form.channels = []
  if (form.email_enabled) form.channels.push('email')
  if (form.wechat_enabled) form.channels.push('wechat_work')
  if (form.dingtalk_enabled) form.channels.push('dingtalk')
})

const loadSettings = debounce(async (force = false) => {
  loading.value = true
  try {
    const res = await cachedRequest(
      () => getAlertSettings(),
      'alert_settings',
      {},
      { forceRefresh: force }
    )
    Object.assign(form, res)
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('msgLoadSettingsFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const saveSettings = async () => {
  saving.value = true
  try {
    await saveAlertSettings({
      enabled: form.enabled,
      channels: form.channels,
      email_enabled: form.email_enabled,
      email_smtp_host: form.email_smtp_host,
      email_smtp_port: form.email_smtp_port,
      email_use_tls: form.email_use_tls,
      email_username: form.email_username,
      email_password: form.email_password,
      email_from_addr: form.email_from_addr,
      email_recipients: form.email_recipients,
      wechat_enabled: form.wechat_enabled,
      wechat_webhook_url: form.wechat_webhook_url,
      dingtalk_enabled: form.dingtalk_enabled,
      dingtalk_webhook_url: form.dingtalk_webhook_url,
      dingtalk_secret: form.dingtalk_secret,
    })
    clearCache('alert_settings')
    ElMessage.success(t('msgSaveSuccess'))
  } catch (e) {
    ElMessage.error(t('msgSaveFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const testChannel = async (channel) => {
  try {
    const res = await testAlertChannel(channel)
    const results = res.results || {}
    const msgs = Object.entries(results).map(([k, v]) => `${k}: ${v === true ? '✅ ' + t('msgSuccess') : v === false ? '❌ ' + t('msgFailed') : v}`)
    ElMessage.success(msgs.join(' | ') || t('msgTestComplete'))
  } catch (e) {
    ElMessage.error(t('msgTestFailed'))
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.alert-settings-page { padding: 0; }
.form-tip { color: var(--text-muted); font-size: 12px; margin-left: var(--gap-sm); }
</style>