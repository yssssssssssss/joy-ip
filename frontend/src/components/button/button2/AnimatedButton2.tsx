"use client"

import React from 'react'
import './button2.css'

interface AnimatedButton2Props {
  children: React.ReactNode
  onClick?: () => void
  className?: string
}

export default function AnimatedButton2({ children, onClick, className = '' }: AnimatedButton2Props) {
  return (
    <button type="button" className={`button ${className}`} onClick={onClick}>
      <span>{children}</span>
    </button>
  )
}
