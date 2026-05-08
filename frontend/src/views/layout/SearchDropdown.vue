<template>
  <div class="search-wrap" :class="{ active: showSearchResults }">
    <el-icon class="search-icon"><Search /></el-icon>
    <input
      ref="searchInputRef"
      class="search-input"
      :placeholder="placeholder"
      v-model="searchQuery"
      @input="handleSearch"
      @focus="showSearchResults = true"
      @keydown.escape="closeSearch"
      @keydown.enter="handleEnterKey"
    />
    <kbd class="search-kbd" @click="focusSearch">CmdK</kbd>

    <!-- Search Results Dropdown -->
    <div class="search-results" v-if="showSearchResults && hasResults">
      <div class="sr-section" v-if="searchResults.devices.length > 0">
        <div class="sr-section-label">{{ devicesLabel }}</div>
        <div
          class="sr-item"
          v-for="(device, idx) in searchResults.devices"
          :key="device.id"
          :class="{ selected: selectedIndex === idx }"
          @click="goToDevice(device.id)"
        >
          <el-icon class="sr-icon"><Connection /></el-icon>
          <div class="sr-content">
            <span class="sr-title">{{ device.name }}</span>
            <span class="sr-meta">{{ device.ip }} - {{ device.status }}</span>
          </div>
        </div>
      </div>

      <div class="sr-section" v-if="searchResults.templates.length > 0">
        <div class="sr-section-label">{{ templatesLabel }}</div>
        <div
          class="sr-item"
          v-for="(template, idx) in searchResults.templates"
          :key="template.id"
          :class="{ selected: selectedIndex === searchResults.devices.length + idx }"
          @click="goToTemplate(template.id)"
        >
          <el-icon class="sr-icon"><Document /></el-icon>
          <div class="sr-content">
            <span class="sr-title">{{ template.name }}</span>
            <span class="sr-meta">{{ template.description || noRecordsLabel }}</span>
          </div>
        </div>
      </div>

      <div class="sr-section" v-if="searchResults.backups.length > 0">
        <div class="sr-section-label">{{ backupsLabel }}</div>
        <div
          class="sr-item"
          v-for="(backup, idx) in searchResults.backups.slice(0, 5)"
          :key="backup.id"
          :class="{ selected: selectedIndex === searchResults.devices.length + searchResults.templates.length + idx }"
          @click="goToBackups(backup.device_name)"
        >
          <el-icon class="sr-icon"><Download /></el-icon>
          <div class="sr-content">
            <span class="sr-title">{{ backup.device_name }}</span>
            <span class="sr-meta">{{ formatDate(backup.backup_time) }} - {{ backup.has_change ? modifiedLabel : cleanLabel }}</span>
          </div>
        </div>
      </div>

      <div class="sr-empty" v-if="searchQuery && !hasResults && !searchLoading">
        {{ noResultsLabel }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Connection, Document, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const props = defineProps({
  placeholder: {
    type: String,
    default: 'Search...'
  },
  devicesLabel: {
    type: String,
    default: 'Devices'
  },
  templatesLabel: {
    type: String,
    default: 'Templates'
  },
  backupsLabel: {
    type: String,
    default: 'Backups'
  },
  noResultsLabel: {
    type: String,
    default: 'No results found'
  },
  noRecordsLabel: {
    type: String,
    default: 'No records'
  },
  modifiedLabel: {
    type: String,
    default: 'Modified'
  },
  cleanLabel: {
    type: String,
    default: 'Clean'
  }
})

const emit = defineEmits(['close'])

const router = useRouter()

const searchInputRef = ref(null)
const searchQuery = ref('')
const showSearchResults = ref(false)
const searchLoading = ref(false)
const selectedIndex = ref(0)
const searchResults = ref({
  devices: [],
  templates: [],
  backups: [],
})

const hasResults = computed(() => {
  return searchResults.value.devices.length > 0 ||
         searchResults.value.templates.length > 0 ||
         searchResults.value.backups.length > 0
})

const totalResults = computed(() => {
  return searchResults.value.devices.length +
         searchResults.value.templates.length +
         searchResults.value.backups.length
})

const formatDate = (dateStr) => dayjs(dateStr).format('MM-DD HH:mm')

const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = { devices: [], templates: [], backups: [] }
    return
  }

  searchLoading.value = true
  selectedIndex.value = 0

  try {
    const query = searchQuery.value.trim()

    // Search devices
    const devicesRes = await fetch(`/api/devices?search=${encodeURIComponent(query)}&limit=5`)
    const devicesData = await devicesRes.json()
    searchResults.value.devices = devicesData.items || []

    // Search templates
    const templatesRes = await fetch(`/api/templates`)
    const templatesData = await templatesRes.json()
    const allTemplates = templatesData.items || templatesData || []
    searchResults.value.templates = allTemplates
      .filter(t => t.name?.toLowerCase().includes(query.toLowerCase()) ||
                   t.description?.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 5)

    // Search backups
    const backupsRes = await fetch(`/api/backups?limit=20`)
    const backupsData = await backupsRes.json()
    const allBackups = backupsData.items || backupsData.backups || []
    searchResults.value.backups = allBackups
      .filter(b => b.device_name?.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 5)

  } catch (err) {
    console.error('Search failed:', err)
  }

  searchLoading.value = false
}

