import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

interface RunningLogBarProps {
  visible: boolean
  text: string
}

export default function RunningLogBar({ visible, text }: RunningLogBarProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const textRef = useRef<HTMLSpanElement>(null)
  const [marqueeKey, setMarqueeKey] = useState(0)
  const [marquee, setMarquee] = useState<{ enabled: boolean; distancePx: number; durationSec: number }>({
    enabled: false,
    distancePx: 0,
    durationSec: 0
  })

  const displayText = text || ''

  const recalcMarquee = useCallback(() => {
    const container = containerRef.current
    const content = textRef.current
    if (!container || !content) return

    if (!visible || !displayText) {
      setMarquee(prev => (prev.enabled ? { enabled: false, distancePx: 0, durationSec: 0 } : prev))
      return
    }

    const containerWidth = container.getBoundingClientRect().width
    const contentWidth = content.scrollWidth
    const overflowPx = Math.ceil(contentWidth - containerWidth)

    if (overflowPx <= 1) {
      setMarquee(prev => (prev.enabled ? { enabled: false, distancePx: 0, durationSec: 0 } : prev))
      return
    }

    const distancePx = overflowPx + 16
    const durationSec = Math.min(24, Math.max(8, distancePx / 60))

    setMarquee(prev => {
      if (prev.enabled && prev.distancePx === distancePx && prev.durationSec === durationSec) return prev
      return { enabled: true, distancePx, durationSec }
    })
  }, [visible, displayText])

  useLayoutEffect(() => {
    recalcMarquee()
  }, [recalcMarquee])

  useEffect(() => {
    if (!visible) return
    setMarqueeKey(key => key + 1)
  }, [visible, displayText])

  useEffect(() => {
    if (!visible) return
    if (typeof ResizeObserver === 'undefined') return

    const container = containerRef.current
    const content = textRef.current
    if (!container || !content) return

    const observer = new ResizeObserver(() => recalcMarquee())
    observer.observe(container)
    observer.observe(content)
    return () => observer.disconnect()
  }, [visible, recalcMarquee])

  return (
    <div
      className={`overflow-hidden transition-[max-height,opacity] duration-300 ${
        visible ? 'max-h-12 opacity-100 mb-4' : 'max-h-0 opacity-0 mb-0'
      }`}
      aria-hidden={!visible}
    >
      <div className={`transform transition-transform duration-300 ${visible ? 'translate-y-0' : '-translate-y-2'}`}>
        <div className="h-8 flex items-center gap-2 px-4 rounded-[12px] bg-[#2b2d33] border border-white/10 shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="relative flex items-center justify-center w-2.5 h-2.5 flex-shrink-0">
            <span className="absolute inline-flex h-2.5 w-2.5 rounded-full bg-purple-400/30 animate-ping" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-gradient-to-r from-[#d580ff] to-[#a6ccfd]" />
          </div>
          <div ref={containerRef} className="relative flex-1 min-w-0 overflow-hidden">
            <span
              key={marqueeKey}
              ref={textRef}
              className={`block text-xs text-white/70 whitespace-nowrap ${marquee.enabled ? 'joy-running-log-marquee' : 'truncate'}`}
              style={
                marquee.enabled
                  ? ({
                    '--joy-running-log-distance': `${marquee.distancePx}px`,
                    '--joy-running-log-duration': `${marquee.durationSec}s`
                  } as React.CSSProperties)
                  : undefined
              }
              aria-live="polite"
            >
              {displayText}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
