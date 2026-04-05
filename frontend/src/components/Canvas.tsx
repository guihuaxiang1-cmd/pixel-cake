import React, { useRef, useEffect, useState, useCallback } from 'react'
import { ImageInfo, Tool } from '../App'

interface CanvasProps {
  image: ImageInfo | null
  resultUrl: string | null
  tool: Tool
  brushSize: number
  zoom: number
  isProcessing: boolean
}

export default function Canvas({ image, resultUrl, tool, brushSize, zoom, isProcessing }: CanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [panStart, setPanStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const [maskPoints, setMaskPoints] = useState<Array<{ x: number; y: number }>>([])
  const [imgLoaded, setImgLoaded] = useState(false)

  // 加载图片到画布
  useEffect(() => {
    if (!image || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')!
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      canvas.width = img.width
      canvas.height = img.height
      ctx.drawImage(img, 0, 0)
      setImgLoaded(true)
    }
    img.src = resultUrl || image.url
  }, [image, resultUrl])

  // 计算鼠标在画布上的坐标
  const getCanvasCoords = useCallback(
    (e: React.MouseEvent) => {
      if (!canvasRef.current || !containerRef.current) return null
      const rect = containerRef.current.getBoundingClientRect()
      const x = (e.clientX - rect.left - pan.x) / zoom
      const y = (e.clientY - rect.top - pan.y) / zoom
      return { x: Math.round(x), y: Math.round(y) }
    },
    [pan, zoom]
  )

  // 鼠标事件
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!image) return

      if (tool === 'hand' || e.button === 1) {
        setPanStart({ x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y })
        return
      }

      if (tool === 'brush' || tool === 'eraser') {
        setIsDrawing(true)
        const coords = getCanvasCoords(e)
        if (coords) {
          setMaskPoints([coords])
          drawBrush(coords)
        }
      }
    },
    [image, tool, pan, getCanvasCoords]
  )

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (panStart) {
        setPan({
          x: panStart.panX + (e.clientX - panStart.x),
          y: panStart.panY + (e.clientY - panStart.y),
        })
        return
      }

      if (!isDrawing) return
      const coords = getCanvasCoords(e)
      if (coords) {
        setMaskPoints(prev => [...prev, coords])
        drawBrush(coords)
      }
    },
    [isDrawing, panStart, getCanvasCoords]
  )

  const handleMouseUp = useCallback(() => {
    setIsDrawing(false)
    setPanStart(null)
  }, [])

  // 绘制画笔
  const drawBrush = useCallback(
    (coords: { x: number; y: number }) => {
      if (!canvasRef.current) return
      const ctx = canvasRef.current.getContext('2d')!
      ctx.globalCompositeOperation = tool === 'eraser' ? 'destination-out' : 'source-over'
      ctx.beginPath()
      ctx.arc(coords.x, coords.y, brushSize / 2, 0, Math.PI * 2)
      ctx.fillStyle = tool === 'eraser' ? 'rgba(0,0,0,1)' : 'rgba(255, 69, 100, 0.5)'
      ctx.fill()
    },
    [tool, brushSize]
  )

  // 滚轮缩放
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault()
      // 缩放由父组件控制
    },
    []
  )

  const cursorMap: Record<Tool, string> = {
    select: 'default',
    hand: 'grab',
    brush: 'crosshair',
    eraser: 'crosshair',
    'auto-person': 'pointer',
    'auto-sky': 'pointer',
    inpaint: 'crosshair',
    crop: 'crosshair',
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex items-center justify-center overflow-hidden"
      style={{ cursor: cursorMap[tool] || 'default' }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {image ? (
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center',
            transition: panStart ? 'none' : 'transform 0.1s ease-out',
          }}
        >
          <canvas
            ref={canvasRef}
            className="max-w-none shadow-2xl rounded-sm"
            style={{ imageRendering: zoom > 2 ? 'pixelated' : 'auto' }}
          />
        </div>
      ) : null}
    </div>
  )
}
