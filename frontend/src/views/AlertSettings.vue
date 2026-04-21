<template>
  <div class="alert-settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警通知设置</span>
          <el-button type="primary" @click="saveSettings" :loading="saving">保存设置</el-button>
        </div>
      </template>

      <el-form :model="form" label-width="140px" v-loading="loading">
        <!-- 全局开关 -->
        <el-divider content-position="left">全局设置</el-divider>
        <el-form-item label="启用告警">
          <el-switch v-model="form.enabled" />
          <span class="form-tip">关闭后将停止所有告警通知</span>
        </el-form-item>

        <!-- 邮件告警 -->
        <el-divider content-position="left">📧 邮件告警</el-divider>
        <el-form-item label="启用邮件">
          <el-switch v-model="form.email_enabled" />
        </el-form-item>
        <el-form-item label="SMTP 服务器" v-if="form.email_enabled">
          <el-input v-model="form.email_smtp_host" placeholder="smtp.company.com" />
        </el-form-item>
        <el-form-item label="SMTP 端口" v-if="form.email_enabled">
          <el-input-number v-model="form.email_smtp_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="使用 TLS" v-if="form.email_enabled">
          <el-switch v-model="form.email_use_tls" />
        </el-form-item>
        <el-form-item label="用户名" v-if="form.email_enabled">
          <el-input v-model="form.email_username" />
        </el-form-item>
        <el-form-item label="密码" v-if="form.email_enabled">
          <el-input v-model="form.email_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="发件人" v-if="form.email_enabled">
          <el-input v-model="form.email_from_addr" placeholder="noreply@company.com" />
        </el-form-item>
        <el-form-item label="收件人" v-if="form.email_enabled">
          <el-select v-model="form.email_recipients" multiple filterable allow-create placeholder="输入邮箱地址" style="width: 100%">
            <el-option v-for="addr in form.email_recipients" :key="addr" :label="addr" :value="addr" />
          </el-select>
        </el-form-item>

        <!-- 企业微信 -->
        <el-divider content-position="left">💬 企业微信 Webhook</el-divider>
        <el-form-item label="启用企业微信">
          <el-switch v-model="form.wechat_enabled" />
        </el-form-item>
        <el-form-item label="Webhook URL" v-if="form.wechat_enabled">
          <el-input v-model="form.wechat_webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
          <span class="form-tip">在群聊中添加机器人后获取 Webhook 地址</span>
        </el-form-item>

        <!-- 钉钉 -->
        <el-divider content-position="left">🔔 钉钉 Webhook</el-divider>
        <el-form-item label="启用钉钉">
          <el-switch v-model="form.dingtalk_enabled" />
        </el-form-item>
        <el-form-item label="Webhook URL" v-if="form.dingtalk_enabled">
          <el-input v-model="form.dingtalk_webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
        </el-form-item>
        <el-form-item label="加签密钥" v-if="form.dingtalk_enabled">
          <el-input v-model="form.dingtalk_secret" placeholder="SECxxxxxxxx" show-password />
          <span class="form-tip">可选，推荐启用加签验证</span>
        </el-form-item>

        <!-- 测试按钮 -->
        <el-divider />
        <el-form-item label="测试渠道">
          <el-button @click="testChannel('email')" :disabled="!form.email_enabled">测试邮件</el-button>
          <el-button @click="testChannel('wechat_work')" :disabled="!form.wechat_enabled">测试企业微信</el-button>
          <el-button @click="testChannel('dingtalk')" :disabled="!form.dingtalk_enabled">测试钉钉</el-button>
          <el-button type="warning" @click="testChannel('all')" :disabled="!form.enabled">测试全部</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getAlertSettings, saveAlertSettings, testAlertChannel } from '@/api'

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

const loadSettings = async () => {
  loading.value = true
  try {
    const res = await getAlertSettings()
    Object.assign(form, res)
  } catch (e) {
    ElMessage.error('加载设置失败')
  } finally {
    loading.value = false
  }
}

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
    ElMessage.success('设置已保存')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

const testChannel = async (channel) => {
  try {
    const res = await testAlertChannel(channel)
    const results = res.results || {}
    const msgs = Object.entries(results).map(([k, v]) => `${k}: ${v === true ? '✅ 成功' : v === false ? '❌ 失败' : v}`)
    ElMessage.success(msgs.join(' | ') || '测试完成')
  } catch (e) {
    ElMessage.error('测试失败')
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.alert-settings-page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.form-tip { color: #909399; font-size: 12px; margin-left: 8px; }
</style>
