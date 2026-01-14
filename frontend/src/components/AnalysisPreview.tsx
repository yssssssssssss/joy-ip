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
  视角?: string
}

// 维度配置
const BASE_DIMENSIONS = [
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

  // 根据分析结果动态构建维度列表
  const dimensions = React.useMemo(() => {
    const dims = [...BASE_DIMENSIONS] as any[]
    // 如果分析结果中包含“视角”，则插入到动作之后
    if (analysis && '视角' in analysis) {
      dims.splice(2, 0, { 
        key: '视角', 
        label: '视角', 
        placeholder: '如：正视角、仰视角', 
        icon: '' 
      })
    }
    return dims
  }, [analysis])

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
    <div className="w-full max-w-xl mx-auto">
      {/* 卡片容器 - 紧凑液态玻璃质感 */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/30 backdrop-blur-xl shadow-2xl transition-all duration-300">
        {/* 玻璃高光层 */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent pointer-events-none" />
        
        {/* 标题栏 - 紧凑型 */}
        <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between bg-white/5">
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-white/90 tracking-[0.2em] uppercase">Preview</h3>
            {originalPrompt && (
              <p className="text-[10px] text-white/40 mt-0.5 truncate uppercase tracking-wider">
                Prompt: {originalPrompt}
              </p>
            )}
          </div>
          <div className="flex gap-1.5">
            <div className="w-2 h-2 rounded-full bg-white/10" />
            <div className="w-2 h-2 rounded-full bg-white/20" />
            <div className="w-2 h-2 rounded-full bg-white/30" />
          </div>
        </div>

        {/* 六维度列表 - 极简紧凑 */}
        <div className="p-3 space-y-1">
          {dimensions.map(({ key, label, placeholder }) => {
            const value = analysis[key as keyof AnalysisResult] || ''
            const isEditing = editingKey === key

            return (
              <div
                key={key}
                className={`
                  flex items-center gap-3 px-3 py-1.5 rounded-lg border transition-all duration-300
                  ${isEditing 
                    ? 'bg-white/10 border-white/30 ring-1 ring-white/10' 
                    : 'bg-transparent border-transparent hover:bg-white/5'
                  }
                `}
              >
                {/* 标签 - 固定宽度 */}
                <div className="w-10 flex-shrink-0">
                    <span className="text-[11px] font-bold text-white/30 uppercase tracking-tighter">{label}</span>
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
                      className="w-full px-0 py-0.5 bg-transparent text-white text-sm placeholder:text-white/20 border-none focus:outline-none focus:ring-0"
                    />
                  ) : (
                    <span className={`text-sm block truncate ${value ? 'text-white/80' : 'text-white/20 italic'}`}>
                      {value || 'None'}
                    </span>
                  )}
                </div>

                {/* 操作按钮 - 始终显示 */}
                <div className="flex-shrink-0">
                  {isEditing ? (
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveEdit}
                        className="p-1.5 text-white hover:bg-white/10 rounded-md transition-colors"
                        title="Save"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-1.5 text-white/40 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleStartEdit(key, value)}
                      className="p-1.5 text-white/20 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                      title="Edit"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* 底部操作栏 - 紧凑型 */}
        <div className="px-5 py-3 border-t border-white/10 bg-black/20 flex items-center justify-between">
          <span className="text-[10px] text-white/20 uppercase tracking-widest">Awaiting Confirmation</span>
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              disabled={isGenerating}
              className="px-4 py-1.5 text-[11px] font-bold text-white/40 hover:text-white tracking-widest uppercase transition-all"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isGenerating}
              className="px-6 py-1.5 text-[11px] font-black text-black bg-white/90 hover:bg-white backdrop-blur-md rounded-md tracking-[0.2em] uppercase transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Processing
                </>
              ) : (
                'Generate'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
