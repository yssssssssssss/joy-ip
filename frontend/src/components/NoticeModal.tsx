"use client"

import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { NOTICE_CONFIG } from '@/lib/noticeConfig'

/**
 * 简单的 Markdown 解析器
 * 支持：粗体、三级标题、列表、斜体
 */
const parseMarkdown = (text: string) => {
    return text
        .split('\n')
        .map((line, index) => {
            // 标题 ###
            if (line.startsWith('### ')) {
                return <h3 key={index} className="text-lg font-bold mt-4 mb-2 text-white/90">{line.replace('### ', '')}</h3>
            }
            // 列表 -
            if (line.startsWith('- ')) {
                return <li key={index} className="ml-4 mb-1 text-white/70 list-disc">{line.replace('- ', '')}</li>
            }
            // 空行
            if (line.trim() === '') {
                return <div key={index} className="h-2" />
            }

            // 处理行内样式：粗体 **text** 和 斜体 *text*
            let content: React.ReactNode = line

            // 粗体
            const boldRegex = /\*\*(.*?)\*\*/g
            const parts = line.split(boldRegex)
            if (parts.length > 1) {
                content = parts.map((part, i) =>
                    i % 2 === 1 ? <strong key={i} className="text-blue-400 font-bold">{part}</strong> : part
                )
            }

            // 斜体 (简单处理)
            if (typeof content === 'string' && content.startsWith('*') && content.endsWith('*')) {
                content = <em className="text-white/50 italic">{content.slice(1, -1)}</em>
            }

            return <p key={index} className="text-white/80 leading-relaxed">{content}</p>
        })
}

export default function NoticeModal() {
    const [isOpen, setIsOpen] = useState(false)
    const [progress, setProgress] = useState(100)
    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const progressRef = useRef<NodeJS.Timeout | null>(null)

    useEffect(() => {
        // 1. 检查是否开启了“预览模式”（每次刷新都显示）
        const isAlwaysShow = NOTICE_CONFIG.alwaysShow

        // 2. 检查是否已看过该版本的公告
        const lastSeenVersion = localStorage.getItem('notice_version')
        const isNewVersion = lastSeenVersion !== NOTICE_CONFIG.version

        // 只要满足其中之一就弹出
        if (isAlwaysShow || isNewVersion) {
            setIsOpen(true)

            // 10秒后自动关闭
            timerRef.current = setTimeout(() => {
                handleClose()
            }, NOTICE_CONFIG.duration)

            // 进度条动画
            const step = 100 / (NOTICE_CONFIG.duration / 100)
            progressRef.current = setInterval(() => {
                setProgress(prev => Math.max(0, prev - step))
            }, 100)
        }

        return () => {
            if (timerRef.current) clearTimeout(timerRef.current)
            if (progressRef.current) clearInterval(progressRef.current)
        }
    }, [])

    const handleClose = () => {
        setIsOpen(false)
        // 只有在关闭时，才记录当前版本号，标记为“已看过”
        localStorage.setItem('notice_version', NOTICE_CONFIG.version)
        if (timerRef.current) clearTimeout(timerRef.current)
        if (progressRef.current) clearInterval(progressRef.current)
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-white/10 bg-[#1A1A1A]/90 shadow-2xl shadow-black/50"
                    >
                        {/* 顶部进度条 */}
                        <div className="absolute top-0 left-0 h-1 bg-blue-500/50 w-full">
                            <motion.div
                                className="h-full bg-blue-500"
                                style={{ width: `${progress}%` }}
                            />
                        </div>

                        {/* 关闭按钮 */}
                        <button
                            onClick={handleClose}
                            className="absolute top-4 right-4 p-1 rounded-full hover:bg-white/10 transition-colors text-white/50 hover:text-white"
                        >
                            <X size={20} />
                        </button>

                        {/* 内容区 */}
                        <div className="p-8 pt-10">
                            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                                <span className="w-2 h-6 bg-blue-500 rounded-full" />
                                {NOTICE_CONFIG.title}
                            </h2>

                            <div className="max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
                                {parseMarkdown(NOTICE_CONFIG.content)}
                            </div>

                            <div className="mt-8 flex justify-end">
                                <button
                                    onClick={handleClose}
                                    className="px-6 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all active:scale-95 shadow-lg shadow-blue-900/20"
                                >
                                    我知道了
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}
