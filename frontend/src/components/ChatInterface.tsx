"use client"

import React, { useRef, useEffect, useLayoutEffect } from 'react'
import axios from 'axios'
import { useRouter } from 'next/navigation'
import { getRouteKey, readScrollPos, saveScrollPos, restoreElementScroll } from '@/lib/scrollMemory'
import { useChatState, Message } from '@/app/providers'
import { formatWaitTime } from '@/lib/api'
import ChatHeader from './ChatHeader'
import MessageArea from './MessageArea'
import ChatInput from './ChatInput'
import AnalysisPreview, { AnalysisResult } from './AnalysisPreview'
import NoticeModal from './NoticeModal'
import ThreeEditorModal from './ThreeEditorModal'
import TwoDEditorModal from './TwoDEditorModal'


// 队列状态类型
interface QueueInfo {
  position: number
  estimatedWait: number
  runningCount: number
  waitingCount: number
}

// 聊天状态类型
type ChatStatus = 'idle' | 'analyzing' | 'preview' | 'generating'

export default function ChatInterface() {
  const router = useRouter()
  const { messages, setMessages, input, setInput, selectedPresets, setSelectedPresets, persistState } = useChatState()
  const [isLoading, setIsLoading] = React.useState(false)
  const [complianceError, setComplianceError] = React.useState(false)
  const [hoveredImage, setHoveredImage] = React.useState<string | null>(null)
  const [threeModalOpen, setThreeModalOpen] = React.useState(false)
  const [renderPreviewUrl, setRenderPreviewUrl] = React.useState<string | null>(null)
  const [renderFilePath, setRenderFilePath] = React.useState<string | null>(null)
  const [threePrompt, setThreePrompt] = React.useState('')
  const [twoDEditorOpen, setTwoDEditorOpen] = React.useState(false)
  const [twoDBaseImageUrl, setTwoDBaseImageUrl] = React.useState<string | null>(null)
  // 队列状态
  const [queueInfo, setQueueInfo] = React.useState<QueueInfo | null>(null)
  const [currentJobId, setCurrentJobId] = React.useState<string | null>(null)
  // 分析预览状态
  const [chatStatus, setChatStatus] = React.useState<ChatStatus>('idle')
  const [analysisResult, setAnalysisResult] = React.useState<AnalysisResult | null>(null)
  // 2D/3D模式切换状态
  const [generationMode, setGenerationMode] = React.useState<'2D' | '3D'>('3D')
  const [perspective, setPerspective] = React.useState<string>('正视角')
  const [pendingPrompt, setPendingPrompt] = React.useState<string>('')
  const [runningLog, setRunningLog] = React.useState<string>('')
  const [runningLogActive, setRunningLogActive] = React.useState(false)

  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const pollTimerRef = useRef<number | null>(null)
  const scrollAnimationFrameRef = useRef<number | null>(null)
  const autoScrollRef = useRef<boolean>(true) // 控制是否自动滚动
  const lastLogRef = useRef<string>('')
  const runningLogsRef = useRef<string[]>([])
  const runningLogHideTimerRef = useRef<number | null>(null)

  const cancelRunningLogHide = () => {
    if (runningLogHideTimerRef.current !== null) {
      window.clearTimeout(runningLogHideTimerRef.current)
      runningLogHideTimerRef.current = null
    }
  }

  const scheduleRunningLogHide = (delayMs = 1000) => {
    cancelRunningLogHide()
    runningLogHideTimerRef.current = window.setTimeout(() => {
      setRunningLogActive(false)
      clearRunningLog()
      runningLogHideTimerRef.current = null
    }, delayMs)
  }

  const clearRunningLog = () => {
    lastLogRef.current = ''
    runningLogsRef.current = []
    setRunningLog('')
  }

  const updateRunningLog = (nextLog: unknown) => {
    if (typeof nextLog !== 'string') return
    const trimmed = nextLog.trim()
    if (!trimmed) return
    if (trimmed === lastLogRef.current) return  // 跳过重复的日志
    
    lastLogRef.current = trimmed
    
    const nextLogs = [...runningLogsRef.current, trimmed]
    runningLogsRef.current = nextLogs.slice(-8)
    setRunningLog(runningLogsRef.current.join('\n'))
  }

  const handleThreeModalOpenChange = (nextOpen: boolean) => {
    setThreeModalOpen(nextOpen)
    if (!nextOpen) {
      persistState(messages, input, selectedPresets)
    }
  }

  // 自动滚动到底部的函数
  const scrollToBottom = (smooth = true) => {
    const container = scrollContainerRef.current
    if (!container) return

    if (scrollAnimationFrameRef.current !== null) {
      cancelAnimationFrame(scrollAnimationFrameRef.current)
    }

    scrollAnimationFrameRef.current = requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      })
    })
  }

  // 检查是否应该自动滚动（用户是否在底部附近）
  const shouldAutoScroll = () => {
    const container = scrollContainerRef.current
    if (!container) return false

    const { scrollTop, scrollHeight, clientHeight } = container
    // 允许 200 像素的误差
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 200
    return isNearBottom
  }

  const isInitial = messages.length === 0
  const lastAssistantWithImages = [...messages].reverse().find(m => m.type === 'assistant' && Array.isArray(m.images) && m.images.length > 0)
  const lastAssistantImagesOnly = lastAssistantWithImages?.images && Array.isArray(lastAssistantWithImages.images)
    ? { images: lastAssistantWithImages.images }
    : null
  const lastUserPrompt = [...messages].reverse().find(m => m.type === 'user')?.content || ''

  // 是否显示分析预览（只在 preview 状态显示）
  const showAnalysisPreview = chatStatus === 'preview' && analysisResult !== null

  const runningLogText =
    runningLog ||
    (queueInfo && queueInfo.position > 0
      ? `排队中，预计等待 ${formatWaitTime(queueInfo.estimatedWait)}`
      : chatStatus === 'analyzing'
        ? '正在分析，请稍候...'
        : chatStatus === 'preview'
          ? '请确认分析结果后开始生成'
          : isLoading || chatStatus === 'generating'
            ? '后台处理中，请稍候...'
            : '')
  const showRunningLogBar = (runningLogActive || isLoading || chatStatus !== 'idle') && !!runningLogText

  // 监听消息变化，自动滚动到底部
  useEffect(() => {
    if (messages.length > 0) {
      // 立即滚动一次
      scrollToBottom(true)

      // 100ms 后再滚动一次，确保 DOM 渲染完成
      const timer = setTimeout(() => {
        if (autoScrollRef.current || shouldAutoScroll()) {
          scrollToBottom(true)
        }
      }, 100)

      // 500ms 后再滚动一次，应对可能的图片加载导致的布局变化
      const timer2 = setTimeout(() => {
        if (autoScrollRef.current || shouldAutoScroll()) {
          scrollToBottom(true)
        }
      }, 500)

      return () => {
        clearTimeout(timer)
        clearTimeout(timer2)
      }
    }
  }, [messages])

  // 监听加载状态和分析状态变化
  useEffect(() => {
    if (isLoading || chatStatus !== 'idle') {
      const timer = setInterval(() => {
        if (autoScrollRef.current || shouldAutoScroll()) {
          scrollToBottom(true)
        }
      }, 500)
      return () => clearInterval(timer)
    }
  }, [isLoading, chatStatus])

  useLayoutEffect(() => {
    const el = scrollContainerRef.current
    if (!el || typeof window === 'undefined') return
    const key = getRouteKey()
    const st = readScrollPos(key)
    if (typeof st === 'number' && st >= 0) {
      restoreElementScroll(el, st, { smooth: true, retries: 2 })
    }

    // 添加滚动监听，控制自动滚动行为
    const handleScroll = () => {
      if (!el) return
      const { scrollTop, scrollHeight, clientHeight } = el
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 150
      autoScrollRef.current = isNearBottom
    }

    el.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      el.removeEventListener('scroll', handleScroll)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (scrollAnimationFrameRef.current !== null) {
        cancelAnimationFrame(scrollAnimationFrameRef.current)
      }
    }
  }, [])

  const SCENE_MAP: Record<string, string> = {
    '圣诞风': '穿着圣诞服，戴着圣诞帽，拿着仙女棒',
    '新年风': '穿着财神服，戴着财神帽，拿着金元宝',
    '运动风': '穿着篮球服，拿着篮球',
    '魔法风': '穿着魔法长袍，戴着魔法帽，拿着魔法棒',
    '老板风': '穿着超市店员服装，拿着扩音器',
  }

  const buildInputFromPresets = (presets: { expression?: string; action?: string; style?: string }) => {
    const expr = presets.expression || '[表情]'
    const act = presets.action || '[动作]'
    const scn = presets.style || '[场景]'
    return `我想生成一个 ${expr} ， ${act} ，${scn} 的joy`
  }

  const insertPreset = (text: string, type: 'expression' | 'action' | 'style' | 'perspective') => {
    // 视角类型单独处理
    if (type === 'perspective') {
      setPerspective(text)
      return
    }
    const actual = type === 'style' ? (SCENE_MAP[text] || text) : text
    const next = { ...selectedPresets, [type]: actual }
    setSelectedPresets(next)
    setInput(buildInputFromPresets(next))
  }

  const clearChat = () => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    cancelRunningLogHide()
    const defaultInput = '我想生成一个 [表情] ， [动作] ，[场景] 的joy'
    setMessages([])
    setInput(defaultInput)
    setSelectedPresets({})
    setComplianceError(false)
    setIsLoading(false)
    setHoveredImage(null)
    setThreeModalOpen(false)
    setRenderPreviewUrl(null)
    setRenderFilePath(null)
    setQueueInfo(null)
    setCurrentJobId(null)
    setThreePrompt('')
    setChatStatus('idle')
    setAnalysisResult(null)
    setPendingPrompt('')
    setRunningLogActive(false)
    clearRunningLog()
    persistState([], defaultInput, {}, 0)
    const key = getRouteKey()
    const el = scrollContainerRef.current
    if (el) {
      el.scrollTop = 0
      saveScrollPos(key, 0)
    }
  }

  // 测试函数：添加多条消息来测试滚动
  const addTestMessages = () => {
    const testMessages: Message[] = []
    for (let i = 1; i <= 5; i++) {
      testMessages.push({
        id: `test-${Date.now()}-${i}`,
        type: i % 2 === 0 ? 'assistant' : 'user',
        content: `测试消息 ${i} - 这是一条用于测试滚动功能的长文本消息。\n为了确保内容足够长以触发滚动，我们重复这段话：\n随着消息列表的增加，页面应该自动平滑滚动到底部，以便用户始终能看到最新的对话内容。`,
        timestamp: new Date()
      })
    }
    setMessages(prev => {
      const updated = [...prev, ...testMessages]
      // 手动触发一次状态保存，确保新消息被记录
      persistState(updated, input, selectedPresets)
      return updated
    })

    // 强制触发一次滚动
    setTimeout(() => scrollToBottom(true), 100)
  }


  const handleSend = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim()
    if (!text || isLoading) return

    if (threeModalOpen) handleThreeModalOpenChange(false)

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: text,
      timestamp: new Date()
    }

    setMessages(prev => {
      const nextMessages: Message[] = [userMessage]

      // 2D 底图存在时：若 prompt 仍包含表情/动作信息，则提示“底图已锁定动作表情”
      if (generationMode === '2D' && twoDBaseImageUrl) {
        const keywords = ['表情', '动作', '站姿', '站立', '坐姿', '跳跃', '跑动', '欢快', '开心', '[表情]', '[动作]']
        const needHint = keywords.some(k => text.includes(k))
        if (needHint) {
          nextMessages.push({
            id: `${Date.now()}-2d-base-hint`,
            type: 'assistant',
            content: '提示：底图已锁定动作表情，仅处理配件/背景',
            timestamp: new Date()
          })
        }
      }

      const updated = [...prev, ...nextMessages]
      persistState(updated, '', selectedPresets)
      return updated
    })
    setInput('')
    cancelRunningLogHide()
    setRunningLogActive(true)
    clearRunningLog()
    setIsLoading(true)

    let requestId = ''
    try {
      requestId =
        globalThis.crypto?.randomUUID?.() ??
        `${Date.now()}-${Math.random().toString(16).slice(2)}`

      if (renderFilePath) {
        const currentRenderPath = renderFilePath
        setRenderFilePath(null)
        setRenderPreviewUrl(null)
        setThreePrompt('')

        const runRes = await axios.post(
          '/api/run-3d-banana',
          { imagePath: currentRenderPath, promptText: text },
          { timeout: 0, headers: { 'X-Request-ID': requestId } }  // 取消超时限制
        )
        if (runRes.data?.success && runRes.data?.url) {
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: '已根据渲染图生成结果',
            images: [runRes.data.url],
            mode: '3D',
            timestamp: new Date()
          }
          setMessages(prev => {
            const updated = [...prev, assistantMessage]
            persistState(updated, input, selectedPresets)
            return updated
          })
        } else {
          // 检查是否为违规词检查失败
          const isComplianceError = runRes.data?.code === 'COMPLIANCE' || String(runRes.data?.error || '').includes('不合规')
          setComplianceError(!!isComplianceError)

          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: isComplianceError
              ? '输入内容不符合规范，请重新描述你的需求'
              : `生成失败: ${runRes.data?.error || '未知错误'}`,
            timestamp: new Date()
          }
          setMessages(prev => {
            const updated = [...prev, errorMessage]
            persistState(updated, input, selectedPresets)
            return updated
          })
        }
        setIsLoading(false)
        scheduleRunningLogHide()
        return
      }

      // 第一步：分析内容（异步轮询，避免网关/反代超时）
      setChatStatus('analyzing')
      const analyzeRes = await axios.post(
        '/api/analyze',
        {
          requirement: text,
          mode: generationMode,
          perspective: generationMode === '2D' ? perspective : undefined,
          async: true
        },
        { timeout: 0, headers: { 'X-Request-ID': requestId } }  // timeout: 0 表示无超时限制
      )

      if (!analyzeRes.data?.success) {
        const needComplianceMsg = analyzeRes.data?.code === 'COMPLIANCE' || !analyzeRes.data?.compliant || String(analyzeRes.data?.reason || analyzeRes.data?.error || '').includes('违规')
        setComplianceError(!!needComplianceMsg)
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: needComplianceMsg
            ? '输入内容不符合规范，请重新描述你的需求'
            : `分析失败: ${analyzeRes.data?.reason || analyzeRes.data?.error || '未知错误'}`,
          timestamp: new Date()
        }
        setMessages(prev => {
          const updated = [...prev, errorMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
        setIsLoading(false)
        setChatStatus('idle')
        scheduleRunningLogHide()
        return
      }

      // 兼容：如果后端直接返回 analysis（同步模式）
      if (analyzeRes.data?.analysis) {
        const analysis = analyzeRes.data.analysis as AnalysisResult
        setAnalysisResult(analysis)
        setPendingPrompt(text)
        setChatStatus('preview')
        setIsLoading(false)
        return
      }

      const analyzeJobId = analyzeRes.data?.job_id as string | undefined
      if (!analyzeJobId) {
        throw new Error('分析任务启动失败: 缺少 job_id')
      }

      const deadline = Date.now() + 600000  // 10分钟超时
      let retryCount = 0
      const MAX_RETRIES = 400  // 最多重试 400 次（前30秒1秒间隔=30次，后9.5分钟2秒间隔=285次，总计约10分钟）
      
      while (true) {
        retryCount++
        
        // 多重退出条件保护
        if (Date.now() > deadline) {
          console.error('分析超时: 超过时间限制')
          throw new Error('分析超时，请稍后重试')
        }
        
        if (retryCount > MAX_RETRIES) {
          console.error('分析超时: 超过最大重试次数')
          throw new Error('分析超时，请稍后重试')
        }
        
        try {
          const statusRes = await axios.get(`/api/job/${analyzeJobId}/status`, {
            timeout: 0,  // 取消超时限制
            headers: { 'X-Request-ID': requestId }
          })
          if (statusRes.data?.success) {
            const job = statusRes.data.job as any
            updateRunningLog(job?.latest_log)
            if (job?.status === 'succeeded') {
              const analysis = job.analysis as AnalysisResult
              setComplianceError(false)
              setAnalysisResult(analysis)
              setPendingPrompt(text)
              setChatStatus('preview')
              setIsLoading(false)
              return
            }

            if (job?.status === 'failed' || job?.status === 'cancelled') {
              const reasonText = String(job?.details?.reason || job?.error || '未知错误')
              const needComplianceMsg = job?.details?.code === 'COMPLIANCE' || reasonText.includes('不合规') || reasonText.includes('违规')
              setComplianceError(!!needComplianceMsg)
              const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                type: 'assistant',
                content: needComplianceMsg ? '输入内容不符合规范，请重新描述你的需求' : `分析失败: ${reasonText}`,
                timestamp: new Date()
              }
              setMessages(prev => {
                const updated = [...prev, errorMessage]
                persistState(updated, input, selectedPresets)
                return updated
              })
              setIsLoading(false)
              setChatStatus('idle')
              scheduleRunningLogHide()
              return
            }
          }
        } catch (pollError) {
          console.warn(`轮询第 ${retryCount} 次失败:`, pollError)
          // ignore and retry
        }

        // 动态轮询间隔：前30秒每1秒检查一次，之后每2秒检查一次
        const pollInterval = retryCount <= 30 ? 1000 : 2000
        await new Promise(resolve => setTimeout(resolve, pollInterval))
      }

    } catch (error: any) {
      let errorText = '分析失败: 未知错误'
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.message?.includes('超时')) {
        errorText = '分析超时，请稍后重试'
      } else if (error?.response?.data?.error) {
        errorText = `分析失败: ${error.response.data.error}`
      } else if (error.message) {
        errorText = `错误: ${error.message}`
      }
      if (typeof requestId === 'string' && requestId) {
        errorText = `${errorText} (request_id: ${requestId})`
      }
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: errorText,
        timestamp: new Date()
      }
      setMessages(prev => {
        const updated = [...prev, errorMessage]
        persistState(updated, input, selectedPresets)
        return updated
      })
      setIsLoading(false)
      setChatStatus('idle')
      scheduleRunningLogHide()
    }
  }

  // 确认分析结果，开始生成
  const handleConfirmAnalysis = async () => {
    if (!analysisResult || !pendingPrompt) return

    cancelRunningLogHide()
    setRunningLogActive(true)
    setIsLoading(true)
    setChatStatus('generating')
    clearRunningLog()

    try {
      const modeAtStart = generationMode
      const startRes = await axios.post('/api/start_generate', {
        requirement: pendingPrompt,
        analysis: analysisResult,  // 传递用户确认/编辑后的分析结果
        mode: modeAtStart,
        perspective: modeAtStart === '2D' ? perspective : undefined,
        ...(modeAtStart === '2D' && twoDBaseImageUrl ? { base_image_url: twoDBaseImageUrl } : {})
      }, { timeout: 0 })  // 取消超时限制

      if (!startRes.data?.success || !startRes.data?.job_id) {
        const needComplianceMsg = startRes.data?.code === 'COMPLIANCE' || String(startRes.data?.error || '').includes('违规')
        const isQueueFull = startRes.data?.code === 'QUEUE_FULL'
        setComplianceError(!!needComplianceMsg)
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: needComplianceMsg
            ? '输入内容不符合规范，请重新描述你的需求'
            : (isQueueFull ? '当前排队人数较多，请稍后重试' : `生成失败: ${startRes.data?.error || '启动任务失败'}`),
          timestamp: new Date()
        }
        setMessages(prev => {
          const updated = [...prev, errorMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
        setIsLoading(false)
        setChatStatus('idle')
        setAnalysisResult(null)
        setPendingPrompt('')
        scheduleRunningLogHide()
        return
      }

      const jobId: string = startRes.data.job_id
      setCurrentJobId(jobId)
      setAnalysisResult(null)
      setPendingPrompt('')

      // 设置初始队列信息
      if (startRes.data.queue_position > 0) {
        setQueueInfo({
          position: startRes.data.queue_position,
          estimatedWait: startRes.data.estimated_wait || 0,
          runningCount: startRes.data.queue_stats?.running_count || 0,
          waitingCount: startRes.data.queue_stats?.waiting_count || 0
        })
      }

      const computePollInterval = (job: any): number => {
        const status = String(job?.status || '')
        const stage = String(job?.stage || '')
        const position = Number(job?.queue_position || 0)
        const estimatedWait = Number(job?.estimated_wait || 0)

        // 排队中：降低轮询频率，减少后端压力
        if (status === 'queued' || position > 0) {
          if (estimatedWait >= 120 || position >= 10) return 10000
          if (estimatedWait >= 30 || position >= 3) return 6000
          return 4000
        }

        // 运行中：根据阶段适当降频
        if (status === 'running') {
          if (stage === 'decorate' || stage === 'gate') return 2500
          if (stage === 'compose') return 2000
          return 1500
        }

        // 结束态不再轮询
        return 0
      }

      const scheduleNextPoll = (delayMs: number) => {
        if (pollTimerRef.current) {
          clearTimeout(pollTimerRef.current)
          pollTimerRef.current = null
        }
        if (delayMs <= 0) return
        pollTimerRef.current = window.setTimeout(() => {
          void pollOnce()
        }, delayMs)
      }

      const pollOnce = async () => {
        try {
          const res = await axios.get(`/api/job/${jobId}/status`, { timeout: 0 })
          if (!res.data?.success) {
            scheduleNextPoll(2000)
            return
          }
          const job = res.data.job
          updateRunningLog(job?.latest_log)

          if (job.queue_position > 0) {
            setQueueInfo({
              position: job.queue_position,
              estimatedWait: job.estimated_wait || 0,
              runningCount: 0,
              waitingCount: 0
            })
          } else if (job.status === 'running') {
            setQueueInfo(null)
          }

          if (job.status === 'succeeded') {
            if (pollTimerRef.current) {
              clearTimeout(pollTimerRef.current)
              pollTimerRef.current = null
            }
            setComplianceError(false)
            setQueueInfo(null)
            setCurrentJobId(null)
            setChatStatus('idle')
            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: '已为您生成图片',
              images: Array.isArray(job.images) ? job.images : [],
              mode: modeAtStart,
              timestamp: new Date()
            }
            setMessages(prev => {
              const updated = [...prev, assistantMessage]
              persistState(updated, input, selectedPresets)
              return updated
            })
            setIsLoading(false)
            scheduleRunningLogHide()
            return
          }

          if (job.status === 'failed' || job.status === 'cancelled') {
            if (pollTimerRef.current) {
              clearTimeout(pollTimerRef.current)
              pollTimerRef.current = null
            }
            setQueueInfo(null)
            setCurrentJobId(null)
            setChatStatus('idle')
            const needComplianceMsg = job?.details?.code === 'COMPLIANCE' || String(job?.error || '').includes('违规')
            setComplianceError(!!needComplianceMsg)
            const errorMessage: Message = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: needComplianceMsg ? '输入内容不符合规范，请重新描述你的需求' : `生成失败: ${job?.error || '任务失败'}`,
              timestamp: new Date()
            }
            setMessages(prev => {
              const updated = [...prev, errorMessage]
              persistState(updated, input, selectedPresets)
              return updated
            })
            setIsLoading(false)
            scheduleRunningLogHide()
            return
          }

          scheduleNextPoll(computePollInterval(job) || 2000)
        } catch (err) {
          scheduleNextPoll(3000)
        }
      }

      await pollOnce()
    } catch (error: any) {
      let errorText = '生成失败: 未知错误'
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorText = '生成超时: 图片生成过程较长，请稍后重试。'
      } else if (error?.response?.data?.error) {
        const needComplianceMsg = error?.response?.data?.code === 'COMPLIANCE' || String(error.response.data.error || '').includes('违规')
        setComplianceError(!!needComplianceMsg)
        errorText = needComplianceMsg ? '输入内容不符合规范，请重新描述你的需求' : `生成失败: ${error.response.data.error}`
      } else if (error.message) {
        errorText = `错误: ${error.message}`
      }
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: errorText,
        timestamp: new Date()
      }
      setMessages(prev => {
        const updated = [...prev, errorMessage]
        persistState(updated, input, selectedPresets)
        return updated
      })
      setQueueInfo(null)
      setCurrentJobId(null)
      setChatStatus('idle')
      setAnalysisResult(null)
      setPendingPrompt('')
      setIsLoading(false)
      scheduleRunningLogHide()
    }
  }

  // 取消分析预览
  const handleCancelAnalysis = () => {
    setChatStatus('idle')
    setAnalysisResult(null)
    setPendingPrompt('')
    setIsLoading(false)
    scheduleRunningLogHide()
  }

  // 取消排队中的任务
  const handleCancelJob = async () => {
    if (!currentJobId) return
    try {
      await axios.post(`/api/job/${currentJobId}/cancel`)
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current)
        pollTimerRef.current = null
      }
      setQueueInfo(null)
      setCurrentJobId(null)
      setIsLoading(false)
      scheduleRunningLogHide()

      const cancelMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '任务已取消',
        timestamp: new Date()
      }
      setMessages(prev => {
        const updated = [...prev, cancelMessage]
        persistState(updated, input, selectedPresets)
        return updated
      })
    } catch (err) {
      console.error('取消任务失败:', err)
    }
  }


  useEffect(() => {
    const el = scrollContainerRef.current
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current)
        pollTimerRef.current = null
      }
      cancelRunningLogHide()
      if (el && typeof window !== 'undefined') {
        saveScrollPos(getRouteKey(), el.scrollTop)
      }
    }
  }, [])

  const downloadImage = async (imageUrl: string) => {
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `joy_ip_${Date.now()}.png`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
    }
  }

  const handleImageClick = (imageUrl: string) => {
    const el = scrollContainerRef.current
    const currentScrollTop = el ? el.scrollTop : 0
    if (typeof window !== 'undefined') {
      saveScrollPos(getRouteKey(), currentScrollTop)
    }

    // 对于 base64 图片，使用 sessionStorage 传递以避免 URL 过长
    if (imageUrl.startsWith('data:')) {
      try {
        sessionStorage.setItem('pending_detail_image', imageUrl)
        router.push('/detail?image=pending', { scroll: false })
      } catch (e) {
        console.error('存储图片失败:', e)
        // 如果存储失败，尝试直接跳转（可能会失败）
        router.push(`/detail?image=${encodeURIComponent(imageUrl)}`, { scroll: false })
      }
    } else {
      router.push(`/detail?image=${encodeURIComponent(imageUrl)}`, { scroll: false })
    }
  }

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      const data = e.data
      if (!data || typeof data !== 'object') return

      if (data.type === 'three-editor-hq-render') {
        console.log('[3D Editor] 收到渲染预览', data)
        setRenderPreviewUrl(data.dataURL)
      } else if (data.type === 'three-editor-hq-saved') {
        console.log('[3D Editor] 收到保存完成', data)
        setRenderFilePath(data.filePath || null)
        setRenderPreviewUrl(data.previewUrl || data.url || null)
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  // 切换视角/2D-3D 模式时，自动清空 2D 底图预览条（并关闭编辑器弹窗）
  useEffect(() => {
    setTwoDBaseImageUrl(null)
    setTwoDEditorOpen(false)
  }, [generationMode, perspective])

  useEffect(() => {
    const handler = () => {
      const el = scrollContainerRef.current
      if (!el) return
      const st = readScrollPos(getRouteKey())
      if (typeof st === 'number' && st >= 0) {
        restoreElementScroll(el, st, { smooth: true, retries: 2 })
      }
    }
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const TwoDBasePreview = () => {
    if (generationMode !== '2D' || !twoDBaseImageUrl) return null
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4">
        <span className="text-sm text-gray-300">已选择2D底图：</span>
        <img
          src={twoDBaseImageUrl}
          alt="2D底图预览"
          className="w-16 h-16 object-cover rounded border border-gray-600 bg-white"
        />
        <button
          className="text-xs text-gray-400 hover:text-white ml-2"
          onClick={() => setTwoDBaseImageUrl(null)}
        >
          清除
        </button>
        <button
          className="text-xs text-gray-400 hover:text-white"
          onClick={() => setTwoDEditorOpen(true)}
        >
          替换
        </button>
      </div>
    )
  }

  const RenderPreview = () => {
    if (!renderPreviewUrl || threeModalOpen) return null
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4">
        <span className="text-sm text-gray-300">已渲染预览：</span>
        <img src={renderPreviewUrl} alt="渲染预览" className="w-16 h-16 object-cover rounded border border-gray-600" />
        <button
          className="text-xs text-gray-400 hover:text-white ml-2"
          onClick={() => { setRenderPreviewUrl(null); setRenderFilePath(null) }}
        >
          清除
        </button>
      </div>
    )
  }

  // 分析中的加载提示
  const AnalyzingIndicator = () => {
    if (chatStatus !== 'analyzing') return null
    return (
      <div className="my-6 max-w-lg">
        <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black/20 backdrop-blur-xl shadow-2xl transition-all duration-500">
          {/* 玻璃反光层 */}
          <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent pointer-events-none" />

          <div className="relative flex items-center gap-5 p-5">
            {/* 科技感动态图标 */}
            <div className="relative flex items-center justify-center w-10 h-10 flex-shrink-0">
              <div className="absolute inset-0 rounded-full border border-white/10" />
              <div className="absolute inset-0 rounded-full border-t border-white/80 animate-spin shadow-[0_0_15px_rgba(255,255,255,0.2)]" />
              <div className="absolute inset-3 rounded-full border border-white/30 animate-[spin_3s_linear_infinite_reverse]" />
              <div className="w-1.5 h-1.5 bg-white rounded-full shadow-[0_0_10px_white] animate-pulse" />
            </div>

            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-white/90 tracking-widest uppercase flex items-center gap-2">
                Analyzing
                <span className="flex space-x-1 opacity-60">
                  <span className="w-0.5 h-0.5 bg-white rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-0.5 h-0.5 bg-white rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-0.5 h-0.5 bg-white rounded-full animate-bounce"></span>
                </span>
              </span>
              <span className="text-xs text-white/40 font-light mt-1 truncate">
                AI 正在解构您的创意需求，构建场景元素...
              </span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const handleThreeSend = async () => {
    if (!threePrompt.trim()) return
    if (!renderFilePath) return
    handleThreeModalOpenChange(false)
    setInput(threePrompt)
    setTimeout(() => handleSend(threePrompt), 100)
  }

  return (
    <div className="h-screen w-full bg-gradient-to-b from-[#202020] to-[#1c2033] text-white overflow-hidden">
      <ThreeEditorModal
        open={threeModalOpen}
        onOpenChange={handleThreeModalOpenChange}
        renderPreviewUrl={renderPreviewUrl}
        renderFilePath={renderFilePath}
        threePrompt={threePrompt}
        onThreePromptChange={setThreePrompt}
        isLoading={isLoading}
        onGenerate={handleThreeSend}
      />
      <TwoDEditorModal
        open={twoDEditorOpen}
        onOpenChange={setTwoDEditorOpen}
        perspective={perspective}
        onUse={(baseImageUrl) => setTwoDBaseImageUrl(baseImageUrl)}
      />
      <div className="max-w-5xl mx-auto flex flex-col h-full min-h-0">
        {isInitial ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 overflow-y-auto">
            <h1 className="text-[36px] font-extrabold tracking-tight mb-6">创造你想要的JOY</h1>
            <div className="w-full max-w-[915px] relative">
              <TwoDBasePreview />
              <RenderPreview />
              <ChatInput
                input={input}
                setInput={setInput}
                handleSend={handleSend}
	                isLoading={isLoading}
	                insertPreset={insertPreset}
                  runningLogVisible={showRunningLogBar}
                  runningLogText={runningLogText}
	                variant="center"
	                onOpenThreeTest={() => handleThreeModalOpenChange(true)}
                  onOpenTwoDEditor={() => setTwoDEditorOpen(true)}
	                generationMode={generationMode}
	                setGenerationMode={setGenerationMode}
                perspective={perspective}
                setPerspective={setPerspective}
              />
            </div>
          </div>
        ) : (
          <>
            <ChatHeader clearChat={clearChat} />
            <div className="relative flex-1 min-h-0 flex flex-col">
              <MessageArea
                messages={messages}
                scrollContainerRef={scrollContainerRef}
                hoveredImage={hoveredImage}
                setHoveredImage={setHoveredImage}
                handleImageClick={handleImageClick}
                downloadImage={downloadImage}
                isLoading={isLoading && chatStatus === 'generating'}
                showComplianceMsg={complianceError}
                queueInfo={queueInfo}
                onCancelJob={handleCancelJob}
                bottomActions={{
                  lastAssistantWithImages: lastAssistantImagesOnly,
                  lastUserPrompt,
                  onEdit: () => setInput(lastUserPrompt || ''),
                  onRegenerate: () => handleSend(lastUserPrompt || input)
                }}
                customContent={
                  <>
                    <AnalyzingIndicator />
                    {showAnalysisPreview && (
                      <div className="my-4">
                        <AnalysisPreview
                          analysis={analysisResult}
                          onAnalysisChange={setAnalysisResult}
                          onConfirm={handleConfirmAnalysis}
                          onCancel={handleCancelAnalysis}
                          isGenerating={false}
                          originalPrompt={pendingPrompt}
                        />
                      </div>
                    )}
                  </>
                }
              />
            </div>

            <div className="relative">
		              <TwoDBasePreview />
		              <RenderPreview />
		              <ChatInput
		                input={input}
		                setInput={setInput}
		                handleSend={handleSend}
		                isLoading={isLoading}
	                insertPreset={insertPreset}
	                onOpenThreeTest={() => handleThreeModalOpenChange(true)}
                  onOpenTwoDEditor={() => setTwoDEditorOpen(true)}
                  runningLogVisible={showRunningLogBar}
                  runningLogText={runningLogText}
	                variant="center"
	                generationMode={generationMode}
	                setGenerationMode={setGenerationMode}
	                perspective={perspective}
                setPerspective={setPerspective}
              />
            </div>
          </>
        )}
      </div>
      {/* 2D/3D 模式切换提示 */}
      <NoticeModal />
    </div>
  )
}
