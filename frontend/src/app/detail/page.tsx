"use client"

import { Suspense } from 'react'
import DetailView from '@/components/DetailView'

export default function DetailPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen bg-[#1E202C] text-white">加载中...</div>}>
      <DetailView />
    </Suspense>
  )
}

