'use client'

import { User } from 'lucide-react'

export default function Profile() {
  return (
    <div className="flex flex-col h-full">
      <div className="p-8 border-b border-gray-200 bg-white">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Profile</h1>
        <p className="text-gray-600">Manage your account and fitness preferences</p>
      </div>

      <div className="p-8 bg-gray-50 flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center space-x-4 mb-6">
            <div className="w-14 h-14 bg-blue-500 rounded-full flex items-center justify-center">
              <User className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Fitness User</h2>
              <p className="text-sm text-gray-600">Stay strong & healthy</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Goal</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="Lose weight" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Weekly availability</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500" placeholder="3 sessions" />
            </div>
          </div>
          <div className="mt-6">
            <button className="px-4 py-2 rounded-lg bg-primary-500 text-white hover:bg-primary-600">
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


