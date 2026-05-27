import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function AgentChatPanel({ onClose }: { onClose: () => void }) {
  return (
    <Card className="fixed bottom-24 right-6 w-80 h-96 p-4 flex flex-col shadow-xl">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-semibold">AI 助手</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
      </div>
      <div className="flex-1 overflow-y-auto border rounded p-2 mb-2">
        {/* 聊天消息区域 */}
      </div>
      <div className="flex gap-2">
        <Input placeholder="输入问题..." />
        <Button size="sm">发送</Button>
      </div>
    </Card>
  )
}