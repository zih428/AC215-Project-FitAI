'use client'

import { Dumbbell, Play, Clock } from 'lucide-react'

export default function Workouts() {
  return (
    <div className="flex flex-col h-full">
      <div className="p-8 border-b border-gray-200 bg-white">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Workouts</h1>
        <p className="text-gray-600">Browse and start your workout sessions</p>
      </div>

      <div className="p-8 bg-gray-50 flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[ 
            { title: 'Upper Body Strength', duration: '45 min' },
            { title: 'Lower Body Power', duration: '40 min' },
            { title: 'Cardio Endurance', duration: '30 min' },
          ].map((w) => (
            <div key={w.title} className="bg-white border border-gray-200 rounded-xl p-5">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <Dumbbell className="w-6 h-6 text-primary-600" />
                </div>
                <h3 className="font-semibold text-gray-900">{w.title}</h3>
              </div>
              <div className="flex items-center justify-between text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{w.duration}</span>
                </div>
                <button className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-primary-500 text-white hover:bg-primary-600">
                  <Play className="w-4 h-4" />
                  <span>Start</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}


