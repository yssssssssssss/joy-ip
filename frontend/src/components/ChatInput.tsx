import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Send, Smile, Activity, Palette, Eye } from 'lucide-react'

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
  // 新增: 2D/3D模式切换
  generationMode?: '2D' | '3D'
  setGenerationMode?: (mode: '2D' | '3D') => void
  // 新增: 视角选择
  perspective?: string
  setPerspective?: (perspective: string) => void
}

export default function ChatInput({ 
  input, 
  setInput, 
  handleSend, 
  isLoading, 
  insertPreset, 
  variant = 'bottom', 
  onOpenThreeTest,
  generationMode = '3D',
  setGenerationMode,
  perspective = '正视角',
  setPerspective
}: ChatInputProps) {
  const isCenter = variant === 'center'
  const is2DMode = generationMode === '2D'

  // Tab切换组件
  const TabSwitch = () => (
    <div className="flex items-center gap-1 bg-[#2b2d33] rounded-[12px] p-1">
      <button
        onClick={() => setGenerationMode?.('2D')}
        className={`px-4 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
          is2DMode 
            ? 'bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white shadow-lg' 
            : 'text-gray-400 hover:text-white hover:bg-white/10'
        }`}
      >
        2D素材生成
      </button>
      <button
        onClick={() => setGenerationMode?.('3D')}
        className={`px-4 py-2 rounded-[10px] text-sm font-medium transition-all duration-200 ${
          !is2DMode 
            ? 'bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white shadow-lg' 
            : 'text-gray-400 hover:text-white hover:bg-white/10'
        }`}
      >
        3D素材生成
      </button>
    </div>
  )

  // 视角选择按钮 (仅在2D模式下显示)
  const PerspectiveButton = () => {
    if (!is2DMode) return null
    
    return (
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="h-[40px] px-4 rounded-[10px] bg-[#5a4b7a] text-[#e0d4ff] border-0 hover:bg-[#6b5a8a]"
          >
            <Eye className="w-5 h-5 mr-2" />
            {perspective}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-40 p-2 bg-[#1b1d21] text-white border-white/20">
          <div className="grid grid-cols-1 gap-2">
            {PERSPECTIVE_PRESET.perspective.options.map(option => (
              <Button
                key={option}
                variant="outline"
                size="sm"
                className={`bg-black/30 text-white border-white/20 hover:bg-black/40 ${
                  perspective === option ? 'ring-2 ring-[#d580ff]' : ''
                }`}
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
    )
  }

  if (isCenter) {
    return (
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-[915px] rounded-[30px] border border-white/15 bg-[#202126] shadow-[0_8px_24px_rgba(0,0,0,0.35)]">
          {/* Tab切换 + 头部标题 */}
          <div className="px-6 pt-5 pb-2">
            <div className="flex items-center justify-between mb-4">
              <TabSwitch />
            </div>
            <div className="flex items-center gap-3">
              <div className="bg-clip-text text-transparent bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-[25px] mt-2 mb-2 font-bold leading-[28px]">
                {is2DMode ? '2D素材生成' : 'JOY生成'}
              </div>
              <div className="text-[20px] leading-[28px] text-[#8b8fa3] mt-2 mb-2">
                {is2DMode ? '描述你想要生成的2D素材' : '描述你想要生成的JOY'}
              </div>
            </div>
          </div>

          {/* 输入框 */}
          <div className="px-6 pb-2 mb-2">
            <div className="flex items-center">
              <div className="flex-1">
                <Input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder={is2DMode ? "描述你想要生成的2D素材" : "描述你想要生成的JOY"}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                  disabled={isLoading}
                  className="h-[50px] pr-10 bg-[#2b2d33] text-white border-0 placeholder:text-gray-500 rounded-[12px] focus:ring-2 focus:ring-primary"
                />
              </div>
              {isLoading && (
                <div className="ml-2">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                </div>
              )}
            </div>
          </div>

          {/* 预设按钮 + 3D场景 + 发送 */}
          <div className="px-6 pb-5">
            <div className="flex items-center gap-2 flex-wrap">
              {/* 2D模式下显示视角按钮 */}
              <PerspectiveButton />
              
              {/* 原有的预设按钮 */}
              {Object.entries(PRESETS).map(([key, preset]) => (
                <Popover key={key}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-[40px] px-4 rounded-[10px] bg-[#424158] text-[#b7affe] border-0 hover:bg-[#4a4964]"
                    >
                      <img
                        src={key === 'expression' ? '/icons/head.svg' : key === 'action' ? '/icons/body.svg' : '/icons/style.svg'}
                        alt=""
                        className="w-6 h-6 mr-2"
                      />
                      {preset.label}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-60 p-2 bg-[#1b1d21] text-white border-white/20">
                    <div className="grid grid-cols-2 gap-2">
                      {preset.options.map(option => (
                        <Button
                          key={option}
                          variant="outline"
                          size="sm"
                          className="bg-black/30 text-white border-white/20 hover:bg-black/40"
                          onClick={() => insertPreset(option, key as any)}
                        >
                          {option}
                        </Button>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>
              ))}
              
              {/* 3D场景按钮 (仅在3D模式下显示) */}
              {!is2DMode && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-[40px] px-4 rounded-[10px] bg-[#424158] text-[#b7affe] border-0 hover:bg-[#4a4964]"
                  onClick={() => onOpenThreeTest?.()}
                >
                  3D场景
                </Button>
              )}
              
              <div className="ml-auto">
                <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="rounded-full h-[50px] w-[50px] bg-gradient-to-r from-[#d580ff] to-[#a6ccfd] text-white hover:opacity-90 hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed">
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
