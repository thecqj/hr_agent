import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import AgentFloatingButton from '../agents/AgentFloatingButton'

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto py-6 px-4">
        <Outlet />
      </main>
      <AgentFloatingButton />
    </div>
  )
}