"use client"

import React, { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

type ThreeEditorModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  renderPreviewUrl: string | null
  renderFilePath: string | null
  threePrompt: string
  onThreePromptChange: (value: string) => void
  isLoading: boolean
  onGenerate: () => void
}

type ApprovedModel = { name?: string; url: string; preview: string }

const LIGHT_OPTIONS = [
  { label: '强对比', value: '强对比' },
  { label: '常规', value: '常规' },
  { label: '弱对比', value: '弱对比' },
] as const

export default function ThreeEditorModal({
  open,
  onOpenChange,
  renderPreviewUrl,
  isLoading,
}: ThreeEditorModalProps) {
  const [selectedLight, setSelectedLight] = useState<string>('弱对比')
  const [approvedModels, setApprovedModels] = useState<ApprovedModel[]>([])
  const [selectedModelUrl, setSelectedModelUrl] = useState<string | null>(null)
  const [isLoadingApprovedModels, setIsLoadingApprovedModels] = useState(false)
  const threeEditorIframeRef = useRef<HTMLIFrameElement | null>(null)

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
    setIsLoadingApprovedModels(true)
    ;(async () => {
      try {
        const resp = await fetch('/three-editor/approved-models.json', { cache: 'no-store' })
        if (!resp.ok) throw new Error('加载预审模型失败')
        const list = await resp.json()
        if (Array.isArray(list)) {
          setApprovedModels(list)
          setSelectedModelUrl(list[0]?.url ?? null)
        } else {
          setApprovedModels([])
          setSelectedModelUrl(null)
        }
      } catch {
        setApprovedModels([])
        setSelectedModelUrl(null)
      } finally {
        setIsLoadingApprovedModels(false)
      }
    })()
  }, [open])

  useEffect(() => {
    if (!open) return
    const handleLoad = () => {
      const win = threeEditorIframeRef.current?.contentWindow
      if (!win) return
      const level = selectedLight === '强对比' ? 'strong' : selectedLight === '常规' ? 'normal' : 'weak'
      win.postMessage({ type: 'three-editor-set-contrast', level }, '*')
    }
    const iframe = threeEditorIframeRef.current
    if (iframe) {
      iframe.addEventListener('load', handleLoad)
      // 如果 iframe 已经加载完成，手动调用一次
      if (iframe.contentDocument?.readyState === 'complete') {
        handleLoad()
      }
    }
    return () => iframe?.removeEventListener('load', handleLoad)
  }, [open, selectedLight])

  useEffect(() => {
    if (!open || !selectedModelUrl) return
    const handleLoadModel = () => {
      const win = threeEditorIframeRef.current?.contentWindow
      if (!win) return
      win.postMessage({ type: 'three-editor-load-model', url: selectedModelUrl }, '*')
    }
    const iframe = threeEditorIframeRef.current
    if (iframe) {
      iframe.addEventListener('load', handleLoadModel)
      if (iframe.contentDocument?.readyState === 'complete') {
        handleLoadModel()
      }
    }
    return () => iframe?.removeEventListener('load', handleLoadModel)
  }, [open, selectedModelUrl])

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
          <div className="text-[32px] font-bold text-white tracking-tight">JOY 3D 渲染建模</div>
          <button
            onClick={() => onOpenChange(false)}
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10 transition-all"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 min-h-0 flex px-10 pb-10 gap-10">
          {/* Left Panel: Controls */}
          <div className="w-[480px] flex flex-col gap-8">
            {/* Approved Models Section */}
            <div className="flex flex-col gap-4">
              <div className="text-base text-gray-400 font-bold ml-1">预审模型相片墙</div>
              <div className="bg-[#1a1c22]/80 rounded-[24px] p-5 border border-white/5">
                <div className="approved-grid">
                  {isLoadingApprovedModels ? (
                    <div className="text-sm text-gray-500">加载中...</div>
                  ) : approvedModels.length ? (
                    approvedModels.map((item) => (
                      <button
                        key={item.url}
                        type="button"
                        className={`flex-shrink-0 flex flex-col items-center gap-2.5 p-2.5 rounded-[20px] border-2 transition-all hover:bg-white/5 ${
                          selectedModelUrl === item.url ? 'border-[#b7affe]/60 bg-white/5' : 'border-transparent'
                        }`}
                        onClick={() => {
                          setSelectedModelUrl(item.url)
                        }}
                      >
                        <div className="w-[80px] h-[80px] rounded-[16px] bg-black overflow-hidden border border-white/5 flex items-center justify-center">
                          <img src={item.preview} alt={item.name || '预审模型'} className="w-full h-full object-contain" />
                        </div>
                        <span className="text-[13px] font-bold text-gray-500">{item.name || ''}</span>
                      </button>
                    ))
                  ) : (
                    <div className="text-sm text-gray-500">暂无预审模型</div>
                  )}
                </div>
              </div>
            </div>

            {/* Light Section */}
            <div className="flex flex-col gap-4">
              <div className="text-base text-gray-400 font-bold ml-1">灯光</div>
              <div className="bg-[#1a1c22]/80 rounded-[24px] p-5 border border-white/5">
                <div className="light-buttons">
                  {LIGHT_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      className={`flex-1 py-3.5 rounded-[16px] text-sm font-bold transition-all ${
                        selectedLight === opt.value ? 'bg-[#3a3a4a] text-[#b7affe] border border-[#b7affe]/30' : 'bg-[#25262b] text-gray-500 hover:text-gray-400'
                      }`}
                      onClick={() => {
                        setSelectedLight(opt.value)
                        const win = threeEditorIframeRef.current?.contentWindow
                        if (!win) return
                        const level = opt.value === '强对比' ? 'strong' : opt.value === '常规' ? 'normal' : 'weak'
                        win.postMessage({ type: 'three-editor-set-contrast', level }, '*')
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Panel: Preview/Iframe */}
          <div className="flex-1 flex flex-col gap-8">
            <div className="flex-1 bg-black/40 rounded-[40px] overflow-hidden flex items-center justify-center relative border border-white/5">
              <iframe
                ref={threeEditorIframeRef}
                src="/three-editor/index.html"
                title="3D Editor"
                className={`w-full h-full ${renderPreviewUrl ? 'absolute inset-0 opacity-0 pointer-events-none' : 'opacity-80'}`}
              />
              {renderPreviewUrl ? (
                <img
                  src={renderPreviewUrl}
                  alt="Preview"
                  className="max-w-[90%] max-h-[90%] object-contain drop-shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
                />
              ) : null}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-5">
              <button
                onClick={() => {
                  if (!renderPreviewUrl) return
                  const a = document.createElement('a')
                  a.href = renderPreviewUrl
                  a.download = `joy-3d-render-${Date.now()}.png`
                  a.click()
                }}
                className={`flex-1 h-[72px] rounded-[24px] font-bold text-xl transition-all flex items-center justify-center gap-3 ${
                  renderPreviewUrl
                  ? 'bg-[#3a3a4a] text-[#b7affe] border-2 border-[#b7affe]/30 hover:bg-[#4a4964]' 
                  : 'bg-white/5 text-gray-600 border-2 border-transparent cursor-not-allowed'
                }`}
              >
                下载
              </button>
              <button
                onClick={() => {
                  const win = threeEditorIframeRef.current?.contentWindow
                  if (!win) return
                  win.postMessage({ type: 'three-editor-hq-render-default' }, '*')
                }}
                disabled={isLoading}
                className={`flex-1 h-[72px] rounded-[24px] font-bold text-xl transition-all flex items-center justify-center gap-3 ${
                  !isLoading 
                  ? 'bg-gradient-to-r from-[#b7affe] to-[#a6ccfd] text-[#16171d] shadow-[0_10px_30px_rgba(183,175,254,0.3)] hover:scale-[1.02] active:scale-[0.98]'
                  : 'bg-white/5 text-gray-600 cursor-not-allowed'
                }`}
              >
                {isLoading ? '生成中...' : '使用'}
              </button>
            </div>
          </div>
        </div>

        <style>{`
          .approved-grid {
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding-bottom: 0.5rem;
          }
          .approved-grid::-webkit-scrollbar {
            height: 4px;
            width: 4px;
          }
          .approved-grid::-webkit-scrollbar-track {
            background: transparent;
          }
          .approved-grid::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
          }
          .approved-grid::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
          }
          .light-buttons {
            display: flex;
            gap: 0.75rem;
          }
          .custom-scrollbar::-webkit-scrollbar {
            height: 4px;
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
