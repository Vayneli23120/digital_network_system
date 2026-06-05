import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'
import type { Job, PaginatedResponse, JobType, JobStatus } from '@/types/api'

// ===== Jobs API =====

export const jobKeys = {
  all: ['jobs'] as const,
  list: (filters?: JobFilters) => ['jobs', 'list', filters] as const,
  detail: (id: string) => ['jobs', 'detail', id] as const,
  stats: (days: number) => ['jobs', 'stats', days] as const,
}

interface JobFilters {
  job_type?: JobType
  status?: JobStatus
  device_id?: number
  operator?: string
}

// 获取作业列表
export function useJobs(filters?: JobFilters & { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: jobKeys.list(filters),
    queryFn: async (): PaginatedResponse<Job> => {
      const params = new URLSearchParams()
      if (filters?.job_type) params.set('job_type', filters.job_type)
      if (filters?.status) params.set('status', filters.status)
      if (filters?.device_id) params.set('device_id', filters.device_id.toString())
      if (filters?.operator) params.set('operator', filters.operator)
      if (filters?.skip) params.set('skip', filters.skip.toString())
      if (filters?.limit) params.set('limit', filters.limit.toString())

      const response = await apiClient.get(`/jobs?${params.toString()}`)
      return response as PaginatedResponse<Job>
    },
  })
}

// 获取单个作业
export function useJob(jobId: string) {
  return useQuery({
    queryKey: jobKeys.detail(jobId),
    queryFn: async (): Job => {
      const response = await apiClient.get(`/jobs/${jobId}`)
      return response as Job
    },
    enabled: !!jobId,
  })
}

// 取消作业
export function useCancelJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: string) => {
      const response = await apiClient.post(`/jobs/${jobId}/cancel`)
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all })
    },
  })
}

// ===== Devices API =====

export const deviceKeys = {
  all: ['devices'] as const,
  list: (filters?: Record<string, unknown>) => ['devices', 'list', filters] as const,
  detail: (id: number) => ['devices', 'detail', id] as const,
}

// ===== Backup API =====

// 异步备份设备
export function useBackupDeviceAsync() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ deviceId, operator }: { deviceId: number; operator?: string }) => {
      const response = await apiClient.post(`/backups/backup/${deviceId}/async?operator=${operator || 'system'}`)
      return response as { success: boolean; job_id: string; status: string }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all })
    },
  })
}