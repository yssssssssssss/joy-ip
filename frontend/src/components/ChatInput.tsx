import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Send, Smile, Activity, Palette, Eye, X } from 'lucide-react'
import RunningLogBar from './RunningLogBar'

const PRESETS = {
  expression: {
    label: '表情',
    icon: Smile,
    options: ['大笑', '微笑', '陶醉', '眨眼']
  },
  action: {
    label: '动作',
    icon: Activity,
    options: ['站姿', '坐姿', '跳跃', '跑动', '动态']
  },
  style: {
    label: '场景',
    icon: Palette,
    options: ['圣诞风', '新年风', '运动风', '魔法风', '老板风']
  }
}

// 2D模式下的视角选项
const PERSPECTIVE_PRESET = {
  perspective: {
    label: '视角',
    icon: Eye,
    options: ['正视角', '仰视角']
  }
}

interface ChatInputProps {
  input: string
  setInput: (value: string) => void
  handleSend: (overrideText?: string) => void
  isLoading: boolean
  insertPreset: (text: string, type: 'expression' | 'action' | 'style' | 'perspective') => void
  variant?: 'bottom' | 'center'
  onOpenThreeTest?: () => void
  onOpenTwoDEditor?: () => void
  onOpenThreeDEditor?: () => void
  runningLogVisible?: boolean
  runningLogText?: string
  // 新增: 2D/3D模式切换
  generationMode?: '2D' | '3D'
  setGenerationMode?: (mode: '2D' | '3D') => void
  // 新增: 视角选择
  perspective?: string
  setPerspective?: (perspective: string) => void
  titlePreviewUrl?: string | null
  onClearTitlePreview?: () => void
  inputPreviewUrl?: string | null
  onClearInputPreview?: () => void
}

