/**
 * API客户端工具
 * 统一管理所有API请求
 */

// API基础路径配置
// 生产环境使用相对路径（同源），开发环境可通过环境变量配置
// 使用空字符串表示相对路径，浏览器会自动使用当前域名
const API_BASE = ''

/**
 * 通用API请求函数
 */
async function apiRequest<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  
  return response.json()
}

/**
 * 任务状态响应类型
 */
export interface JobStatus {
  job_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  progress: number
  stage: string
  analysis?: Record<string, string>
  images: string[]
  error?: string
  details?: Record<string, any>
  queue_position: number
  estimated_wait: number
  created_at: number
  started_at?: number
  finished_at?: number
}

export interface StartGenerateResponse {
  success: boolean
  job_id?: string
  error?: string
  queue_position?: number
  estimated_wait?: number
  queue_stats?: {
    running_count: number
    waiting_count: number
    max_concurrent: number
    avg_duration: number
  }
}

export interface QueueStats {
  running_count: number
  waiting_count: number
  max_concurrent: number
  avg_duration: number
}

/**
 * API客户端对象
 * 包含所有API方法
 */
export const api = {
  /**
   * 启动生成任务（异步，支持排队）
   */
  startGenerate: (requirement: string): Promise<StartGenerateResponse> =>
    apiRequest('/api/start_generate', {
      method: 'POST',
      body: JSON.stringify({ requirement }),
    }),
  
  /**
   * 查询任务状态（包含队列位置和预估时间）
   */
  getJobStatus: (jobId: string): Promise<{ success: boolean; job?: JobStatus; error?: string }> =>
    apiRequest(`/api/job/${jobId}/status`),
  
  /**
   * 取消排队中的任务
   */
  cancelJob: (jobId: string) =>
    apiRequest(`/api/job/${jobId}/cancel`, {
      method: 'POST',
    }),
  
  /**
   * 获取队列统计信息
   */
  getQueueStats: (): Promise<{ success: boolean; stats: QueueStats }> =>
    apiRequest('/api/queue/stats'),
  
  /**
   * 同步生成图片
   */
  generate: (requirement: string) =>
    apiRequest('/api/generate', {
      method: 'POST',
      body: JSON.stringify({ requirement }),
    }),
  
  /**
   * 分析内容
   */
  analyze: (requirement: string) =>
    apiRequest('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ requirement }),
    }),
  
  /**
   * 健康检查
   */
  health: () =>
    apiRequest('/api/health'),
  
  /**
   * 执行banana-background脚本
   */
  runBanana: (tagImgUrl: string, backgroundText: string) =>
    apiRequest('/api/run-banana', {
      method: 'POST',
      body: JSON.stringify({ tagImgUrl, backgroundText }),
    }),
  
  /**
   * 执行jimeng4脚本
   */
  runJimeng4: (tagImgUrl: string, backgroundText: string) =>
    apiRequest('/api/run-jimeng4', {
      method: 'POST',
      body: JSON.stringify({ tagImgUrl, backgroundText }),
    }),
  
  /**
   * 执行3D banana脚本
   */
  run3dBanana: (imagePath: string, promptText: string) =>
    apiRequest('/api/run-3d-banana', {
      method: 'POST',
      body: JSON.stringify({ imagePath, promptText }),
    }),
  
  /**
   * 执行banana pro img jd脚本
   */
  runBananaProImgJd: (imageUrl: string, prompt: string) =>
    apiRequest('/api/run-banana-pro-img-jd', {
      method: 'POST',
      body: JSON.stringify({ imageUrl, prompt }),
    }),
  
  /**
   * 执行turn脚本（角度变换）
   */
  runTurn: (imageUrl: string, action: string) =>
    apiRequest('/api/run-turn', {
      method: 'POST',
      body: JSON.stringify({ imageUrl, action }),
    }),
  
  /**
   * 上传图片到图床
   */
  uploadImage: (image: string, customName?: string) =>
    apiRequest('/api/upload-image', {
      method: 'POST',
      body: JSON.stringify({ image, customName: customName || 'tag_img' }),
    }),
  
  /**
   * 保存渲染图片
   */
  saveRender: (dataURL: string) =>
    apiRequest('/api/save-render', {
      method: 'POST',
      body: JSON.stringify({ dataURL }),
    }),
}

/**
 * 格式化等待时间
 */
export function formatWaitTime(seconds: number): string {
  if (seconds <= 0) return '即将开始'
  if (seconds < 60) return `约 ${Math.ceil(seconds)} 秒`
  const minutes = Math.ceil(seconds / 60)
  return `约 ${minutes} 分钟`
}

/**
 * 导出默认API客户端
 */
export default api
