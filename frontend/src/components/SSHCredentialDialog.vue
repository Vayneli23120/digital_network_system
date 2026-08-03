<template>
  <el-dialog v-model="visible" :title="t('sshCredTitle')" width="520px" append-to-body draggable align-center class="credential-dialog">
    <el-form :model="form" label-width="100px" size="default" class="credential-form">
      <div class="form-section">
        <div class="section-header">
          <el-icon><Lock /></el-icon>
          <span>{{ t('sshCredSection') }}</span>
        </div>
        <el-form-item :label="t('sshCredUsername')" required>
          <el-input v-model="form.username" :placeholder="t('sshCredUsernamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('sshCredPassword')" required>
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="t('sshCredPasswordPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('sshCredSecret')">
          <el-input
            v-model="form.secret"
            type="password"
            show-password
            :placeholder="t('sshCredSecretPlaceholder')"
          />
        </el-form-item>
        <el-form-item>
          <el-alert type="warning" :closable="false" class="info-alert">
            <template #title>
              <p>{{ t('sshCredSessionInfo') }}</p>
              <p>{{ t('sshCredNoServerStore') }}</p>
            </template>
          </el-alert>
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="cancel" class="footer-btn secondary">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="confirm" class="footer-btn primary">{{ t('actionConfirm') }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const visible = ref(false)
const form = ref({ username: '', password: '', secret: '' })
let resolver = null

function open() {
  visible.value = true
  return new Promise((resolve) => {
    resolver = resolve
  })
}

function confirm() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning(t('sshCredRequiredHint'))
    return
  }
  visible.value = false
  const creds = { ...form.value }
  if (resolver) resolver(creds)
  resolver = null
  form.value = { username: '', password: '', secret: '' }
}

function cancel() {
  visible.value = false
  if (resolver) resolver(null)
  resolver = null
}

defineExpose({ open })
</script>
