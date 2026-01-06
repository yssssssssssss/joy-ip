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

  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const pollTimerRef = useRef<number | null>(null)
  const scrollAnimationFrameRef = useRef<number | null>(null)
  const autoScrollRef = useRef<boolean>(true) // 控制是否自动滚动

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
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
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

    if (threeModalOpen) setThreeModalOpen(false)

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: text,
      timestamp: new Date()
    }

    setMessages(prev => {
      const updated = [...prev, userMessage]
      persistState(updated, '', selectedPresets)
      return updated
    })
    setInput('')
    setIsLoading(true)

    try {
      if (renderFilePath) {
        const currentRenderPath = renderFilePath
        setRenderFilePath(null)
        setRenderPreviewUrl(null)
        setThreePrompt('')

        const runRes = await axios.post('/api/run-3d-banana', { imagePath: currentRenderPath, promptText: text }, { timeout: 120000 })
        if (runRes.data?.success && runRes.data?.url) {
          const assistantMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: 'assistant',
            content: '已根据渲染图生成结果',
            images: [runRes.data.url],
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
        return
      }

      // 第一步：分析内容（增加超时时间，因为后端可能有多次AI调用）
      setChatStatus('analyzing')
      const analyzeRes = await axios.post('/api/analyze', {
        requirement: text,
        mode: generationMode,
        perspective: generationMode === '2D' ? perspective : undefined
      }, { timeout: 180000 })

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
        return
      }

      // 分析成功，显示预览
      const analysis = analyzeRes.data.analysis as AnalysisResult
      setAnalysisResult(analysis)
      setPendingPrompt(text)
      setChatStatus('preview')
      setIsLoading(false)

    } catch (error: any) {
      let errorText = '分析失败: 未知错误'
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorText = '分析超时，请稍后重试'
      } else if (error?.response?.data?.error) {
        errorText = `分析失败: ${error.response.data.error}`
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
      setIsLoading(false)
      setChatStatus('idle')
    }
  }

  // 确认分析结果，开始生成
  const handleConfirmAnalysis = async () => {
    if (!analysisResult || !pendingPrompt) return

    setIsLoading(true)
    setChatStatus('generating')

    try {
      const startRes = await axios.post('/api/start_generate', {
        requirement: pendingPrompt,
        analysis: analysisResult,  // 传递用户确认/编辑后的分析结果
        mode: generationMode,
        perspective: generationMode === '2D' ? perspective : undefined
      }, { timeout: 60000 })

      if (!startRes.data?.success || !startRes.data?.job_id) {
        const needComplianceMsg = startRes.data?.code === 'COMPLIANCE' || String(startRes.data?.error || '').includes('违规')
        setComplianceError(!!needComplianceMsg)
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: needComplianceMsg ? '输入内容不符合规范，请重新描述你的需求' : `生成失败: ${startRes.data?.error || '启动任务失败'}`,
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

      const checkStatus = async () => {
        try {
          const res = await axios.get(`/api/job/${jobId}/status`, { timeout: 60000 })
          if (!res.data?.success) return
          const job = res.data.job

          // 更新队列信息
          if (job.queue_position > 0) {
            setQueueInfo({
              position: job.queue_position,
              estimatedWait: job.estimated_wait || 0,
              runningCount: 0,
              waitingCount: 0
            })
          } else if (job.status === 'running') {
            setQueueInfo(null) // 已开始执行，清除队列信息
          }

          if (job.status === 'succeeded') {
            if (pollTimerRef.current) {
              clearInterval(pollTimerRef.current)
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
              timestamp: new Date()
            }
            setMessages(prev => {
              const updated = [...prev, assistantMessage]
              persistState(updated, input, selectedPresets)
              return updated
            })
            setIsLoading(false)
          } else if (job.status === 'failed' || job.status === 'cancelled') {
            if (pollTimerRef.current) {
              clearInterval(pollTimerRef.current)
              pollTimerRef.current = null
            }
            setQueueInfo(null)
            setCurrentJobId(null)
            setChatStatus('idle')
            const needComplianceMsg = job?.code === 'COMPLIANCE' || String(job?.error || '').includes('违规')
            setComplianceError(!!needComplianceMsg)
            const errorMessage: Message = {
              id: (Date.now() + 1).toString(),
              type: 'assistant',
              content: job.status === 'cancelled'
                ? '任务已取消'
                : (needComplianceMsg ? '输入内容不符合规范，请重新描述你的需求' : `生成失败: ${job.error || '未知错误'}`),
              timestamp: new Date()
            }
            setMessages(prev => {
              const updated = [...prev, errorMessage]
              persistState(updated, input, selectedPresets)
              return updated
            })
            setIsLoading(false)
          }
        } catch (err) {
          // ignore
        }
      }

      await checkStatus()
      pollTimerRef.current = window.setInterval(checkStatus, 2500)
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
    }
  }

  // 取消分析预览
  const handleCancelAnalysis = () => {
    setChatStatus('idle')
    setAnalysisResult(null)
    setPendingPrompt('')
    setIsLoading(false)
  }

  // 取消排队中的任务
  const handleCancelJob = async () => {
    if (!currentJobId) return
    try {
      await axios.post(`/api/job/${currentJobId}/cancel`)
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      setQueueInfo(null)
      setCurrentJobId(null)
      setIsLoading(false)

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
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
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
    router.push(`/detail?image=${encodeURIComponent(imageUrl)}`, { scroll: false })
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
    setThreeModalOpen(false)
    setInput(threePrompt)
    setTimeout(() => handleSend(threePrompt), 100)
  }

  const threeInputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="h-screen w-full bg-gradient-to-b from-[#202020] to-[#1c2033] text-white overflow-hidden">
      <div className="max-w-5xl mx-auto flex flex-col h-full min-h-0">
        {isInitial ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 overflow-y-auto">
            <h1 className="text-[36px] font-extrabold tracking-tight mb-6">创造你想要的JOY</h1>
            <div className="w-full max-w-[915px] relative">
              {/* 3D Editor Modal - inline JSX to avoid re-render issues */}
              {threeModalOpen && (
                <div className="w-full mb-4">
                  <div className="bg-[#0f1419] border border-gray-700 rounded-lg w-full max-w-[1000px] mx-auto overflow-hidden shadow-2xl" style={{ height: '1000px' }}>
                    <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
                      <div className="text-sm text-gray-300">JOY 3D 编辑器</div>
                      <button className="px-3 py-1 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded" onClick={() => setThreeModalOpen(false)}>关闭</button>
                    </div>
                    <iframe src="/three-editor/index.html" title="3D Editor" className="w-full" style={{ height: 'calc(100% - 120px)' }} />
                    <div className="px-4 py-3 border-t border-gray-700 bg-[#1a1d24]">
                      <div className="flex items-center gap-3">
                        {renderPreviewUrl && (
                          <img src={renderPreviewUrl} alt="渲染预览" className="w-12 h-12 object-cover rounded border border-gray-600 flex-shrink-0" />
                        )}
                        <input
                          ref={threeInputRef}
                          type="text"
                          value={threePrompt}
                          onChange={e => setThreePrompt(e.target.value)}
                          onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') handleThreeSend(); }}
                          placeholder={renderFilePath ? "输入描述，然后点击生成" : "请先点击上方的开始渲染按钮"}
                          className="flex-1 h-[44px] px-4 bg-[#2b2d33] text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none placeholder:text-gray-500"
                        />
                        <button
                          onClick={handleThreeSend}
                          disabled={!renderFilePath || !threePrompt.trim() || isLoading}
                          className="h-[44px] px-6 bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                        >
                          {isLoading ? '生成中...' : '生成'}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        {renderFilePath ? '✓ 渲染图已准备好，输入描述后点击生成' : '⚠ 请先在编辑器中点击开始渲染按钮'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <RenderPreview />
              <ChatInput
                input={input}
                setInput={setInput}
                handleSend={handleSend}
                isLoading={isLoading}
                insertPreset={insertPreset}
                variant="center"
                onOpenThreeTest={() => setThreeModalOpen(true)}
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
              {/* 3D Editor Modal - inline JSX to avoid re-render issues */}
              {threeModalOpen && (
                <div className="w-full mb-4">
                  <div className="bg-[#0f1419] border border-gray-700 rounded-lg w-full max-w-[1000px] mx-auto overflow-hidden shadow-2xl" style={{ height: '1000px' }}>
                    <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
                      <div className="text-sm text-gray-300">JOY 3D 编辑器</div>
                      <button className="px-3 py-1 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded" onClick={() => setThreeModalOpen(false)}>关闭</button>
                    </div>
                    <iframe src="/three-editor/index.html" title="3D Editor" className="w-full" style={{ height: 'calc(100% - 120px)' }} />
                    <div className="px-4 py-3 border-t border-gray-700 bg-[#1a1d24]">
                      <div className="flex items-center gap-3">
                        {renderPreviewUrl && (
                          <img src={renderPreviewUrl} alt="渲染预览" className="w-12 h-12 object-cover rounded border border-gray-600 flex-shrink-0" />
                        )}
                        <input
                          ref={threeInputRef}
                          type="text"
                          value={threePrompt}
                          onChange={e => setThreePrompt(e.target.value)}
                          onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') handleThreeSend(); }}
                          placeholder={renderFilePath ? "输入描述，然后点击生成" : "请先点击上方的开始渲染按钮"}
                          className="flex-1 h-[44px] px-4 bg-[#2b2d33] text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none placeholder:text-gray-500"
                        />
                        <button
                          onClick={handleThreeSend}
                          disabled={!renderFilePath || !threePrompt.trim() || isLoading}
                          className="h-[44px] px-6 bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                        >
                          {isLoading ? '生成中...' : '生成'}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        {renderFilePath ? '✓ 渲染图已准备好，输入描述后点击生成' : '⚠ 请先在编辑器中点击开始渲染按钮'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <RenderPreview />
              <ChatInput
                input={input}
                setInput={setInput}
                handleSend={handleSend}
                isLoading={isLoading}
                insertPreset={insertPreset}
                onOpenThreeTest={() => setThreeModalOpen(true)}
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
    </div>
  )
}
