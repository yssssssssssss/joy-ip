"use client"

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

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

const MAX_MODAL_WIDTH_PX = 1000
const MAX_MODAL_VIEWPORT_RATIO = 0.92

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

type ModalLayout = {
  width: number
  height: number
  iframeSide: number
  chromeHeight: number
}

export default function ThreeEditorModal({
  open,
  onOpenChange,
  renderPreviewUrl,
  renderFilePath,
  threePrompt,
  onThreePromptChange,
  isLoading,
  onGenerate,
}: ThreeEditorModalProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const footerRef = useRef<HTMLDivElement>(null)
  const [layout, setLayout] = useState<ModalLayout | null>(null)

  const computeLayout = useCallback(() => {
    if (typeof window === 'undefined') return

    const maxHeight = Math.floor(window.innerHeight * MAX_MODAL_VIEWPORT_RATIO)
    const maxWidth = Math.floor(Math.min(MAX_MODAL_WIDTH_PX, window.innerWidth * MAX_MODAL_VIEWPORT_RATIO))

    const headerHeight = Math.ceil(headerRef.current?.getBoundingClientRect().height ?? 0)
    const footerHeight = Math.ceil(footerRef.current?.getBoundingClientRect().height ?? 0)
    const measuredChromeHeight = headerHeight + footerHeight
    setLayout(prev => {
      const chromeHeight =
        measuredChromeHeight > 0
          ? measuredChromeHeight
          : prev?.chromeHeight ?? 160

      // 以高度为标准自适配：优先用高度算出 iframe 正方形边长，再用宽度上限兜底
      const iframeSide = Math.max(1, Math.floor(Math.min(maxWidth, maxHeight - chromeHeight)))
      const nextLayout: ModalLayout = {
        width: iframeSide,
        height: chromeHeight + iframeSide,
        iframeSide,
        chromeHeight,
      }
      if (
        prev &&
        prev.width === nextLayout.width &&
        prev.height === nextLayout.height &&
        prev.iframeSide === nextLayout.iframeSide &&
        prev.chromeHeight === nextLayout.chromeHeight
      ) {
        return prev
      }
      return nextLayout
    })
  }, [])

  useLayoutEffect(() => {
    if (!open) return
    let cancelled = false
    let frameId = 0
    let rounds = 0

    const tick = () => {
      if (cancelled) return
      computeLayout()
      rounds += 1
      if (rounds < 3) frameId = window.requestAnimationFrame(tick)
    }

    tick()

    const onResize = () => {
      rounds = 0
      tick()
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelled = true
      window.cancelAnimationFrame(frameId)
      window.removeEventListener('resize', onResize)
    }
  }, [computeLayout, open])

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
    const timer = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => window.clearTimeout(timer)
  }, [open])

  if (!open) return null

  const iframeSide =
    layout?.iframeSide ??
    (() => {
      if (typeof window === 'undefined') return 720
      const maxHeight = Math.floor(window.innerHeight * MAX_MODAL_VIEWPORT_RATIO)
      const maxWidth = Math.floor(Math.min(MAX_MODAL_WIDTH_PX, window.innerWidth * MAX_MODAL_VIEWPORT_RATIO))
      const chromeHeight = layout?.chromeHeight ?? 160
      return Math.max(1, Math.floor(Math.min(maxWidth, maxHeight - chromeHeight)))
    })()
  const uiScale = clamp(iframeSide / 720, 0.75, 1.15)
  const ui = {
    headerFontSize: Math.round(clamp(14 * uiScale, 12, 16)),
    hintFontSize: Math.round(clamp(12 * uiScale, 11, 14)),
    controlFontSize: Math.round(clamp(14 * uiScale, 12, 16)),
    controlHeight: Math.round(clamp(44 * uiScale, 34, 54)),
    previewSize: Math.round(clamp(48 * uiScale, 32, 56)),
    headerPaddingX: Math.round(clamp(12 * uiScale, 10, 16)),
    headerPaddingY: Math.round(clamp(8 * uiScale, 6, 12)),
    footerPaddingX: Math.round(clamp(16 * uiScale, 12, 20)),
    footerPaddingY: Math.round(clamp(12 * uiScale, 10, 16)),
    controlPaddingX: Math.round(clamp(16 * uiScale, 12, 18)),
    buttonPaddingX: Math.round(clamp(24 * uiScale, 16, 28)),
    radius: Math.round(clamp(12 * uiScale, 10, 16)),
    gap: Math.round(clamp(12 * uiScale, 8, 14)),
  }

  const modalStyle: React.CSSProperties = layout
    ? { width: layout.width }
    : { width: 'min(1000px, 92vw)' }

  const isCompact = iframeSide < 560

  return (
    <div
      className="fixed inset-0 z-[9998] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-[#0f1419] border border-gray-700 overflow-hidden shadow-2xl flex flex-col"
        style={{ ...modalStyle, borderRadius: ui.radius }}
      >
        <div
          ref={headerRef}
          className="flex items-center justify-between border-b border-gray-700"
          style={{ padding: `${ui.headerPaddingY}px ${ui.headerPaddingX}px` }}
        >
          <div className="text-gray-300" style={{ fontSize: ui.headerFontSize }}>JOY 3D 编辑器</div>
          <button
            type="button"
            className="text-gray-300 hover:text-white hover:bg-gray-700"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onOpenChange(false)
            }}
            style={{
              padding: `${Math.max(6, Math.round(ui.headerPaddingY * 0.75))}px ${ui.headerPaddingX}px`,
              fontSize: ui.headerFontSize,
              borderRadius: ui.radius,
            }}
          >
            关闭
          </button>
        </div>

        <div className="w-full aspect-square shrink-0">
          <iframe src="/three-editor/index.html" title="3D Editor" className="w-full h-full" />
        </div>

        <div
          ref={footerRef}
          className="border-t border-gray-700 bg-[#1a1d24]"
          style={{ padding: `${ui.footerPaddingY}px ${ui.footerPaddingX}px` }}
        >
          <div
            className={isCompact ? 'flex flex-col' : 'flex items-center'}
            style={{ gap: ui.gap }}
          >
            {renderPreviewUrl && (
              <img
                src={renderPreviewUrl}
                alt="渲染预览"
                className="object-cover border border-gray-600 flex-shrink-0"
                style={{ width: ui.previewSize, height: ui.previewSize, borderRadius: ui.radius }}
              />
            )}
            <div
              className={isCompact ? 'flex flex-col w-full' : 'flex items-center flex-1 min-w-0'}
              style={{ gap: ui.gap }}
            >
              <input
                ref={inputRef}
                type="text"
                value={threePrompt}
                onChange={(e) => onThreePromptChange(e.target.value)}
                onKeyDown={(e) => {
                  e.stopPropagation()
                  if (e.key === 'Enter') onGenerate()
                }}
                placeholder={renderFilePath ? '输入描述，然后点击生成' : '请先点击上方的开始渲染按钮'}
                className="flex-1 bg-[#2b2d33] text-white border border-gray-600 focus:border-purple-500 focus:outline-none placeholder:text-gray-500 min-w-0"
                style={{
                  height: ui.controlHeight,
                  paddingLeft: ui.controlPaddingX,
                  paddingRight: ui.controlPaddingX,
                  borderRadius: ui.radius,
                  fontSize: ui.controlFontSize,
                }}
              />
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onGenerate()
                }}
                disabled={!renderFilePath || !threePrompt.trim() || isLoading}
                className="bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                style={{
                  height: ui.controlHeight,
                  paddingLeft: ui.buttonPaddingX,
                  paddingRight: ui.buttonPaddingX,
                  borderRadius: ui.radius,
                  fontSize: ui.controlFontSize,
                }}
              >
                {isLoading ? '生成中...' : '生成'}
              </button>
            </div>
          </div>
          <div className="text-gray-500" style={{ fontSize: ui.hintFontSize, marginTop: Math.round(ui.gap * 0.6) }}>
            {renderFilePath ? '✓ 渲染图已准备好，输入描述后点击生成' : '⚠ 请先在编辑器中点击开始渲染按钮'}
          </div>
        </div>
      </div>
    </div>
  )
}
