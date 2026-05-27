import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { MessageCircle } from 'lucide-react'
import AgentChatPanel from './AgentChatPanel'

export default function AgentFloatingButton() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button
        className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-lg"
        onClick={() => setOpen(!open)}
      >
        <MessageCircle size={24} />
      </Button>
      {open && <AgentChatPanel onClose={() => setOpen(false)} />}
    </>
  )
}