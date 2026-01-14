"use client"

import { AnimatePresence, motion } from 'framer-motion'
import { usePathname } from 'next/navigation'

export default function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // 根据方向动态设置：返回时新页面从左向右滑入
  const isForward = pathname?.includes('/detail')
  const initialX = isForward ? '100%' : '-100%'  // 前进: 从左滑入; 返回: 从右滑入
  const exitX = isForward ? '100%' : '-100%'     // 前进: 旧向右滑出; 返回: 旧向左滑出

  return (
    // 允许页面滚动：去掉外层 overflow hidden，并在内层启用滚动
    <div style={{ position: 'relative', minHeight: '100vh', overflow: 'auto' }}>
      <AnimatePresence mode="popLayout">
        <motion.div
          key={pathname}
          initial={{ x: initialX, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          // 让旧页面滑出，同时新页面滑入，避免白色背景和闪现
          exit={{ x: exitX, opacity: 0 }}
          transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          style={{ position: 'absolute', inset: 0, willChange: 'transform', overflowY: 'auto' }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}