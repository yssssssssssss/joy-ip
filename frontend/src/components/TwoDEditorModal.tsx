"use client"

import React, { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'

type AssetItem = { name: string; url: string }

type TwoDEditorModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  perspective: string
  onUse: (baseImageUrl: string) => void
}

const ACTION_OPTIONS = [
  { label: '站立', value: '站姿' },
  { label: '动感', value: '欢快' },
  { label: '跳跃', value: '跳跃' },
  { label: '跑动', value: '跑动' },
  { label: '坐姿', value: '坐姿' },
] as const

export default function TwoDEditorModal({
  open,
  onOpenChange,
  perspective,
  onUse,
}: TwoDEditorModalProps) {
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

  const canCompose = Boolean(selectedHeadUrl && selectedBodyUrl && selectedAction && !isComposing)

  const resetAll = () => {
    setSelectedHeadUrl(null)
    setSelectedAction(null)
    setSelectedBodyUrl(null)
    setPreviewUrl(null)
    setBaseImageUrl(null)
    setBodyAssets([])
    setErrorText(null)
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

  useEffect(() => {
    if (!open) return
    resetAll()
    setHeadAssets([])
    setIsLoadingHead(true)

    const controller = new AbortController()
    ;(async () => {
      try {
        const res = await axios.get('/api/2d_assets', {
          params: { perspective, type: 'head' },
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
  }, [open, perspective])

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
        const res = await axios.get('/api/2d_assets', {
          params: { perspective, type: 'body', action: selectedAction },
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
  }, [open, perspective, selectedAction])

  if (!open) return null

  const modalSize = 'min(1100px, 94vw, 92vh)'

  const handleCompose = async () => {
    if (!selectedHeadUrl || !selectedBodyUrl || !selectedAction) return
    if (isComposing) return
    setIsComposing(true)
    setErrorText(null)
    setPreviewUrl(null)
    setBaseImageUrl(null)
    try {
      const res = await axios.post(
        '/api/2d_editor/compose',
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
    }
  }

  const handleRetry = () => {
    resetAll()
    headGridRef.current?.scrollTo({ top: 0 })
    bodyGridRef.current?.scrollTo({ top: 0 })
  }

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-[#0f1419] border border-gray-700 rounded-lg overflow-hidden shadow-2xl flex flex-col"
        style={{ width: modalSize, height: modalSize }}
      >
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
          <div className="text-sm text-gray-300">2D素材编辑器（{perspective}）</div>
          <button
            type="button"
            className="px-3 py-1 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onOpenChange(false)
            }}
          >
            关闭
          </button>
        </div>

        <div className="flex-1 min-h-0 grid grid-cols-[360px_1fr]">
          {/* 左侧：选择面板 */}
          <div className="min-h-0 border-r border-gray-700 bg-[#0b1016] p-4 flex flex-col gap-4">
            <div>
              <div className="text-xs text-gray-400 mb-2">表情</div>
              <div
                ref={headGridRef}
                className="min-h-[140px] max-h-[240px] overflow-auto rounded border border-gray-700 bg-black/20 p-2"
              >
                {isLoadingHead ? (
                  <div className="text-xs text-gray-500 p-2">加载中...</div>
                ) : sortedHeadAssets.length === 0 ? (
                  <div className="text-xs text-gray-500 p-2">暂无素材</div>
                ) : (
                  <div className="grid grid-cols-4 gap-2">
                    {sortedHeadAssets.map((item) => (
                      <button
                        key={item.url}
                        type="button"
                        className={`relative rounded overflow-hidden border transition-all ${
                          selectedHeadUrl === item.url
                            ? 'border-[#d580ff] ring-2 ring-[#d580ff]/40'
                            : 'border-white/10 hover:border-white/25'
                        }`}
                        onClick={() => setSelectedHeadUrl(item.url)}
                        title={item.name}
                      >
                        <img src={item.url} alt={item.name} className="w-full h-16 object-contain bg-black" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div>
              <div className="text-xs text-gray-400 mb-2">动作</div>
              <div className="flex flex-wrap gap-2">
                {ACTION_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                      selectedAction === opt.value
                        ? 'bg-[#5a4b7a] text-[#e0d4ff] border-[#6b5a8a]'
                        : 'bg-black/20 text-gray-200 border-white/10 hover:border-white/25'
                    }`}
                    onClick={() => setSelectedAction(opt.value)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <div className="mt-3">
                <div className="text-[11px] text-gray-500 mb-2">
                  {selectedAction ? `身体素材（${selectedAction}）` : '请选择动作后展示身体素材'}
                </div>
                <div
                  ref={bodyGridRef}
                  className="min-h-[140px] max-h-[260px] overflow-auto rounded border border-gray-700 bg-black/20 p-2"
                >
                  {!selectedAction ? (
                    <div className="text-xs text-gray-500 p-2">未选择动作</div>
                  ) : isLoadingBody ? (
                    <div className="text-xs text-gray-500 p-2">加载中...</div>
                  ) : sortedBodyAssets.length === 0 ? (
                    <div className="text-xs text-gray-500 p-2">暂无素材</div>
                  ) : (
                    <div className="grid grid-cols-3 gap-2">
                      {sortedBodyAssets.map((item) => (
                        <button
                          key={item.url}
                          type="button"
                          className={`relative rounded overflow-hidden border transition-all ${
                            selectedBodyUrl === item.url
                              ? 'border-[#a6ccfd] ring-2 ring-[#a6ccfd]/40'
                              : 'border-white/10 hover:border-white/25'
                        }`}
                        onClick={() => setSelectedBodyUrl(item.url)}
                        title={item.name}
                      >
                          <img src={item.url} alt={item.name} className="w-full h-20 object-cover bg-black" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {errorText && (
              <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2">
                {errorText}
              </div>
            )}

            <div className="mt-auto flex items-center gap-2">
              <button
                type="button"
                onClick={handleCompose}
                disabled={!canCompose}
                className="h-[40px] px-4 bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white rounded font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isComposing ? '生成中...' : '生成'}
              </button>
            </div>
          </div>

          {/* 右侧：预览面板 */}
          <div className="min-h-0 p-4 flex flex-col">
            <div className="text-xs text-gray-400 mb-2">拼装结果</div>
            <div className="flex-1 min-h-0 rounded border border-gray-700 bg-black flex items-center justify-center overflow-hidden">
              {previewUrl ? (
                <img src={previewUrl} alt="2D 拼装结果" className="max-w-full max-h-full object-contain" />
              ) : (
                <div className="text-sm text-gray-500">
                  {isComposing ? '正在生成...' : '请选择表情与身体素材后点击“生成”'}
                </div>
              )}
            </div>

            <div className="mt-4 flex items-center gap-2">
              {baseImageUrl && (
                <button
                  type="button"
                  onClick={handleRetry}
                  className="h-[44px] px-6 bg-gray-700/40 text-gray-200 rounded-lg hover:bg-gray-600/40"
                >
                  重试
                </button>
              )}
              <button
                type="button"
                disabled={!baseImageUrl}
                onClick={() => {
                  if (!baseImageUrl) return
                  onUse(baseImageUrl)
                  onOpenChange(false)
                }}
                className="h-[44px] px-6 bg-white/90 text-black rounded-lg font-medium hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed"
              >
                使用
              </button>
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="h-[44px] px-6 bg-gray-700/40 text-gray-200 rounded-lg hover:bg-gray-600/40"
              >
                取消
              </button>
              <div className="ml-auto text-[11px] text-gray-500">
                预览为透底 2000×2000；点击“使用”后将以白底 1024×1200 作为底图进入后续流程
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
