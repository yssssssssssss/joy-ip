"use client"

import React from 'react'
import { Pencil, Check, X, Loader2 } from 'lucide-react'

// 六维度分析结果类型
export interface AnalysisResult {
  表情: string
  动作: string
  上装: string
  下装: string
  头戴: string
  手持: string
}

// 维度配置
const DIMENSIONS = [
  { key: '表情', label: '表情', placeholder: '如：开心、微笑、惊讶', icon: '' },
  { key: '动作', label: '动作', placeholder: '如：站姿、坐姿、跑步', icon: '' },
  { key: '上装', label: '上装', placeholder: '如：红色夹克、白色T恤', icon: '' },
  { key: '下装', label: '下装', placeholder: '如：牛仔裤、运动裤', icon: '' },
  { key: '头戴', label: '头戴', placeholder: '如：圣诞帽、棒球帽', icon: '' },
  { key: '手持', label: '手持', placeholder: '如：礼物盒、魔法棒', icon: '' },
] as const

interface AnalysisPreviewProps {
  analysis: AnalysisResult
  onAnalysisChange: (analysis: AnalysisResult) => void
  onConfirm: () => void
  onCancel: () => void
  isGenerating?: boolean
  originalPrompt?: string
}

export default function AnalysisPreview({
  analysis,
  onAnalysisChange,
  onConfirm,
  onCancel,
  isGenerating = false,
  originalPrompt = ''
}: AnalysisPreviewProps) {
  const [editingKey, setEditingKey] = React.useState<string | null>(null)
  const [editValue, setEditValue] = React.useState('')

  const handleStartEdit = (key: string, value: string) => {
    setEditingKey(key)
    setEditValue(value || '')
  }

  const handleSaveEdit = () => {
    if (editingKey) {
      onAnalysisChange({
        ...analysis,
        [editingKey]: editValue.trim()
      })
      setEditingKey(null)
      setEditValue('')
    }
  }

  const handleCancelEdit = () => {
    setEditingKey(null)
    setEditValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit()
    } else if (e.key === 'Escape') {
      handleCancelEdit()
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* 卡片容器 - 毛玻璃质感 */}
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-white/5 backdrop-blur-md shadow-2xl transition-all duration-300">
        
        {/* 标题栏 */}
        <div className="px-6 py-5 border-b border-white/10 bg-white/5">
          <h3 className="text-lg font-semibold text-white/90 tracking-wide">分析预览</h3>
          {originalPrompt && (
            <p className="text-sm text-gray-400 mt-1 truncate">
              原始描述：{originalPrompt}
            </p>
          )}
        </div>

        {/* 六维度列表 */}
        <div className="p-6 space-y-3">
          {DIMENSIONS.map(({ key, label, placeholder, icon }) => {
            const value = analysis[key as keyof AnalysisResult] || ''
            const isEditing = editingKey === key

            return (
              <div
                key={key}
                className={`
                  group flex items-center gap-4 p-3 rounded-xl border transition-all duration-200
                  ${isEditing 
                    ? 'bg-white/10 border-purple-500/50 ring-1 ring-purple-500/20' 
                    : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/20'
                  }
                `}
              >
                {/* 标签 */}
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10">
                    <span className="text-xs font-medium text-gray-300">{label}</span>
                </div>

                {/* 值/编辑框 */}
                <div className="flex-1 min-w-0">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={placeholder}
                      autoFocus
                      className="w-full px-0 py-1 bg-transparent text-white text-base placeholder:text-gray-500 border-none focus:outline-none focus:ring-0"
                    />
                  ) : (
                    <span className={`text-base block truncate ${value ? 'text-white/90' : 'text-gray-500 italic'}`}>
                      {value || '未设置'}
                    </span>
                  )}
                </div>

                {/* 操作按钮 */}
                <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                  {isEditing ? (
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveEdit}
                        className="p-2 text-green-400 hover:text-green-300 hover:bg-green-500/20 rounded-full transition-colors"
                        title="保存"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-2 text-gray-400 hover:text-gray-300 hover:bg-white/10 rounded-full transition-colors"
                        title="取消"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleStartEdit(key, value)}
                      className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                      title="编辑"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* 底部操作栏 */}
        <div className="px-6 py-5 border-t border-white/10 bg-white/5 flex items-center justify-between">
          <p className="text-xs text-gray-500/80">
            点击列表项右侧按钮修改内容
          </p>
          <div className="flex gap-4">
            <button
              onClick={onCancel}
              disabled={isGenerating}
              className="px-5 py-2.5 text-sm font-medium text-gray-300 hover:text-white hover:bg-white/10 rounded-xl transition-all disabled:opacity-50"
            >
              取消
            </button>
            <button
              onClick={onConfirm}
              disabled={isGenerating}
              className="px-8 py-2.5 text-sm font-semibold text-white bg-white/20 hover:bg-white/30 border border-white/30 backdrop-blur-sm rounded-xl shadow-lg shadow-black/20 hover:shadow-black/40 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  生成中...
                </>
              ) : (
                '确认生成'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
