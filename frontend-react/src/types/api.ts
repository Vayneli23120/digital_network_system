// ===== Job 相关类型 =====

export interface Job {
  id: string
  job_type: JobType
  status: JobStatus
  device_id?: number
  device_ids?: number[]
  celery_task_id?: string
  progress_percent: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
  result?: Record<string, unknown>
  operator?: string
}

export type JobType =
  | 'backup'
  | 'deploy'
  | 'compliance_scan'
  | 'discovery'
  | 'health_check'
  | 'command_exec'
  | 'config_collect'

export type JobStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'success'
  | 'failed'
  | 'cancelled'
  | 'timeout'
  | 'partial'

// ===== Device 相关类型 =====

export interface Device {
  id: number
  name: string
  ip: string
  vendor?: string
  model?: string
  serial_number?: string
  location?: string
  role?: string
  deployment_status: string
  reachability: string
  last_backup_time?: string
  created_at?: string
}

// ===== AI 相关类型 =====

export interface AIAnalysisResult {
  id: string
  analysis_type: string
  target_type?: string
  target_id?: number
  success: boolean
  response?: string
  parsed_result?: Record<string, unknown>
  confidence_score?: number
  created_at: string
}

// ===== API 响应类型 =====

export interface PaginatedResponse<T> {
  total: number
  skip: number
  limit: number
  items: T[]
}

export interface ApiResponse<T> {
  success: boolean
  message?: string
  data?: T
  error?: string
}