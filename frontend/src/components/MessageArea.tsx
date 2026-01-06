import { Message } from '@/app/providers'
import { Download } from 'lucide-react'
import { formatWaitTime } from '@/lib/api'

interface QueueInfo {
  position: number
  estimatedWait: number
  runningCount: number
  waitingCount: number
}

interface BottomActionsProps {
  lastAssistantWithImages?: { images: string[] } | null
  lastUserPrompt?: string
  onEdit?: () => void
  onRegenerate?: () => void
}

interface MessageAreaProps {
  messages: Message[]
  scrollContainerRef: React.RefObject<HTMLDivElement>
  hoveredImage: string | null
  setHoveredImage: (url: string | null) => void
  handleImageClick: (url: string) => void
  downloadImage: (url: string) => void
  isLoading?: boolean
  showComplianceMsg?: boolean
  bottomActions?: BottomActionsProps
  queueInfo?: QueueInfo | null
  onCancelJob?: () => void
  customContent?: React.ReactNode
}

export default function MessageArea({ 
  messages, 
  scrollContainerRef, 
  hoveredImage, 
  setHoveredImage, 
  handleImageClick, 
  downloadImage, 
  isLoading = false, 
  showComplianceMsg = false, 
  bottomActions,
  queueInfo,
  onCancelJob,
  customContent
}: MessageAreaProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4" ref={scrollContainerRef} data-scroll-root>
      <div className="space-y-4">
        {showComplianceMsg && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-center text-sm text-red-600">输入内容违规，请重新描述你的需求</div>
        )}
        {messages.length === 0 && !isLoading && (
          <div className="text-center text-muted-foreground">
            <p>Joy IP, 创意无限</p>
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`p-3 rounded-lg max-w-[80%] ${msg.type === 'user' ? 'bg-primary text-primary-foreground' : 'bg-transparent'}`}>
              <p>{msg.content}</p>
              {msg.images && msg.images.length > 0 && (
                <div className="mt-2 grid grid-cols-2 gap-2">
                  {msg.images.map((img, index) => (
                    <div
                      key={index}
                      className="relative group cursor-pointer"
                      onMouseEnter={() => setHoveredImage(img)}
                      onMouseLeave={() => setHoveredImage(null)}
                      onClick={() => handleImageClick(img)}
                    >
                      <img src={img} alt="Generated Image" className="rounded-lg" />
                      {hoveredImage === img && (
                        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center rounded-lg">
                          <button
                            onClick={e => {
                              e.stopPropagation()
                              downloadImage(img)
                            }}
                            className="text-white p-2 bg-black bg-opacity-50 rounded-full hover:bg-opacity-75"
                          >
                            <Download className="w-5 h-5" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-right mt-1 opacity-50">{new Date(msg.timestamp).toLocaleTimeString()}</p>
            </div>
          </div>
        ))}
        {/* 队列等待状态显示 */}
        {isLoading && queueInfo && queueInfo.position > 0 && (
          <div className="my-4 p-4 bg-gradient-to-r from-purple-900/30 to-blue-900/30 border border-purple-500/30 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <span className="text-lg font-bold text-purple-300">{queueInfo.position}</span>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">排队等待中</h3>
                  <p className="text-xs text-gray-400">
                    前面还有 <span className="text-purple-300 font-medium">{queueInfo.position}</span> 个任务，
                    预计等待 <span className="text-purple-300 font-medium">{formatWaitTime(queueInfo.estimatedWait)}</span>
                  </p>
                </div>
              </div>
              {onCancelJob && (
                <button
                  onClick={onCancelJob}
                  className="px-3 py-1.5 text-xs text-gray-300 hover:text-white bg-gray-700/50 hover:bg-gray-600/50 rounded transition-colors"
                >
                  取消排队
                </button>
              )}
            </div>
            {/* 进度条动画 */}
            <div className="mt-3 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full animate-pulse" style={{ width: '30%' }} />
            </div>
          </div>
        )}
        {/* 自定义内容区域（分析预览等） */}
        {customContent}
        {/* 生成中骨架：放在对话底部以贴近即将出现的图片 */}
        {isLoading && (!queueInfo || queueInfo.position === 0) && (
          <div className="my-4">
            <h3 className="text-sm text-muted-foreground mb-2">正在生成</h3>
            <div className="grid grid-cols-4 gap-4">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-40 rounded-md bg-gradient-to-br from-purple-300/40 to-purple-500/40 animate-pulse" />
              ))}
            </div>
          </div>
        )}
        {/* 图片区域下的操作按钮：随内容滚动 */}
        {bottomActions?.lastAssistantWithImages && (
          <div className="px-4 pb-2 flex gap-2 -mt-2">
            <button
              className="bg-primary text-primary-foreground rounded px-3 py-2 transition-colors duration-200 hover:bg-secondary hover:text-secondary-foreground"
              onClick={bottomActions.onEdit}
            >
              重新编辑
            </button>
            <button
              className="bg-primary text-primary-foreground rounded px-3 py-2 transition-colors duration-200 hover:bg-secondary hover:text-secondary-foreground"
              onClick={bottomActions.onRegenerate}
            >
              再次生成
            </button>
          </div>
        )}
      </div>
    </div>
  )
}