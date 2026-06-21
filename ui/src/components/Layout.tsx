import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard,
  Settings,
  Bot,
  PlayCircle,
  Ticket,
  Lock,
  LogOut,
  Menu,
  X,
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { path: '/projects', label: 'Projects', icon: LayoutDashboard },
  { path: '/secrets', label: 'Secrets', icon: Lock },
  { path: '/providers', label: 'Providers', icon: Settings },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/executions', label: 'Executions', icon: PlayCircle },
  { path: '/tickets', label: 'Tickets', icon: Ticket },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900 text-white">
        <div className="p-4 font-bold text-xl">Code Issues Solver</div>
        <nav className="flex-1 px-2 space-y-1">
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.path)
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition ${
                  active ? 'bg-primary-600' : 'hover:bg-slate-800'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <div className="text-sm text-slate-400 mb-2">{user?.username}</div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300"
          >
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-slate-900 text-white flex items-center justify-between px-4 py-3">
        <span className="font-bold">CIS</span>
        <button onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-slate-900 text-white pt-16 px-4">
          <nav className="space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800"
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            ))}
            <button onClick={logout} className="flex items-center gap-3 px-3 py-2 text-red-400">
              <LogOut className="w-5 h-5" /> Logout
            </button>
          </nav>
        </div>
      )}

      <main className="flex-1 p-6 md:p-8 pt-20 md:pt-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}