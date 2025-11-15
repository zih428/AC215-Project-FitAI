'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  MessageCircle, 
  Dumbbell, 
  User
} from 'lucide-react'

const navigation = [
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'AI Coach', href: '/ai-coach', icon: MessageCircle },
  { name: 'Workouts', href: '/workouts', icon: Dumbbell },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Logo Section */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-2 mb-2">
          <div className="w-8 h-8 bg-primary-500 rounded flex items-center justify-center">
            <Dumbbell className="w-5 h-5 text-white rotate-45" />
          </div>
          <span className="text-xl font-bold text-gray-900">FitAI</span>
        </div>
        <p className="text-xs text-gray-500">Smart Fitness Platform</p>
      </div>

      {/* Navigation */}
      <div className="flex-1 p-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 px-3">
          NAVIGATION
        </p>
        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`
                  flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span>{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {/* User Profile Section */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
            <span className="text-white font-semibold text-sm">U</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              Fitness User
            </p>
            <p className="text-xs text-gray-500 truncate">
              Stay strong & healthy
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
