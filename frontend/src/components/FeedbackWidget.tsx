'use client'

import * as React from "react"
import { MessageSquare, X, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

export function FeedbackWidget() {
  const [isOpen, setIsOpen] = React.useState(false)
  const [message, setMessage] = React.useState("")
  const [contact, setContact] = React.useState("")
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [success, setSuccess] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return

    setIsSubmitting(true)
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, contact }),
      })
      const data = await res.json()
      if (data.success) {
        setSuccess(true)
        setTimeout(() => {
          setIsOpen(false)
          setSuccess(false)
          setMessage("")
          setContact("")
        }, 2000)
      } else {
        alert(data.error || "提交失败，请重试")
      }
    } catch (error) {
        console.error(error)
      alert("提交失败，请重试")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button 
            variant="outline"
            className="h-16 w-16 rounded-full shadow-xl border-2 border-primary/20 bg-white/80 backdrop-blur-sm hover:bg-white hover:border-primary transition-all duration-300"
            size="icon"
          >
            <MessageSquare className="h-8 w-8 text-primary" />
            <span className="sr-only">意见反馈</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0 mr-4 mb-2" align="end" side="top">
            <div className="flex items-center justify-between border-b px-4 py-3">
                <h4 className="font-semibold">意见反馈</h4>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsOpen(false)}>
                    <X className="h-4 w-4" />
                </Button>
            </div>
            <div className="p-4">
                {success ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center text-green-600">
                        <p className="text-lg font-medium">感谢您的反馈！</p>
                        <p className="text-sm text-gray-500">我们将不断改进产品。</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label htmlFor="feedback-message" className="text-sm font-medium">
                                您的建议 <span className="text-red-500">*</span>
                            </label>
                            <textarea
                                id="feedback-message"
                                className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                placeholder="请告诉我们需要改进的地方..."
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label htmlFor="feedback-contact" className="text-sm font-medium">
                                联系方式 (可选)
                            </label>
                            <Input
                                id="feedback-contact"
                                placeholder="ERP或者手机号"
                                value={contact}
                                onChange={(e) => setContact(e.target.value)}
                            />
                        </div>
                        <Button type="submit" className="w-full" disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            提交反馈
                        </Button>
                    </form>
                )}
            </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