export default function ChatInput({
  input,
  setInput,
  handleSend,
  isLoading,
  insertPreset,
  variant = 'bottom',
  onOpenThreeTest,
  onOpenTwoDEditor,
  onOpenThreeDEditor,
  runningLogVisible = false,
  runningLogText = '',
  generationMode = '3D',
  setGenerationMode,
  perspective = '正视角',
  setPerspective,
  titlePreviewUrl = null,
  onClearTitlePreview,
  inputPreviewUrl = null,
  onClearInputPreview,
}: ChatInputProps) {
  const isCenter = variant === 'center'
  const is2DMode = generationMode === '2D'
  const basePreviewUrl = titlePreviewUrl

  const PreviewThumb = ({
    url,
    alt,
    objectClassName,
    onClear,
    clearLabel,
  }: {
    url: string
    alt: string
    objectClassName: string
    onClear?: () => void
    clearLabel: string
  }) => (
    <div className="relative mt-3 w-[92px] h-[92px]">
      <img
        src={url}
        alt={alt}
        className={`w-full h-full rounded-[16px] border border-white/10 bg-black/40 ${objectClassName}`}
      />
      <button
        type="button"
        onClick={onClear}
        disabled={!onClear}
        className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-black/70 border border-white/10 text-white/80 hover:text-white hover:bg-black/90 transition-all flex items-center justify-center"
        aria-label={clearLabel}
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )

  // Tab切换组件
  const TabSwitch = () => (
    <div className="flex items-center bg-[#25262b] rounded-[10px] p-1 border border-white/5">
      <button
        onClick={() => setGenerationMode?.('2D')}
        className={`px-3 py-1 rounded-[8px] text-[13px] font-bold transition-all duration-200 ${is2DMode
          ? 'bg-[#3a3a4a] text-[#b7affe]'
          : 'text-gray-500 hover:text-gray-400'
          }`}
      >
        2D
      </button>
      <button
        onClick={() => setGenerationMode?.('3D')}
        className={`px-3 py-1 rounded-[8px] text-[13px] font-bold transition-all duration-200 ${!is2DMode
          ? 'bg-[#3a3a4a] text-[#b7affe]'
          : 'text-gray-500 hover:text-gray-400'
          }`}
      >
        3D
      </button>
    </div>
  )

  if (isCenter) {
    return (
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-[915px]">
          <RunningLogBar 
            visible={runningLogVisible && !!runningLogText} 
            text={runningLogText} 
          />

          <div className="w-full max-w-[915px] rounded-[30px] border border-white/10 bg-[#16171d] shadow-[0_8px_32px_rgba(0,0,0,0.45)] flex flex-col min-h-[160px] p-6 pb-4">
            {/* Top Section: Title and Input area */}
            <div className="flex items-start gap-4 flex-1">
              <div className="flex flex-col items-start">
                <div className="text-[#b7affe] text-[19px] font-bold whitespace-nowrap pt-1">
                  {is2DMode ? '2D素材生成' : 'JOY生成'}
                </div>
                {basePreviewUrl ? (
                  <PreviewThumb
                    url={basePreviewUrl}
                    alt="底图预览"
                    objectClassName="object-cover"
                    onClear={onClearTitlePreview}
                    clearLabel="删除预览图"
                  />
                ) : null}
                {inputPreviewUrl ? (
                  <PreviewThumb
                    url={inputPreviewUrl}
                    alt="Compose Preview"
                    objectClassName="object-contain"
                    onClear={onClearInputPreview}
                    clearLabel="Clear compose preview"
                  />
                ) : null}
              </div>
              
              <div className="flex-1 flex flex-col">
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder={is2DMode ? "描述你想要生成的2D素材" : "描述你想要生成的JOY"}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={isLoading}
                  className="flex-1 bg-transparent border-0 outline-none text-gray-200 placeholder:text-gray-600 resize-none text-[17px] py-1.5 min-h-[60px] font-normal"
                />
              </div>
            </div>

            {/* Bottom Section: Mode switch, buttons, and send */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-3">
                <TabSwitch />
                
                {is2DMode ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-[40px] px-3.5 rounded-[11px] bg-[#3a3a4a] text-[#b7affe] border-0 hover:bg-[#4a4964] flex items-center gap-2 text-[13px] font-bold"
                    onClick={() => onOpenTwoDEditor?.()}
                  >
                    <div className="w-6 h-6 rounded-full bg-black/40 flex items-center justify-center overflow-hidden">
                      <Palette className="w-3.5 h-3.5 text-[#b7affe]" />
                    </div>
                    2D素材拼装
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-[40px] px-3.5 rounded-[11px] bg-[#3a3a4a] text-[#b7affe] border-0 hover:bg-[#4a4964] flex items-center gap-2 text-[13px] font-bold"
                      onClick={() => onOpenThreeTest?.()}
                    >
                      <div className="w-6 h-6 rounded-full bg-black/40 flex items-center justify-center overflow-hidden">
                        <Smile className="w-3.5 h-3.5 text-[#b7affe]" />
                      </div>
                      3D渲染建模
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-[40px] px-3.5 rounded-[11px] bg-[#3a3a4a] text-[#b7affe] border-0 hover:bg-[#4a4964] flex items-center gap-2 text-[13px] font-bold"
                      onClick={() => onOpenThreeDEditor?.()}
                    >
                      <div className="w-6 h-6 rounded-full bg-black/40 flex items-center justify-center overflow-hidden">
                        <Activity className="w-3.5 h-3.5 text-[#b7affe]" />
                      </div>
                      3D素材拼模
                    </Button>
                  </>
                )}
              </div>

              <div className="flex items-center gap-3">
                {isLoading && (
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white/60"></div>
                )}
                <Button 
                  onClick={() => handleSend()} 
                  disabled={isLoading || !input.trim()} 
                  className="rounded-full h-[52px] w-[52px] bg-[#2b2d33] text-gray-400 border border-white/5 hover:bg-[#35373d] hover:text-white transition-all duration-200 disabled:opacity-20 disabled:cursor-not-allowed flex-shrink-0 shadow-lg"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }



  // bottom variant
  return (
    <div className="p-4">
      {/* Tab切换 (bottom variant) */}
      <div className="flex items-center justify-center mb-3">
        <TabSwitch />
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={is2DMode ? "描述你想要生成的2D素材..." : "请输入您的创意要求..."}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            disabled={isLoading}
            className="h-[40px] pr-10 bg-black/40 text-white border border-white/20 placeholder:text-gray-500 rounded focus:ring-2 focus:ring-primary"
          />
        </div>
        {isLoading && (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary"></div>
        )}
        <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white rounded px-3 py-2 transition-all duration-200 hover:opacity-90 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
          <Send className="w-5 h-5" />
        </Button>
      </div>
      <div className="flex items-center gap-1 mt-2 flex-wrap">
        {/* 2D模式下显示视角按钮 */}
        {is2DMode && (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="sm" className="hover:bg-white/10 text-[#e0d4ff]">
                <Eye className="w-5 h-5 mr-1" />
                {perspective}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-36 p-2">
              <div className="grid grid-cols-1 gap-2">
                {PERSPECTIVE_PRESET.perspective.options.map(option => (
                  <Button
                    key={option}
                    variant="outline"
                    size="sm"
                    className={perspective === option ? 'ring-2 ring-[#d580ff]' : ''}
                    onClick={() => {
                      setPerspective?.(option)
                      insertPreset(option, 'perspective')
                    }}
                  >
                    {option}
                  </Button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        )}

        {Object.entries(PRESETS).map(([key, preset]) => (
          <Popover key={key}>
            <PopoverTrigger asChild>
              <Button variant="ghost" size="icon" className="hover:bg-white/10">
                <preset.icon className="w-5 h-5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-48 p-2">
              <div className="grid grid-cols-2 gap-2">
                {preset.options.map(option => (
                  <Button
                    key={option}
                    variant="outline"
                    size="sm"
                    onClick={() => insertPreset(option, key as any)}
                  >
                    {option}
                  </Button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        ))}

        <Button
          variant="ghost"
          size="sm"
          className="hover:bg-white/10"
          onClick={() => onOpenTwoDEditor?.()}
        >
          2D素材编辑器
        </Button>

        {/* 3D场景按钮 (仅在3D模式下显示) */}
        {!is2DMode && (
          <Button variant="ghost" size="sm" className="hover:bg-white/10" onClick={() => onOpenThreeTest?.()}>
            3D场景
          </Button>
        )}
      </div>
    </div>
  )
}
