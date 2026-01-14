// 简易滚动记忆工具：基于 sessionStorage 保存/恢复滚动位置
// 适配 React/Next.js；可用于窗口滚动或指定容器滚动

export const getRouteKey = (): string => {
  if (typeof window === 'undefined') return '/'
  return `${window.location.pathname}${window.location.search}`
}

const storageKey = (routeKey: string) => `__scroll__${routeKey}`

export const saveScrollPos = (routeKey: string, pos: number) => {
  try {
    const key = storageKey(routeKey)
    const v = Number.isFinite(pos) && pos >= 0 ? String(Math.floor(pos)) : '0'
    sessionStorage.setItem(key, v)
  } catch {}
}

export const readScrollPos = (routeKey: string): number | null => {
  try {
    const key = storageKey(routeKey)
    const v = sessionStorage.getItem(key)
    if (v == null) return null
    const n = parseInt(v, 10)
    return Number.isFinite(n) && n >= 0 ? n : null
  } catch {
    return null
  }
}

// 在指定容器内恢复滚动位置；默认首帧立即设置并在下一帧/微任务重试，尽量稳定
export const restoreElementScroll = (
  el: HTMLElement | null,
  pos: number | null,
  opts: { smooth?: boolean; retries?: number; delayMs?: number } = {}
) => {
  if (!el || pos == null || pos < 0) return
  const { smooth = false, retries = 2, delayMs = 0 } = opts

  try {
    if (smooth && 'scrollTo' in el) {
      // 先设置到目标位置，再进行一次平滑滚动确认（避免布局晚到导致跳动）
      el.scrollTop = pos
      requestAnimationFrame(() => {
        try {
          // 现代浏览器 HTMLElement 支持 scrollTo，但 TS 默认类型未声明
          ;(el as any).scrollTo({ top: pos, behavior: 'smooth' })
        } catch {
          el.scrollTop = pos
        }
      })
    } else {
      el.scrollTop = pos
    }

    // 少量重试：处理内容高度晚渲染的场景
    let attempts = retries
    const retry = () => {
      if (attempts <= 0) return
      attempts -= 1
      if (delayMs > 0) {
        setTimeout(() => {
          el.scrollTop = pos
          if (el.scrollTop !== pos) retry()
        }, delayMs)
      } else {
        requestAnimationFrame(() => {
          el.scrollTop = pos
          if (el.scrollTop !== pos) retry()
        })
      }
    }
    retry()
  } catch {}
}

// 恢复窗口滚动（用于使用 window.scrollY 的页面）
export const restoreWindowScroll = (
  pos: number | null,
  opts: { smooth?: boolean } = {}
) => {
  if (typeof window === 'undefined' || pos == null || pos < 0) return
  const { smooth = false } = opts
  try {
    window.scrollTo({ top: pos, behavior: smooth ? 'smooth' : 'auto' })
  } catch {
    window.scrollTo(0, pos)
  }
}