const focusSearch = () => {
  searchInputRef.value?.focus()
  showSearchResults.value = true
}

const closeSearch = () => {
  showSearchResults.value = false
  searchQuery.value = ''
  searchResults.value = { devices: [], templates: [], backups: [] }
  emit('close')
}

const handleEnterKey = () => {
  if (totalResults.value === 0) return

  const allItems = [
    ...searchResults.value.devices.map(d => ({ type: 'device', id: d.id })),
    ...searchResults.value.templates.map(t => ({ type: 'template', id: t.id })),
    ...searchResults.value.backups.map(b => ({ type: 'backup', device_name: b.device_name })),
  ]

  if (selectedIndex.value < allItems.length) {
    const item = allItems[selectedIndex.value]
    if (item.type === 'device') {
      goToDevice(item.id)
    } else if (item.type === 'template') {
      goToTemplate(item.id)
    } else if (item.type === 'backup') {
      goToBackups(item.device_name)
    }
  }
}

const goToDevice = (id) => {
  closeSearch()
  router.push(`/devices/${id}`)
}

const goToTemplate = (id) => {
  closeSearch()
  router.push(`/templates`)
  ElMessage.info(`Template ID: ${id}`)
}

const goToBackups = (deviceName) => {
  closeSearch()
  router.push(`/backups`)
}

// Keyboard navigation for search
const handleKeyDown = (e) => {
  // Cmd/Ctrl + K to open search
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    focusSearch()
  }

  // Arrow keys for navigation when search is open
  if (showSearchResults.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, totalResults.value - 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
    }
  }
}

// Expose methods for parent component
defineExpose({
  focusSearch,
  closeSearch
})

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* Search */
.search-wrap {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all 0.2s;
  width: 240px;
  position: relative;
}

/* Light mode search box */
.search-wrap {
  background: rgba(255, 255, 255, 0.12);
}

.search-wrap:focus-within,
.search-wrap.active {
  border-color: #f6b93b;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 0 3px rgba(255, 204, 0, 0.2);
}

.search-icon {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 13px;
  outline: none;
  color: #fff;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.search-kbd {
  padding: 2px 6px;
  font-family: var(--font-display);
  font-size: 10px;
  border-radius: 4px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
}

/* Dark mode styles applied via parent */
.dark .search-wrap {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .search-wrap:focus-within,
.dark .search-wrap.active {
  border-color: #00b894;
  box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.15);
}

.dark .search-icon {
  color: var(--text-tertiary);
}

.dark .search-input {
  color: var(--text-primary);
}

.dark .search-input::placeholder {
  color: var(--text-muted);
}

.dark .search-kbd {
  color: var(--text-muted);
  background: var(--bg-hover);
}

/* Search Results Dropdown */
.search-results {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 400px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
}

.sr-section {
  padding: 8px 0;
}

.sr-section:not(:last-child) {
  border-bottom: 1px solid var(--border-subtle);
}

.sr-section-label {
  padding: 6px 16px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.sr-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.sr-item:hover,
.sr-item.selected {
  background: var(--bg-hover);
}

.sr-icon {
  font-size: 16px;
  color: var(--accent-secondary);
}

.sr-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sr-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.sr-meta {
  font-size: 12px;
  font-family: var(--font-display);
  color: var(--text-tertiary);
}

.sr-empty {
  padding: 20px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .search-wrap {
    width: 140px;
  }

  .search-kbd {
    display: none;
  }
}
</style>