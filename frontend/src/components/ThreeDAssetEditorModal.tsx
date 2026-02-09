"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import { X } from 'lucide-react'

type AssetItem = { name: string; url: string }

type ThreeDAssetEditorModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onUse: (payload: { previewUrl: string; baseImageUrl: string }) => void
}

const ACTION_OPTIONS = [
  { label: '站立', value: 'stand' },
  { label: '动感', value: 'happy' },
  { label: '跳跃', value: 'jump' },
  { label: '跑步', value: 'run' },
  { label: '坐姿', value: 'sit' },
] as const

export default function ThreeDAssetEditorModal({
  open,
  onOpenChange,
  onUse,
}: ThreeDAssetEditorModalProps) {
  const [headAssets, setHeadAssets] = useState<AssetItem[]>([])
  const [bodyAssets, setBodyAssets] = useState<AssetItem[]>([])
  const [selectedHeadUrl, setSelectedHeadUrl] = useState<string | null>(null)
  const [selectedAction, setSelectedAction] = useState<string | null>(null)
  const [selectedBodyUrl, setSelectedBodyUrl] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [baseImageUrl, setBaseImageUrl] = useState<string | null>(null)
  const [isLoadingHead, setIsLoadingHead] = useState(false)
  const [isLoadingBody, setIsLoadingBody] = useState(false)
  const [isComposing, setIsComposing] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  const headGridRef = useRef<HTMLDivElement>(null)
  const bodyGridRef = useRef<HTMLDivElement>(null)
  const isComposingRef = useRef(false)
  const lastAutoComposeKeyRef = useRef<string | null>(null)

  const canCompose = Boolean(selectedHeadUrl && selectedBodyUrl && !isComposing)

  const resetAll = () => {
    setSelectedHeadUrl(null)
    setSelectedAction(ACTION_OPTIONS[0].value)
    setSelectedBodyUrl(null)
    setPreviewUrl(null)
    setBaseImageUrl(null)
    setBodyAssets([])
    setErrorText(null)
    isComposingRef.current = false
    lastAutoComposeKeyRef.current = null
  }

  const sortedHeadAssets = useMemo(() => {
    return [...headAssets].sort((a, b) => a.name.localeCompare(b.name))
  }, [headAssets])

  const sortedBodyAssets = useMemo(() => {
    return [...bodyAssets].sort((a, b) => a.name.localeCompare(b.name))
  }, [bodyAssets])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onOpenChange])

  // 获取表情素材
  useEffect(() => {
    if (!open) return
    resetAll()
    setHeadAssets([])
    setIsLoadingHead(true)

    const controller = new AbortController()
    ;(async () => {
      try {
        const res = await axios.get('/api/3d_assets', {
          params: { type: 'head' },
          signal: controller.signal,
          timeout: 0,
        })
        if (!res.data?.success) throw new Error(res.data?.error || '获取表情素材失败')
        setHeadAssets(Array.isArray(res.data.items) ? res.data.items : [])
      } catch (e: any) {
        if (e?.name === 'CanceledError') return
        setErrorText(e?.message || '获取表情素材失败')
      } finally {
        setIsLoadingHead(false)
      }
    })()

    return () => controller.abort()
  }, [open])

  // 获取身体素材
  useEffect(() => {
    if (!open) return
    if (!selectedAction) {
      setBodyAssets([])
      setSelectedBodyUrl(null)
      return
    }

    setBodyAssets([])
    setSelectedBodyUrl(null)
    setIsLoadingBody(true)
    setErrorText(null)

    const controller = new AbortController()
    ;(async () => {
      try {
        const res = await axios.get('/api/3d_assets', {
          params: { type: 'body', action: selectedAction },
          signal: controller.signal,
          timeout: 0,
        })
        if (!res.data?.success) throw new Error(res.data?.error || '获取动作素材失败')
        setBodyAssets(Array.isArray(res.data.items) ? res.data.items : [])
      } catch (e: any) {
        if (e?.name === 'CanceledError') return
        setErrorText(e?.message || '获取动作素材失败')
      } finally {
        setIsLoadingBody(false)
      }
    })()

    return () => controller.abort()
  }, [open, selectedAction])

  const handleCompose = useCallback(async () => {
    if (!selectedHeadUrl || !selectedBodyUrl) return
    if (isComposingRef.current) return
    isComposingRef.current = true
    setIsComposing(true)
    setErrorText(null)
    setPreviewUrl(null)
    setBaseImageUrl(null)
    try {
      const res = await axios.post(
        '/api/3d_editor/compose',
        { head_url: selectedHeadUrl, body_url: selectedBodyUrl, action_type: selectedAction },
        { timeout: 0 }
      )
      if (!res.data?.success) throw new Error(res.data?.error || '拼装失败')
      const nextPreviewUrl = res.data?.preview_url || res.data?.previewUrl || res.data?.url
      const nextBaseImageUrl = res.data?.base_image_url || res.data?.baseImageUrl || res.data?.url
      if (!nextPreviewUrl || !nextBaseImageUrl) throw new Error(res.data?.error || '拼装失败')
      setPreviewUrl(String(nextPreviewUrl))
      setBaseImageUrl(String(nextBaseImageUrl))
    } catch (e: any) {
      setErrorText(e?.message || '拼装失败')
    } finally {
      setIsComposing(false)
      isComposingRef.current = false
    }
  }, [selectedHeadUrl, selectedBodyUrl, selectedAction])

  // 自动拼装逻辑
  useEffect(() => {
    if (!selectedHeadUrl || !selectedBodyUrl) return
    const nextKey = `${selectedHeadUrl}|${selectedBodyUrl}|${selectedAction ?? ''}`
    if (lastAutoComposeKeyRef.current === nextKey) return
    if (isComposingRef.current) return
    lastAutoComposeKeyRef.current = nextKey
    handleCompose()
  }, [selectedHeadUrl, selectedBodyUrl, selectedAction, handleCompose])

  const handleDownload = () => {
    if (!previewUrl) return
    const link = document.createElement('a')
    link.href = previewUrl
    link.download = `joy_3d_${Date.now()}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm font-sans"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-[#16171d] rounded-[40px] overflow-hidden shadow-2xl flex flex-col w-[1200px] h-[850px] max-w-[95vw] max-h-[95vh] border border-white/5"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-10 py-8">
          <div className="text-[32px] font-bold text-white tracking-tight">JOY 3D 素材拼模</div>
          <button
            onClick={() => onOpenChange(false)}
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10 transition-all"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 min-h-0 flex px-10 pb-10 gap-10">
          {/* Left Panel: Selectors */}
          <div className="w-[480px] flex flex-col gap-8">
            {/* Expression Section */}
            <div className="flex flex-col gap-4">
              <div className="text-base text-gray-400 font-bold ml-1">表情</div>
              <div
                ref={headGridRef}
                className="bg-[#1a1c22]/80 rounded-[24px] p-5 h-[280px] overflow-y-auto custom-scrollbar border border-white/5"
              >
                {isLoadingHead ? (
                  <div className="flex items-center justify-center h-full text-gray-500 text-sm italic">加载素材中...</div>
                ) : (
                  <div className="grid grid-cols-4 gap-4">
                    {sortedHeadAssets.map((item) => (
                      <button
                        key={item.url}
                        className={`aspect-square rounded-[16px] overflow-hidden bg-black border-2 transition-all ${
                          selectedHeadUrl === item.url ? 'border-[#b7affe] bg-[#b7affe]/10 shadow-[0_0_15px_rgba(183,175,254,0.3)]' : 'border-transparent hover:border-white/10'
                        }`}
                        style={{ aspectRatio: '1 / 1' }}
                        onClick={() => setSelectedHeadUrl(item.url)}
                      >
                        <img src={item.url} alt={item.name} className="w-full h-full object-contain p-1" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Section */}
            <div className="flex flex-col gap-4 flex-1 min-h-0">
              <div className="text-base text-gray-400 font-bold ml-1">动作</div>
              <div className="bg-[#1a1c22]/80 rounded-[24px] p-5 flex-1 flex flex-col gap-5 overflow-hidden border border-white/5">
                <div className="flex flex-wrap gap-2.5">
                  {ACTION_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      className={`px-5 py-2 rounded-[12px] text-[13px] font-bold transition-all ${
                        selectedAction === opt.value ? 'bg-[#3a3a4a] text-[#b7affe] border border-[#b7affe]/30' : 'bg-[#25262b] text-gray-500 hover:text-gray-400'
                      }`}
                      onClick={() => setSelectedAction(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  {isLoadingBody ? (
                    <div className="flex items-center justify-center h-full text-gray-500 text-sm italic">加载素材中...</div>
                  ) : selectedAction ? (
                    <div className="grid grid-cols-4 gap-4">
                      {sortedBodyAssets.map((item) => (
                        <button
                          key={item.url}
                          className={`aspect-square rounded-[16px] overflow-hidden bg-black border-2 transition-all ${
                            selectedBodyUrl === item.url ? 'border-[#b7affe] bg-[#b7affe]/10 shadow-[0_0_15px_rgba(183,175,254,0.3)]' : 'border-transparent hover:border-white/10'
                          }`}
                          style={{ aspectRatio: '1 / 1' }}
                          onClick={() => setSelectedBodyUrl(item.url)}
                        >
                          <img src={item.url} alt={item.name} className="w-full h-full object-contain p-1" />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-600 text-sm">请先选择一个动作类型</div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel: Preview */}
          <div className="flex-1 flex flex-col gap-8">
            <div className="flex-1 bg-black/40 rounded-[40px] overflow-hidden flex items-center justify-center relative border border-white/5">
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" className="max-w-[90%] max-h-[90%] object-contain drop-shadow-[0_20px_50px_rgba(0,0,0,0.5)]" />
              ) : (
                <div className="flex flex-col items-center gap-4 text-gray-600">
                  <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center">
                    <div className="w-10 h-10 border-4 border-gray-700 border-t-[#b7affe] rounded-full animate-spin" style={{ display: isComposing ? 'block' : 'none' }} />
                    {!isComposing && <div className="text-4xl">?</div>}
                  </div>
                  <div className="text-xl font-medium">
                    {isComposing ? 'AI 正在拼装中...' : '在左侧选择素材以开始'}
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-5">
              <button
                onClick={handleDownload}
                disabled={!previewUrl}
                className={`flex-1 h-[72px] rounded-[24px] font-bold text-xl transition-all flex items-center justify-center gap-3 ${
                  previewUrl
                  ? 'bg-[#3a3a4a] text-[#b7affe] border-2 border-[#b7affe]/30 hover:bg-[#4a4964]' 
                  : 'bg-white/5 text-gray-600 border-2 border-transparent cursor-not-allowed'
                }`}
              >
                下载
              </button>
              <button
                onClick={() => {
                  if (!previewUrl || !baseImageUrl) return
                  onUse({ previewUrl, baseImageUrl })
                  onOpenChange(false)
                }}
                disabled={!previewUrl || !baseImageUrl || isComposing}
                className={`flex-1 h-[72px] rounded-[24px] font-bold text-xl transition-all flex items-center justify-center gap-3 ${
                  previewUrl && baseImageUrl && !isComposing 
                  ? 'bg-gradient-to-r from-[#b7affe] to-[#a6ccfd] text-[#16171d] shadow-[0_10px_30px_rgba(183,175,254,0.3)] hover:scale-[1.02] active:scale-[0.98]'
                  : 'bg-white/5 text-gray-600 cursor-not-allowed'
                }`}
              >
                {isComposing ? '拼装中...' : '使用'}
              </button>
            </div>
          </div>
        </div>

        <style jsx>{`
          .custom-scrollbar::-webkit-scrollbar {
            width: 4px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: transparent;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
          }
        `}</style>
      </div>
    </div>
  )
}
