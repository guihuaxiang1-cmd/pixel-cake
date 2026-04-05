import React, { useState, useRef, useCallback } from 'react'

interface BeforeAfterProps {
  original: string
  result: string
}

export default function BeforeAfter({ original, result }: BeforeAfterProps) {
  const [splitX, setSplitX] = useState(50)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMove = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const x = ((clientX - rect.left) / rect.width) * 100
      setSplitX(Math.max(2, Math.min(98, x)))
    },
    []
  )

  const handleMouseDown = () => setIsDragging(true)

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) handleMove(e.clientX)
  }

  const handleMouseUp = () => setIsDragging(false)

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex items-center justify-center relative select-none"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <div className="relative max-w-full max-h-full" style={{ maxWidth: '90%', maxHeight: '90%' }}>
        {/* 修图后 */}
        <img
          src={result}
          alt="修图后"
          className="block max-w-full max-h-[calc(100vh-120px)] object-contain"
          draggable={false}
        />

        {/* 修图前（裁剪） */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${splitX}%` }}
        >
          <img
            src={original}
            alt="修图前"
            className="block max-h-[calc(100vh-120px)] object-contain"
            style={{
              width: containerRef.current
                ? containerRef.current.querySelector('img')?.offsetWidth
                : 'auto',
            }}
            draggable={false}
          />
        </div>

        {/* 分隔线 */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
          style={{ left: `${splitX}%`, transform: 'translateX(-50%)' }}
          onMouseDown={handleMouseDown}
        >
          {/* 拖拽手柄 */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white shadow-xl flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#333" strokeWidth="2">
              <path d="M8 6l-4 6 4 6M16 6l4 6-4 6" />
            </svg>
          </div>
        </div>

        {/* 标签 */}
        <div className="absolute top-3 left-3 px-2 py-1 bg-dark-950/70 rounded text-xs text-dark-200">
          原图
        </div>
        <div className="absolute top-3 right-3 px-2 py-1 bg-dark-950/70 rounded text-xs text-cake-300">
          AI修图
        </div>
      </div>
    </div>
  )
}
