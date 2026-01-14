"use client"

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ArrowLeft, Download, Share2, Heart, ZoomIn, ZoomOut, Upload, Undo2, Check, Brush } from 'lucide-react'
import { useSearchParams, useRouter } from 'next/navigation'
import { getRouteKey, saveScrollPos } from '@/lib/scrollMemory'
import AnimatedButton2 from '@/components/button/button2/AnimatedButton2'
import { useChatState, Message } from '@/app/providers'

// 海报合并的系统级 Prompt（不展示给用户）
const MERGE_SYSTEM_PROMPT = `
将图2中的角色复制到图1中的绿色区域，让图2角色的角度和光影质感根据图1进行调整
`.trim()

// 用户可见的默认 Prompt
const MERGE_USER_PROMPT = '将图2中的角色，复制到图1中的mask区域'

// 仅客户端渲染的时间，避免 SSR 与客户端格式差异导致 Hydration 问题
function ClientTime({ locale = 'zh-CN' }: { locale?: string }) {
  const [text, setText] = useState('')
  useEffect(() => {
    try {
      setText(new Date().toLocaleString(locale))
    } catch {
      // 兜底：不可用时用 ISO 格式片段
      const d = new Date()
      setText(
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ` +
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
      )
    }
  }, [locale])
  return <span suppressHydrationWarning>{text || ' '}</span>
}

export default function DetailView() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const imageUrlParam = searchParams.get('image') || ''
  const { messages, setMessages, persistState, input, selectedPresets } = useChatState()

  // 处理从 sessionStorage 读取的 pending 图片
  const [currentImage, setCurrentImage] = useState<string>('')

  useEffect(() => {
    if (imageUrlParam === 'pending') {
      // 从 sessionStorage 读取图片
      const pendingImage = sessionStorage.getItem('pending_detail_image')
      if (pendingImage) {
        setCurrentImage(pendingImage)
        // 读取后清除，避免重复
        sessionStorage.removeItem('pending_detail_image')
      }
    } else if (imageUrlParam) {
      setCurrentImage(imageUrlParam)
    }
  }, [imageUrlParam])

  // 使用 currentImage 替代原来的 imageUrl
  const imageUrl = currentImage

  const [scale, setScale] = useState(1)
  const [liked, setLiked] = useState(false)
  const [tagImgUrl, setTagImgUrl] = useState<string>('')
  const [showBgInput, setShowBgInput] = useState(false)
  const [bgText, setBgText] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [resultImages, setResultImages] = useState<Array<{ url: string, source: string }>>([])
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [debugInfo, setDebugInfo] = useState<any>(null)
  const [selectedIndex, setSelectedIndex] = useState<number>(0)
  const [showOptimizeDialog, setShowOptimizeDialog] = useState(false)
  const [showApplyDialog, setShowApplyDialog] = useState(false)
  const [showAngleDialog, setShowAngleDialog] = useState(false)
  const [applyText, setApplyText] = useState('')
  const [optimizeText, setOptimizeText] = useState('')

  // 海报 Mask 合并模式状态
  const [showMergeMode, setShowMergeMode] = useState(false)
  const [posterImage, setPosterImage] = useState<string | null>(null)
  const [maskData, setMaskData] = useState<string | null>(null)
  const [visibleCanvasData, setVisibleCanvasData] = useState<string | null>(null)  // 保存可见画布快照（绿色 mask）
  const [brushSize, setBrushSize] = useState(40)
  const [mergePrompt, setMergePrompt] = useState('')
  const [showBrushTools, setShowBrushTools] = useState(false)
  const [drawHistory, setDrawHistory] = useState<ImageData[]>([])
  const [isMerging, setIsMerging] = useState(false)
  const posterCanvasRef = React.useRef<HTMLCanvasElement>(null)
  const maskCanvasRef = React.useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [posterDimensions, setPosterDimensions] = useState<{ width: number, height: number } | null>(null)
  const [canvasDisplaySize, setCanvasDisplaySize] = useState<{ width: number, height: number } | null>(null)

  // 下载图片
  const downloadImage = async () => {
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `image_${Date.now()}.png`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
    }
  }

  // 下载特定生成的图片
  const downloadGeneratedImage = async (imageUrl: string, source: string) => {
    try {
      const response = await fetch(decodeURIComponent(imageUrl))
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `generated_${source.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}.png`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
    }
  }

  // 压缩 base64 图片以适配 localStorage 限制
  const compressImage = async (base64: string, maxWidth: number = 1200): Promise<string> => {
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        let { width, height } = img
        if (width > maxWidth) {
          height = Math.floor(height * (maxWidth / width))
          width = maxWidth
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height)
          // 使用 JPEG 格式和较低质量以减小体积
          resolve(canvas.toDataURL('image/jpeg', 0.8))
        } else {
          resolve(base64)
        }
      }
      img.onerror = () => resolve(base64)
      img.src = base64
    })
  }

  // 将绿色 mask 合成到海报图片上
  const compositeImageWithMask = async (posterBase64: string): Promise<string> => {
    return new Promise((resolve) => {
      const posterImg = new Image()
      posterImg.onload = () => {
        // 创建输出画布，使用海报的原始尺寸
        const outputCanvas = document.createElement('canvas')
        outputCanvas.width = posterImg.width
        outputCanvas.height = posterImg.height
        const ctx = outputCanvas.getContext('2d')
        if (!ctx) {
          console.error('[合成] 无法获取 canvas context')
          resolve(posterBase64)
          return
        }

        // 1. 绘制原始海报
        ctx.drawImage(posterImg, 0, 0)
        console.log('[合成] 已绘制海报，尺寸:', posterImg.width, 'x', posterImg.height)

        // 2. 使用保存的可见画布快照（包含绿色 mask）
        if (visibleCanvasData) {
          console.log('[合成] 正在加载保存的画布快照...')
          const maskImg = new Image()
          maskImg.onload = () => {
            console.log('[合成] 画布快照尺寸:', maskImg.width, 'x', maskImg.height)
            // 将画布快照缩放并绘制到输出画布上
            ctx.drawImage(
              maskImg,
              0, 0, maskImg.width, maskImg.height,    // 源区域
              0, 0, posterImg.width, posterImg.height  // 目标区域（缩放至海报尺寸）
            )
            console.log('[合成] 已绘制绿色 mask')
            const result = outputCanvas.toDataURL('image/png')
            console.log('[合成] 合成完成，输出长度:', result.length)
            resolve(result)
          }
          maskImg.onerror = () => {
            console.error('[合成] 画布快照加载失败')
            resolve(outputCanvas.toDataURL('image/png'))
          }
          maskImg.src = visibleCanvasData
        } else {
          console.warn('[合成] 没有保存的画布快照，仅输出海报')
          resolve(outputCanvas.toDataURL('image/png'))
        }
      }
      posterImg.onerror = (e) => {
        console.error('[合成] 海报图片加载失败:', e)
        resolve(posterBase64)
      }
      posterImg.src = posterBase64
    })
  }

  // 分享图片
  const shareImage = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Joy IP 3D 生成的图片',
        text: '查看我生成的角色图片',
        url: window.location.href
      }).catch(err => console.log('分享失败:', err))
    } else {
      // 复制链接到剪贴板
      navigator.clipboard.writeText(window.location.href)
      alert('链接已复制到剪贴板')
    }
  }

  // 进入页面时，触发上传 tag_img（选中图片）以获取可复用的 URL
  useEffect(() => {
    const doUpload = async () => {
      try {
        if (!imageUrl) return
        const decoded = decodeURIComponent(imageUrl)
        const res = await fetch('/api/upload-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: decoded, customName: 'tag_img' }),
        })
        const data = await res.json()
        if (data?.success && data?.url) {
          setTagImgUrl(data.url)
        } else if (data?.url) {
          setTagImgUrl(data.url)
        }
      } catch (e) {
        console.warn('上传 tag_img 失败', e)
      }
    }
    doUpload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 允许通过 URL 参数直接展开背景输入框，绕过按钮点击问题
  useEffect(() => {
    try {
      const shouldShow = (searchParams.get('showbg') || '').toString() === '1'
      if (shouldShow) {
        setShowBgInput(true)
        console.debug('根据 URL 参数 showbg=1 自动展开背景输入框')
      }
    } catch { }
  }, [searchParams])

  const handleConfirmBackground = async (textOverride?: string) => {
    const finalText = (textOverride ?? bgText).trim()
    if (!finalText) return

    setIsGenerating(true)
    setErrorMessage('')
    setDebugInfo(null)

    try {
      const payload = { tagImgUrl: tagImgUrl || decodeURIComponent(imageUrl), backgroundText: finalText }
      console.log('发送请求payload:', payload)

      const [res1, res2] = await Promise.all([
        fetch('/api/run-jimeng4', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
        fetch('/api/run-banana', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
      ])

      console.log('API响应状态:', { jimeng4: res1.status, banana: res2.status })

      const d1 = await res1.json()
      const d2 = await res2.json()

      console.log('API响应数据:', { jimeng4: d1, banana: d2 })
      setDebugInfo({ jimeng4: d1, banana: d2 })

      // 从 stdout 中更稳健地提取各脚本各自生成的图片，避免并发写入目录导致的交叉抓取
      const extractGeneratedUrlsFromStdout = (stdout: string | undefined): string[] => {
        if (!stdout || typeof stdout !== 'string') return []
        const urls: string[] = []
        const rgx = /generated_images[\\/]+([^'"\s]+?\.(?:png|jpg|jpeg|webp|gif))/ig
        let m: RegExpExecArray | null
        while ((m = rgx.exec(stdout)) !== null) {
          const filename = m[1].replace(/\\/g, '/')
          urls.push(`/generated_images/${filename}`)
        }
        // 去重，保留顺序
        return Array.from(new Set(urls))
      }

      const jimeng4StdUrls = extractGeneratedUrlsFromStdout(d1?.stdout)
      const bananaStdUrls = extractGeneratedUrlsFromStdout(d2?.stdout)

      // 结合 stdout 与 resultImages，尽量拿到各自流程的唯一结果
      const pickFirst = (arr?: string[]) => (Array.isArray(arr) && arr.length > 0 ? arr[0] : '')
      let u1 = pickFirst(jimeng4StdUrls) || pickFirst(d1?.resultImages)
      let u2 = pickFirst(bananaStdUrls) || pickFirst(d2?.resultImages)

      // 若仍然相同，尝试从各自 newFiles 中挑不同的文件
      const normalizeLocal = (p: string) => {
        const m = /generated_images[\\/]+([^'"\s]+?\.(?:png|jpg|jpeg|webp|gif))/i.exec(p || '')
        return m ? `/generated_images/${m[1].replace(/\\/g, '/')}` : ''
      }
      if (u1 && u2 && decodeURIComponent(u1) === decodeURIComponent(u2)) {
        const d1New = Array.isArray(d1?.newFiles) ? d1.newFiles.map(normalizeLocal).filter(Boolean) : []
        const d2New = Array.isArray(d2?.newFiles) ? d2.newFiles.map(normalizeLocal).filter(Boolean) : []
        const alt1 = d1New.find((v: string) => decodeURIComponent(v) !== decodeURIComponent(u2))
        const alt2 = d2New.find((v: string) => decodeURIComponent(v) !== decodeURIComponent(u1))
        if (alt1) u1 = alt1
        if (alt2) u2 = alt2
      }

      const generatedImages: Array<{ url: string, source: string }> = []
      if (u1) generatedImages.push({ url: u1, source: 'Jimeng4' })
      if (u2 && (!u1 || decodeURIComponent(u2) !== decodeURIComponent(u1))) {
        generatedImages.push({ url: u2, source: 'Banana' })
      }

      if (generatedImages.length > 0) {
        setResultImages(generatedImages)
        setErrorMessage('')
        // 显示第一个生成结果；若存在原图缩略图，则索引为 1
        const hasOriginal = !!(imageUrl)
        setSelectedIndex(hasOriginal ? 1 : 0)

        // 将结果写入首页聊天流
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: finalText ? `已生成背景：${finalText}` : '已生成背景图片',
          images: generatedImages.map(g => g.url),
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, assistantMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
      } else {
        // 检查是否有错误信息
        const error1 = d1?.error || d1?.message || ''
        const error2 = d2?.error || d2?.message || ''
        const errorMsg = error1 || error2 || '生成失败，未返回图片URL'
        setErrorMessage(errorMsg)

        // 同步失败信息到首页聊天流
        const errorMessageToChat: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `背景生成失败：${errorMsg}`,
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, errorMessageToChat]
          persistState(updated, input, selectedPresets)
          return updated
        })
      }
    } catch (e) {
      console.error('生成流程失败', e)
      setErrorMessage(`网络请求失败: ${e instanceof Error ? e.message : '未知错误'}`)
      // 同步异常到首页聊天流
      const errorMessageToChat: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `背景生成失败：${e instanceof Error ? e.message : '未知错误'}`,
        timestamp: new Date(),
      }
      setMessages(prev => {
        const updated = [...prev, errorMessageToChat]
        persistState(updated, input, selectedPresets)
        return updated
      })
    } finally {
      setIsGenerating(false)
    }
  }

  // 优化形象：将文本作为 keyword，将当前页面图片作为 IMG1_PATH
  const handleOptimize = async () => {
    const keyword = optimizeText.trim()
    if (!keyword) return
    try {
      setIsGenerating(true)
      setErrorMessage('')
      setDebugInfo(null)

      const img = tagImgUrl || (imageUrl ? decodeURIComponent(imageUrl) : '')
      if (!img) {
        setIsGenerating(false)
        setErrorMessage('缺少参考图片')
        return
      }

      const res = await fetch('/api/run-banana-pro-img-jd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ img1Url: img, keyword })
      })
      const data = await res.json()
      setDebugInfo(data)

      const url: string = data?.url || ''
      if (url) {
        const out = [{ url, source: '优化形象' }]
        setResultImages(out)
        const hasOriginal = !!(imageUrl)
        setSelectedIndex(hasOriginal ? 1 : 0)

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `已优化形象：${keyword}`,
          images: out.map(g => g.url),
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, assistantMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
      } else {
        const errMsg = data?.error || '生成失败，未返回图片URL'
        setErrorMessage(errMsg)
        const errorMessageToChat: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `优化形象失败：${errMsg}`,
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, errorMessageToChat]
          persistState(updated, input, selectedPresets)
          return updated
        })
      }
    } catch (e) {
      setErrorMessage(`网络请求失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setIsGenerating(false)
    }
  }

  // 触发镜头角度变换，调用 /api/run-turn
  const handleTurn = async (actionLabel: string) => {
    try {
      setIsGenerating(true)
      setErrorMessage('')
      setDebugInfo(null)

      const img = tagImgUrl || (imageUrl ? decodeURIComponent(imageUrl) : '')
      if (!img) {
        setIsGenerating(false)
        setErrorMessage('缺少参考图片')
        return
      }
      const payload = { imageUrl: img, action: actionLabel }
      const res = await fetch('/api/run-turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()

      setDebugInfo(data)

      const urls: string[] = Array.isArray(data?.resultImages) ? data.resultImages : []
      const url: string = data?.processedImageUrl || (urls[0] || '')
      if (url || urls.length > 0) {
        const out: Array<{ url: string, source: string }> =
          (urls.length > 0 ? urls : [url]).map(u => ({ url: u, source: 'Turn' }))
        setResultImages(out)
        const hasOriginal = !!(imageUrl)
        setSelectedIndex(hasOriginal ? 1 : 0)

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `已生成角度：${actionLabel}`,
          images: out.map(g => g.url),
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, assistantMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
      } else {
        const errMsg = data?.error || '生成失败，未返回图片URL'
        setErrorMessage(errMsg)
        const errorMessageToChat: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `角度生成失败：${errMsg}`,
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, errorMessageToChat]
          persistState(updated, input, selectedPresets)
          return updated
        })
      }
    } catch (e) {
      setErrorMessage(`网络请求失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setIsGenerating(false)
    }
  }

  // 批量生成三个新视图：左转、右转、广角
  const handleTurnBatch = async () => {
    try {
      setIsGenerating(true)
      setErrorMessage('')
      setDebugInfo(null)

      const img = tagImgUrl || (imageUrl ? decodeURIComponent(imageUrl) : '')
      if (!img) {
        setIsGenerating(false)
        setErrorMessage('缺少参考图片')
        return
      }

      const actions = ['镜头左转45度', '镜头右转45度', '广角镜头']
      const allResults: Array<{ url: string, source: string }> = []

      for (const act of actions) {
        const payload = { imageUrl: img, action: act }
        const res = await fetch('/api/run-turn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        const data = await res.json()

        const urls: string[] = Array.isArray(data?.resultImages) ? data.resultImages : []
        const url: string = data?.processedImageUrl || (urls[0] || '')
        if (url || urls.length > 0) {
          const out: Array<{ url: string, source: string }> = (urls.length > 0 ? urls : [url]).map(u => ({ url: u, source: 'Turn' }))
          allResults.push(...out)
        }
      }

      if (allResults.length > 0) {
        setResultImages(allResults)
        const hasOriginal = !!(imageUrl)
        setSelectedIndex(hasOriginal ? 1 : 0)

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: '已生成角度合集',
          images: allResults.map(g => g.url),
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, assistantMessage]
          persistState(updated, input, selectedPresets)
          return updated
        })
      } else {
        const errMsg = '生成失败，未返回图片URL'
        setErrorMessage(errMsg)
        const errorMessageToChat: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `角度生成失败：${errMsg}`,
          timestamp: new Date(),
        }
        setMessages(prev => {
          const updated = [...prev, errorMessageToChat]
          persistState(updated, input, selectedPresets)
          return updated
        })
      }
    } catch (e) {
      setErrorMessage(`网络请求失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setIsGenerating(false)
    }
  }

  // 放大
  const zoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 3))
  }

  // 缩小
  const zoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.5))
  }

  // 从首页批次中加载与选中图片同批次的所有图片，并定位当前索引
  useEffect(() => {
    try {
      const decoded = imageUrl ? decodeURIComponent(imageUrl) : ''
      if (!decoded) return
      // 已有生成结果则不覆盖（例如在详情页内触发生成）
      if (resultImages && resultImages.length > 0) return
      const msgWithImage = messages.find(m => Array.isArray(m.images) && m.images.some(u => decodeURIComponent(u) === decoded))
      if (msgWithImage && Array.isArray(msgWithImage.images) && msgWithImage.images.length > 0) {
        const imgs = msgWithImage.images
        setResultImages(imgs.map(u => ({ url: u, source: 'Batch' })))
        const idx = imgs.findIndex(u => decodeURIComponent(u) === decoded)
        setSelectedIndex(idx >= 0 ? idx : 0)
      }
    } catch { }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl, messages])

  // 离开详情页时，保存窗口滚动位置到 sessionStorage（增强回退体验）
  useEffect(() => {
    return () => {
      try {
        saveScrollPos(getRouteKey(), (typeof window !== 'undefined' ? (window.scrollY || 0) : 0))
      } catch { }
    }
  }, [])

  // 初始化画布尺寸（当海报图片加载后）
  useEffect(() => {
    if (!posterImage) return

    const img = new Image()
    img.onload = () => {
      // 保存原始尺寸
      setPosterDimensions({ width: img.width, height: img.height })

      const canvas = posterCanvasRef.current
      const maskCanvas = maskCanvasRef.current
      if (canvas && maskCanvas) {
        // 计算显示尺寸（保持宽高比，最大 800x600）
        const maxW = 800
        const maxH = 600
        let displayW = img.width
        let displayH = img.height

        // 按比例缩放到容器内
        if (displayW > maxW || displayH > maxH) {
          const scaleW = maxW / displayW
          const scaleH = maxH / displayH
          const scale = Math.min(scaleW, scaleH)
          displayW = Math.floor(displayW * scale)
          displayH = Math.floor(displayH * scale)
        }

        // 保存显示尺寸
        setCanvasDisplaySize({ width: displayW, height: displayH })

        // 设置 canvas 实际尺寸（与显示尺寸一致）
        canvas.width = displayW
        canvas.height = displayH
        maskCanvas.width = displayW
        maskCanvas.height = displayH

        // 初始化 mask 画布为黑色
        const maskCtx = maskCanvas.getContext('2d')
        if (maskCtx) {
          maskCtx.fillStyle = 'black'
          maskCtx.fillRect(0, 0, displayW, displayH)
        }
      }
    }
    img.src = posterImage
  }, [posterImage])

  return (
    <div className="flex flex-col h-screen bg-[#1E202C] overflow-hidden">
      {/* 头部工具栏 */}
      <div className="flex items-center justify-between p-4 text-white">
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-black/30 transition-colors"
          onClick={() => {
            // 简化返回逻辑：不再携带任何 URL 参数
            router.push('/', { scroll: false })
          }}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回
        </Button>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="text-white hover:bg:black/30 transition-colors" onClick={zoomOut}>
            <ZoomOut className="w-4 h-4" />
          </Button>
          <span className="text-sm text-white/70 min-w-[60px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <Button variant="ghost" size="sm" className="text-white hover:bg-black/30 transition-colors" onClick={zoomIn}>
            <ZoomIn className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-white hover:bg-black/30 transition-colors"
            onClick={() => setLiked(!liked)}
          >
            <Heart className={`w-4 h-4 ${liked ? 'fill-red-500 text-red-500' : ''}`} />
          </Button>
          <Button variant="ghost" size="sm" className="text-white hover:bg-black/30 transition-colors" onClick={shareImage}>
            <Share2 className="w-4 h-4 mr-2" />
            分享
          </Button>
          <Button size="sm" className="text-white hover:bg-black/30 transition-colors" onClick={downloadImage}>
            <Download className="w-4 h-4 mr-2" />
            下载
          </Button>
        </div>
      </div>

      {/* 主内容区：顶部按钮 + 中间大图 + 右侧缩略图 */}
      <div className="flex-1 flex min-h-0">
        {/* 中间画面区 */}
        <div className="flex-1 bg-transparent overflow-auto no-scrollbar">
          {/* 顶部操作按钮 */}
          <div className="flex items-center justify-center gap-3 p-4">
            <Button
              variant="ghost"
              className="rounded px-3 py-2 bg-white/10 text-white hover:bg-white/20 transition-colors duration-200"
              onClick={() => { setShowOptimizeDialog(v => !v); setShowApplyDialog(false); setShowAngleDialog(false) }}
            >
              优化形象
            </Button>
            <Button
              variant="ghost"
              className="rounded px-3 py-2 bg-white/10 text-white hover:bg-white/20 transition-colors duration-200"
              onClick={() => { setShowApplyDialog(v => !v); setShowOptimizeDialog(false); setShowAngleDialog(false) }}
            >
              添加背景
            </Button>
            <Button
              variant="ghost"
              className={`rounded px-3 py-2 ${showMergeMode ? 'bg-green-600 text-white' : 'bg-white/10 text-white'} hover:bg-white/20 transition-colors duration-200`}
              onClick={() => {
                setShowMergeMode(v => !v)
                setShowOptimizeDialog(false)
                setShowApplyDialog(false)
                setShowAngleDialog(false)
                if (!showMergeMode) {
                  setPosterImage(null)
                  setMaskData(null)
                  setMergePrompt('')
                  setDrawHistory([])
                  setVisibleCanvasData(null)  // 清除画布快照
                }
              }}
            >
              合并生成
            </Button>
            {/* 变换角度按钮隐藏 */}
          </div>

          {/* 弹窗：优化形象（仅样式） */}
          {showOptimizeDialog && (
            <div className="mx-auto w-full max-w-[915px] rounded-[30px] border border-white/15 bg-[#202126] text-white shadow-[0_8px_24px_rgba(0,0,0,0.35)] animate-soft-bounce">
              {/* 头部标题与副标题（对齐 ChatInput 风格） */}
              <div className="px-6 pt-5 pb-2 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-clip-text text-transparent bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-[20px] font-bold leading-[24px]">优化形象</div>
                  <div className="text-[14px] leading-[20px] text-[#8b8fa3]">描述你想要的优化</div>
                </div>
                <button className="text-white/70 hover:text-white" onClick={() => setShowOptimizeDialog(false)}>×</button>
              </div>
              {/* 上行：输入框独占一行（去边框、深色底） */}
              <div className="px-6 pb-2 mb-2">
                <div className="flex items-center">
                  <div className="flex-1">
                    <Input
                      className="h-[50px] pr-10 bg-[#2b2d33] text-white border-0 placeholder:text-[#8b8fa3] rounded-[12px] focus:ring-2 focus:ring-primary"
                      placeholder="请输入背景描述..."
                      value={optimizeText}
                      onChange={e => setOptimizeText(e.target.value)}
                    />
                  </div>
                  <div className="ml-3">
                    <Button
                      disabled={isGenerating}
                      className="h-[40px] px-4 rounded-[10px] bg-[#3b69ff] text-white border-0 hover:bg-[#315be6]"
                      onClick={async () => {
                        await handleOptimize()
                        setShowOptimizeDialog(false)
                      }}
                    >
                      {isGenerating ? '生成中...' : '发送'}
                    </Button>
                  </div>
                </div>
              </div>
              {/* 下行：预设按钮（配色与圆角对齐 ChatInput） */}
              <div className="px-6 pb-5">
                {/* <div className="flex items-center gap-2"> */}
                {/* <Button size="sm" variant="outline" className="h-[40px] px-4 rounded-[10px] bg-[#424158] text-[#b7affe] border-0 hover:bg-[#4a4964]">
                    <img src="/icons/head.svg" alt="" className="w-6 h-6 mr-2" />
                    表情
                  </Button>
                  <Button size="sm" variant="outline" className="h-[40px] px-4 rounded-[10px] bg-[#424158] text-[#b7affe] border-0 hover:bg-[#4a4964]">
                    <img src="/icons/body.svg" alt="" className="w-6 h-6 mr-2" />
                    动作
                  </Button> */}
                {/* </div> */}
              </div>
            </div>
          )}

          {/* 弹窗：应用生图（复用背景生成逻辑） */}
          {showApplyDialog && (
            <div className="mx-auto w-full max-w-[915px] rounded-[30px] border border-white/15 bg-[#202126] text-white shadow-[0_8px_24px_rgba(0,0,0,0.35)] animate-soft-bounce">
              <div className="px-6 pt-5 pb-2 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="bg-clip-text text-transparent bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-[20px] font-bold leading-[24px]">添加背景</div>
                  <div className="text-[14px] leading-[20px] text-[#8b8fa3]">基于当前JOY，描述你想要的图</div>
                </div>
                <button className="text-white/70 hover:text-white" onClick={() => setShowApplyDialog(false)}>×</button>
              </div>
              <div className="px-6 pb-2 mb-2">
                <div className="flex items-center">
                  <div className="flex-1">
                    <Input
                      className="h-[50px] pr-10 bg-[#2b2d33] text-white border-0 placeholder:text-[#8b8fa3] rounded-[12px] focus:ring-2 focus:ring-primary"
                      placeholder="请输入画面描述..."
                      value={applyText}
                      onChange={e => setApplyText(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <div className="px-6 pb-5">
                <div className="flex items-center">
                  <div className="ml-auto">
                    <Button
                      disabled={isGenerating}
                      className="h-[40px] px-4 rounded-[10px] bg-[#3b69ff] text-white border-0 hover:bg-[#315be6]"
                      onClick={async () => {
                        const txt = applyText.trim()
                        if (!txt) return
                        setShowApplyDialog(false)
                        await handleConfirmBackground(txt)
                      }}
                    >
                      {isGenerating ? '生成中...' : '应用'}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 弹窗：变换角度（样式与应用生图一致） */}
          {showAngleDialog && (
            <div className="mx-auto w-[560px] rounded-xl bg-[#1f1f1f] text-white p-4 shadow-lg animate-soft-bounce">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold">变换角度</h3>
                <button className="text-white/70 hover:text-white" onClick={() => setShowAngleDialog(false)}>×</button>
              </div>
              <p className="text-xs text-white/70 mt-1">基于大模型生成“左转30度、右转30度、放大背景”三个新视图</p>
              <div className="grid grid-cols-2 gap-2 mt-3">
                <Button
                  size="sm"
                  className="w-full bg-gray-700 text-white border border-gray-600 hover:bg-white hover:text-black hover:border-white transition-colors"
                  disabled={isGenerating}
                  onClick={handleTurnBatch}
                >
                  {isGenerating ? '生成中...' : '生成'}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full bg-gray-700 text-white border border-gray-600 hover:bg-white hover:text-black hover:border-white transition-colors"
                  onClick={() => setShowAngleDialog(false)}
                >
                  取消
                </Button>
              </div>
            </div>
          )}

          <div className="min-h-full p-4">
            {isGenerating || isMerging ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-[300px] h-[300px] flex items-center justify-center rounded-lg bg-muted animate-pulse">
                  <span className="text-muted-foreground">{isMerging ? '合并生成中...' : '生成中...'}</span>
                </div>
              </div>
            ) : showMergeMode ? (
              /* 合并模式：两列布局 */
              <div className="flex flex-col gap-4">
                <div className="grid grid-cols-3 gap-4">
                  {/* 左侧 2/3：海报上传 + Mask 画布 */}
                  <div className="col-span-2 flex flex-col items-center gap-4">
                    {!posterImage ? (
                      <label className="w-full h-[400px] border-2 border-dashed border-white/30 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-white/50 transition-colors">
                        <Upload className="w-12 h-12 text-white/50 mb-4" />
                        <span className="text-white/70">点击上传海报图</span>
                        <input
                          type="file"
                          className="hidden"
                          accept="image/*"
                          onChange={async (e) => {
                            const file = e.target.files?.[0]
                            if (file) {
                              const reader = new FileReader()
                              reader.onload = (ev) => {
                                setPosterImage(ev.target?.result as string)
                                setDrawHistory([])
                                setMaskData(null)
                                setVisibleCanvasData(null)  // 清除旧的画布快照
                              }
                              reader.readAsDataURL(file)
                            }
                          }}
                        />
                      </label>
                    ) : (
                      <div className="relative w-full">
                        <div
                          className="relative border border-white/20 rounded-xl overflow-hidden bg-black mx-auto"
                          style={{
                            width: canvasDisplaySize ? `${canvasDisplaySize.width}px` : 'auto',
                            height: canvasDisplaySize ? `${canvasDisplaySize.height}px` : '400px',
                            maxWidth: '100%'
                          }}
                        >
                          {/* 海报图片 */}
                          <img
                            src={posterImage}
                            alt="海报"
                            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                          />
                          {/* 绘图画布 */}
                          <canvas
                            ref={posterCanvasRef}
                            className="absolute inset-0 w-full h-full cursor-crosshair"
                            style={{ touchAction: 'none' }}
                            onMouseDown={(e) => {
                              const canvas = posterCanvasRef.current
                              const maskCanvas = maskCanvasRef.current
                              if (!canvas || !maskCanvas) return

                              const ctx = canvas.getContext('2d')
                              const maskCtx = maskCanvas.getContext('2d')
                              if (!ctx || !maskCtx) return

                              // 保存当前状态用于回退
                              const currentState = ctx.getImageData(0, 0, canvas.width, canvas.height)
                              setDrawHistory(prev => [...prev, currentState])

                              const rect = canvas.getBoundingClientRect()
                              const scaleX = canvas.width / rect.width
                              const scaleY = canvas.height / rect.height
                              const x = (e.clientX - rect.left) * scaleX
                              const y = (e.clientY - rect.top) * scaleY

                              ctx.strokeStyle = 'rgba(0, 255, 0, 0.5)'
                              ctx.lineWidth = brushSize
                              ctx.lineCap = 'round'
                              ctx.lineJoin = 'round'
                              ctx.beginPath()
                              ctx.moveTo(x, y)

                              maskCtx.strokeStyle = 'white'
                              maskCtx.lineWidth = brushSize
                              maskCtx.lineCap = 'round'
                              maskCtx.lineJoin = 'round'
                              maskCtx.beginPath()
                              maskCtx.moveTo(x, y)

                              setIsDrawing(true)

                              // 自动填充 Prompt（仅用户可见部分）
                              if (!mergePrompt) {
                                setMergePrompt(MERGE_USER_PROMPT)
                              }
                            }}
                            onMouseMove={(e) => {
                              if (!isDrawing) return
                              const canvas = posterCanvasRef.current
                              const maskCanvas = maskCanvasRef.current
                              if (!canvas || !maskCanvas) return

                              const ctx = canvas.getContext('2d')
                              const maskCtx = maskCanvas.getContext('2d')
                              if (!ctx || !maskCtx) return

                              const rect = canvas.getBoundingClientRect()
                              const scaleX = canvas.width / rect.width
                              const scaleY = canvas.height / rect.height
                              const x = (e.clientX - rect.left) * scaleX
                              const y = (e.clientY - rect.top) * scaleY

                              ctx.lineTo(x, y)
                              ctx.stroke()

                              maskCtx.lineTo(x, y)
                              maskCtx.stroke()
                            }}
                            onMouseUp={() => {
                              setIsDrawing(false)
                              const canvas = posterCanvasRef.current
                              const maskCanvas = maskCanvasRef.current
                              if (maskCanvas) {
                                setMaskData(maskCanvas.toDataURL('image/png'))
                              }
                              // 同时保存可见画布快照（包含绿色 mask）
                              if (canvas) {
                                setVisibleCanvasData(canvas.toDataURL('image/png'))
                                console.log('[绘制] 已保存可见画布快照')
                              }
                            }}
                            onMouseLeave={() => {
                              if (isDrawing) {
                                setIsDrawing(false)
                                const canvas = posterCanvasRef.current
                                const maskCanvas = maskCanvasRef.current
                                if (maskCanvas) {
                                  setMaskData(maskCanvas.toDataURL('image/png'))
                                }
                                // 同时保存可见画布快照
                                if (canvas) {
                                  setVisibleCanvasData(canvas.toDataURL('image/png'))
                                  console.log('[绘制] 已保存可见画布快照 (离开)')
                                }
                              }
                            }}
                          />
                          {/* 隐藏的 Mask 画布 */}
                          <canvas ref={maskCanvasRef} className="hidden" />
                        </div>
                        {/* 删除按钮 */}
                        <button
                          className="absolute top-2 right-2 p-2 bg-red-500/80 hover:bg-red-500 text-white rounded-full"
                          onClick={() => {
                            setPosterImage(null)
                            setMaskData(null)
                            setVisibleCanvasData(null)  // 清除画布快照
                            setDrawHistory([])
                          }}
                        >
                          ×
                        </button>
                      </div>
                    )}
                  </div>

                  {/* 右侧 1/3：JoyIP 图片 */}
                  <div className="col-span-1 flex flex-col items-center gap-2">
                    <span className="text-xs text-white/50">JoyIP 角色（图2）</span>
                    {imageUrl && (
                      <img
                        src={decodeURIComponent(imageUrl)}
                        alt="JoyIP"
                        className="rounded-lg shadow-lg max-w-full max-h-[380px] object-contain border border-white/20"
                      />
                    )}
                  </div>
                </div>

                {/* 底部工具栏 */}
                <div className="flex items-center justify-center gap-4 mt-4">
                  <Button
                    variant="ghost"
                    className={`rounded px-4 py-2 ${showBrushTools ? 'bg-green-600 text-white' : 'bg-white/10 text-white'} hover:bg-white/20 transition-colors`}
                    onClick={() => setShowBrushTools(v => !v)}
                  >
                    <Brush className="w-4 h-4 mr-2" />
                    mask画笔
                  </Button>
                  <Button
                    variant="ghost"
                    className="rounded px-4 py-2 bg-white/10 text-white hover:bg-white/20 transition-colors"
                    disabled={drawHistory.length === 0}
                    onClick={() => {
                      const canvas = posterCanvasRef.current
                      if (!canvas || drawHistory.length === 0) return
                      const ctx = canvas.getContext('2d')
                      if (!ctx) return
                      const prevState = drawHistory[drawHistory.length - 1]
                      ctx.putImageData(prevState, 0, 0)
                      setDrawHistory(prev => prev.slice(0, -1))
                    }}
                  >
                    <Undo2 className="w-4 h-4 mr-2" />
                    回退
                  </Button>
                  <Button
                    variant="ghost"
                    className="rounded px-4 py-2 bg-green-600 text-white hover:bg-green-500 transition-colors"
                    disabled={!posterImage || !maskData || isMerging}
                    onClick={async () => {
                      if (!posterImage || !maskData || !imageUrl) return
                      setIsMerging(true)
                      try {
                        const apiUrl = 'https://modelservice.jdcloud.com/v1/images/gemini_flash/generations'
                        const apiKey = 'pk-a3b4d157-e765-45b9-988a-b8b2a6d7c8bf'

                        // 构建请求
                        const extractBase64 = (dataUrl: string) => dataUrl.startsWith('data:') ? dataUrl.split(',')[1] : dataUrl
                        const getMimeType = (dataUrl: string) => {
                          const match = dataUrl.match(/data:([^;]+);/)
                          return match ? match[1] : 'image/png'
                        }

                        // 组合 prompt，添加尺寸要求
                        const dimensionHint = posterDimensions
                          ? `输出图像尺寸应为${posterDimensions.width}x${posterDimensions.height}像素。`
                          : '';
                        // 只使用 MERGE_SYSTEM_PROMPT
                        const finalPrompt = `${dimensionHint}${MERGE_SYSTEM_PROMPT}`

                        // 1. 将绿色 mask 合成到海报图片上
                        const compositedPoster = await compositeImageWithMask(posterImage)

                        // 2. 将合成后的图片保存到服务器
                        console.log('[合并生成] 正在保存合成图片到服务器...')
                        const saveResponse = await fetch('/api/save-render', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ dataURL: compositedPoster })
                        })

                        if (!saveResponse.ok) {
                          throw new Error('保存合成图片失败')
                        }

                        const saveResult = await saveResponse.json()
                        const compositedImageUrl = saveResult.url // 例如: /output/render_20260108_153000.png
                        console.log('[合并生成] 合成图片已保存:', compositedImageUrl)

                        // 3. 重新从服务器读取合成图片
                        const compositedImageResponse = await fetch(compositedImageUrl)
                        const compositedImageBlob = await compositedImageResponse.blob()
                        const compositedImageBase64 = await new Promise<string>((resolve) => {
                          const reader = new FileReader()
                          reader.onload = () => resolve(reader.result as string)
                          reader.readAsDataURL(compositedImageBlob)
                        })
                        console.log('[合并生成] 已重新读取合成图片，长度:', compositedImageBase64.length)

                        const parts = [
                          { inline_data: { mime_type: 'image/png', data: extractBase64(compositedImageBase64) } },
                          { inline_data: { mime_type: 'image/png', data: extractBase64(decodeURIComponent(imageUrl).startsWith('data:') ? decodeURIComponent(imageUrl) : await fetch(decodeURIComponent(imageUrl)).then(r => r.blob()).then(b => new Promise<string>((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result as string); reader.readAsDataURL(b) }))) } },
                          { text: finalPrompt }
                        ]

                        const response = await fetch(apiUrl, {
                          method: 'POST',
                          headers: {
                            'Authorization': `Bearer ${apiKey}`,
                            'Content-Type': 'application/json'
                          },
                          body: JSON.stringify({
                            model: 'Gemini 3-Pro-Image-Preview',
                            contents: { role: 'USER', parts },
                            generation_config: {
                              response_modalities: ['TEXT', 'IMAGE']
                            },
                            stream: false
                          })
                        })

                        const data = await response.json()
                        let resultUrl = ''
                        if (data.candidates?.[0]?.content?.parts) {
                          const imagePart = data.candidates[0].content.parts.find((p: any) => p.inline_data || p.inlineData)
                          if (imagePart) {
                            const inline = imagePart.inline_data || imagePart.inlineData
                            resultUrl = `data:image/png;base64,${inline.data}`
                          }
                        }

                        if (resultUrl) {
                          setResultImages(prev => [...prev, { url: resultUrl, source: '合并生成' }])

                          // 保存生成结果到 output 文件夹
                          console.log('[合并生成] 正在保存结果图片到服务器...')
                          const saveResultResponse = await fetch('/api/save-render', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ dataURL: resultUrl })
                          })
                          if (saveResultResponse.ok) {
                            const saveResultData = await saveResultResponse.json()
                            console.log('[合并生成] 结果图片已保存:', saveResultData.url)
                          }

                          // 自动切换到生成结果图
                          setCurrentImage(resultUrl)

                          // 压缩后保存到主页聊天流
                          const compressedUrl = await compressImage(resultUrl)
                          const assistantMessage: Message = {
                            id: (Date.now() + 1).toString(),
                            type: 'assistant',
                            content: `已完成海报合并生成`,
                            images: [compressedUrl],
                            timestamp: new Date(),
                          }
                          setMessages(prev => {
                            const updated = [...prev, assistantMessage]
                            try {
                              persistState(updated, input, selectedPresets)
                            } catch (e) {
                              console.warn('持久化失败，图片可能过大:', e)
                            }
                            return updated
                          })

                          setShowMergeMode(false)
                          setPosterImage(null)
                          setMaskData(null)
                          setDrawHistory([])
                          setPosterDimensions(null)
                          setVisibleCanvasData(null)  // 清除画布快照
                        } else {
                          setErrorMessage('合并生成失败，未返回图片')
                        }
                      } catch (e: any) {
                        setErrorMessage(`合并生成失败: ${e.message}`)
                      } finally {
                        setIsMerging(false)
                      }
                    }}
                  >
                    <Check className="w-4 h-4 mr-2" />
                    确认
                  </Button>
                </div>

                {/* 画笔工具面板 */}
                {showBrushTools && (
                  <div className="mx-auto w-full max-w-[600px] rounded-xl border border-white/15 bg-[#202126] p-4 mt-4">
                    <div className="flex items-center gap-4">
                      <span className="text-white/70 text-sm">提示词：</span>
                      <Input
                        className="flex-1 h-[40px] bg-[#2b2d33] text-white border-0 placeholder:text-[#8b8fa3] rounded-lg"
                        placeholder={MERGE_USER_PROMPT}
                        value={mergePrompt}
                        onChange={e => setMergePrompt(e.target.value)}
                      />
                    </div>
                    <div className="flex items-center gap-4 mt-4">
                      <span className="text-white/70 text-sm">笔刷大小：</span>
                      <input
                        type="range"
                        min={20}
                        max={100}
                        value={brushSize}
                        onChange={e => setBrushSize(Number(e.target.value))}
                        className="flex-1"
                      />
                      <span className="text-white text-sm min-w-[50px]">{brushSize}px</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4" style={{ transform: `scale(${scale})`, transformOrigin: 'top center', transition: 'transform 0.3s ease' }}>
                {/* 中间放大呈现图片：当同时存在 Jimeng4 与 Banana 的两张生成结果时并排展示 */}
                <div className="text-center ">
                  {(() => {
                    const decodedOriginal = imageUrl ? decodeURIComponent(imageUrl) : ''
                    const hasOriginalInResults = resultImages.some(it => decodeURIComponent(it.url) === decodedOriginal)
                    const displayList = [
                      ...(!hasOriginalInResults && decodedOriginal ? [{ url: imageUrl, source: '原图' }] : []),
                      ...resultImages,
                    ]

                    const jimeng4 = resultImages.find(r => r.source === 'Jimeng4')
                    const banana = resultImages.find(r => r.source === 'Banana')
                    const hasDual = !!jimeng4 && !!banana

                    if (hasDual) {
                      return (
                        <div className="flex items-start justify-center gap-4">
                          <div className="flex flex-col items-center">
                            <img
                              src={decodeURIComponent(jimeng4!.url)}
                              alt="Jimeng4 生成结果"
                              className="rounded-lg shadow-2xl mx-auto max-w-[40vw] max-h-[65vh] object-contain"
                            />
                            <span className="mt-2 text-xs text-white/70">Jimeng4</span>
                          </div>
                          <div className="flex flex-col items-center">
                            <img
                              src={decodeURIComponent(banana!.url)}
                              alt="Banana 生成结果"
                              className="rounded-lg shadow-2xl mx-auto max-w-[40vw] max-h-[65vh] object-contain"
                            />
                            <span className="mt-2 text-xs text-white/70">Banana</span>
                          </div>
                        </div>
                      )
                    }

                    if (displayList.length > 0) {
                      const current = displayList[selectedIndex] || displayList[0]
                      return (
                        <img src={decodeURIComponent(current.url)} alt="选中图片" className="rounded-lg shadow-2xl mx-auto max-w-[60vw] max-h-[65vh] object-contain" />
                      )
                    }
                    if (decodedOriginal) {
                      return (
                        <img src={decodedOriginal} alt="原始图片" className="rounded-lg shadow-2xl mx-auto max-w-[60vw] max-h-[65vh] object-contain" />
                      )
                    }
                    return (
                      <div className="flex items-center justify-center h-64 bg-transparent rounded-lg">
                        <span className="text-muted-foreground">暂无图片</span>
                      </div>
                    )
                  })()}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 右侧缩略图预览栏 */}
        <div className="w-64 bg-[#1E202C] h-full flex flex-col min-h-0">
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-3">
              {(() => {
                const decodedOriginal = imageUrl ? decodeURIComponent(imageUrl) : ''
                const hasOriginalInResults = resultImages.some(it => decodeURIComponent(it.url) === decodedOriginal)
                const thumbs = [
                  ...(!hasOriginalInResults && decodedOriginal ? [{ url: imageUrl, source: '原图' }] : []),
                  ...resultImages,
                ]
                return thumbs.map((item, idx) => (
                  <div key={idx} className={`rounded-md overflow-hidden cursor-pointer border ${selectedIndex === idx ? 'border-primary' : 'border-transparent'}`} onClick={() => setSelectedIndex(idx)}>
                    <img src={decodeURIComponent(item.url)} alt={`预览-${idx}`} className="w-full h-auto object-contain" />
                  </div>
                ))
              })()}

              {/* 下载按钮 */}
              {resultImages.length > 0 && (
                <Button className="w-full" variant="outline" onClick={() => {
                  const decodedOriginal = imageUrl ? decodeURIComponent(imageUrl) : ''
                  const hasOriginalInResults = resultImages.some(it => decodeURIComponent(it.url) === decodedOriginal)
                  const thumbs = [
                    ...(!hasOriginalInResults && decodedOriginal ? [{ url: imageUrl, source: '原图' }] : []),
                    ...resultImages,
                  ]
                  const current = thumbs[selectedIndex] || thumbs[0]
                  if (current?.source === '原图') {
                    // 原图下载
                    downloadImage()
                  } else {
                    downloadGeneratedImage(current.url, current.source || 'result')
                  }
                }}>
                  <Download className="w-4 h-4 mr-2" />
                  下载选中图片
                </Button>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  )
}

