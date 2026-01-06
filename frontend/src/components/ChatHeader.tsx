import { Button } from '@/components/ui/button'
import { ImageIcon, Trash } from 'lucide-react'

interface ChatHeaderProps {
  clearChat: () => void
}

export default function ChatHeader({ clearChat }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between p-4">
      <div className="flex items-center gap-2">
        <ImageIcon className="w-6 h-6" />
        <h1 className="text-xl font-bold">Joy IP 3D 图片生成</h1>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="bg-transparent hover:bg-transparent" onClick={clearChat}>
          <Trash className="w-4 h-4 mr-2" />
          清除
        </Button>
      </div>
    </div>
  )
}