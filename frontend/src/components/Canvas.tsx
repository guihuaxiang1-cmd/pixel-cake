import React, { useRef, useEffect, useState, useCallback } from 'react'
import { ImageInfo, Tool, AIFeature } from '../App'

interface CanvasProps {
  image: ImageInfo | null
  resultUrl: string | null
  tool: Tool
  brushSize: number
  zoom: number
  onZoomChange?: (z: number) => void
  isProcessing: boolean
  onAIFeature: (feature: AIFeature) => void
  onMaskInpaint: (maskBlob: Blob) => void
  onClearTool: () => void
  onError: (msg: string) => void
}

export default function Canvas({
  image,
  resultUrl,
  tool,
  brushSize,
  zoom,
  onZoomChange,
  isProcessing,
  onAIFeature,
  onMaskInpaint,
  onClearTool,
  onError,
}: CanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const overlayRef = useRef<HTMLCanvasElement>(null) // 画笔覆盖层
  const [isDrawing, setIsDrawing] = useState(false)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [panStart, setPanStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const [hasDrawn, setHasDrawn] = useState(false)
  const [imgLoaded, setImgLoaded] = useState(false)
  // 裁剪状态
  const [cropStart, setCropStart] = useState<{ x: number; y: number } | null>(null)
  const [cropRect, setCropRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const [isCropping, setIsCropping] = useState(false)

  // 加载图片到底层画布
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

  // 同步覆盖层尺寸
  useEffect(() => {
    if (!canvasRef.current || !overlayRef.current) return
    overlayRef.current.width = canvasRef.current.width
    overlayRef.current.height = canvasRef.current.height
  }, [imgLoaded])

  // 切换工具时清空画笔/裁剪
  useEffect(() => {
    if (tool !== 'brush' && tool !== 'eraser' && tool !== 'inpaint') {
      clearOverlay()
    }
    if (tool !== 'crop') {
      setCropRect(null)
      setCropStart(null)
      setIsCropping(false)
    }
  }, [tool])

  // 计算鼠标在画布上的坐标
  const getCanvasCoords = useCallback(
    (e: React.MouseEvent) => {
      if (!containerRef.current || !overlayRef.current) return null
      const rect = containerRef.current.getBoundingClientRect()
      const scaleX = overlayRef.current.width / (rect.width)
      const scaleY = overlayRef.current.height / (rect.height)
      const x = (e.clientX - rect.left - pan.x) / zoom
      const y = (e.clientY - rect.top - pan.y) / zoom
      return { x: Math.round(x), y: Math.round(y) }
    },
    [pan, zoom]
  )

  const clearOverlay = useCallback(() => {
    if (!overlayRef.current) return
    const ctx = overlayRef.current.getContext('2d')!
    ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height)
    setHasDrawn(false)
  }, [])

  // 生成 mask 图片（白底黑画笔区域）
  const generateMaskBlob = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      if (!overlayRef.current) { resolve(null); return }
      const src = overlayRef.current
      // 创建离屏 canvas 生成二值 mask
      const maskCanvas = document.createElement('canvas')
      maskCanvas.width = src.width
      maskCanvas.height = src.height
      const ctx = maskCanvas.getContext('2d')!
      // 黑色背景
      ctx.fillStyle = '#000000'
      ctx.fillRect(0, 0, maskCanvas.width, maskCanvas.height)
      // 把覆盖层中非透明区域画成白色
      const srcData = src.getContext('2d')!.getImageData(0, 0, src.width, src.height)
      const maskData = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
      for (let i = 0; i < srcData.data.length; i += 4) {
        if (srcData.data[i + 3] > 0) {
          maskData.data[i] = 255     // R
          maskData.data[i + 1] = 255 // G
          maskData.data[i + 2] = 255 // B
          maskData.data[i + 3] = 255 // A
        }
      }
      ctx.putImageData(maskData, 0, 0)
      maskCanvas.toBlob((blob) => resolve(blob), 'image/png')
    })
  }, [])

  // 提交画笔 mask 做 inpaint
  const handleSubmitInpaint = useCallback(async () => {
    if (!image || !hasDrawn) return
    const maskBlob = await generateMaskBlob()
    if (maskBlob) {
      onMaskInpaint(maskBlob)
      clearOverlay()
    }
  }, [image, hasDrawn, generateMaskBlob, onMaskInpaint, clearOverlay])

  // 鼠标事件
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!image) return

      // 平移
      if (tool === 'hand' || e.button === 1) {
        setPanStart({ x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y })
        return
      }

      // AI 识人 - 一键去路人
      if (tool === 'auto-person') {
        onAIFeature('remove-person')
        return
      }

      // AI 识天 - 一键换天空
      if (tool === 'auto-sky') {
        onAIFeature('sky-replace')
        return
      }

      // 裁剪 - 开始选择区域
      if (tool === 'crop') {
        const coords = getCanvasCoords(e)
        if (coords) {
          setCropStart(coords)
          setCropRect(null)
          setIsCropping(true)
        }
        return
      }

      // 画笔 / 橡皮 / AI修复
      if (tool === 'brush' || tool === 'eraser' || tool === 'inpaint') {
        setIsDrawing(true)
        const coords = getCanvasCoords(e)
        if (coords) {
          drawBrush(coords)
          setHasDrawn(true)
        }
      }
    },
    [image, tool, pan, getCanvasCoords, onAIFeature, onError]
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

      // 裁剪拖拽
      if (isCropping && cropStart) {
        const coords = getCanvasCoords(e)
        if (coords) {
          setCropRect({
            x: Math.min(cropStart.x, coords.x),
            y: Math.min(cropStart.y, coords.y),
            w: Math.abs(coords.x - cropStart.x),
            h: Math.abs(coords.y - cropStart.y),
          })
        }
        return
      }

      if (!isDrawing) return
      const coords = getCanvasCoords(e)
      if (coords) {
        drawBrush(coords)
      }
    },
    [isDrawing, panStart, getCanvasCoords]
  )

  const handleMouseUp = useCallback(() => {
    setIsDrawing(false)
    setPanStart(null)
    if (isCropping) {
      setIsCropping(false)
    }
  }, [isCropping])

  // 在覆盖层上绘制
  const drawBrush = useCallback(
    (coords: { x: number; y: number }) => {
      if (!overlayRef.current) return
      const ctx = overlayRef.current.getContext('2d')!
      ctx.globalCompositeOperation = tool === 'eraser' ? 'destination-out' : 'source-over'
      ctx.beginPath()
      ctx.arc(coords.x, coords.y, brushSize / 2, 0, Math.PI * 2)
      if (tool === 'eraser') {
        ctx.fillStyle = 'rgba(0,0,0,1)'
      } else {
        ctx.fillStyle = 'rgba(255, 69, 100, 0.5)'
      }
      ctx.fill()
    },
    [tool, brushSize]
  )

  // 滚轮缩放
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault()
      if (!onZoomChange) return
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      const newZoom = Math.max(0.1, Math.min(5, zoom + delta))
      onZoomChange(Math.round(newZoom * 100) / 100)
    },
    [zoom, onZoomChange]
  )

  // 应用裁剪
  const applyCrop = useCallback(async () => {
    if (!canvasRef.current || !cropRect || cropRect.w < 10 || cropRect.h < 10 || !image) return
    const src = canvasRef.current
    const cropped = document.createElement('canvas')
    cropped.width = cropRect.w
    cropped.height = cropRect.h
    const ctx = cropped.getContext('2d')!
    ctx.drawImage(src, cropRect.x, cropRect.y, cropRect.w, cropRect.h, 0, 0, cropRect.w, cropRect.h)

    cropped.toBlob(async (blob) => {
      if (!blob) return
      try {
        // Upload cropped image as new image
        const fd = new FormData()
        fd.append('file', blob, 'cropped.png')
        const res = await fetch('/api/upload', { method: 'POST', body: fd })
        if (res.ok) {
          const data = await res.json()
          // Update canvas with cropped image
          const url = URL.createObjectURL(blob)
          const img = new Image()
          img.onload = () => {
            if (canvasRef.current) {
              canvasRef.current.width = img.width
              canvasRef.current.height = img.height
              canvasRef.current.getContext('2d')!.drawImage(img, 0, 0)
            }
            if (overlayRef.current) {
              overlayRef.current.width = img.width
              overlayRef.current.height = img.height
            }
            setCropRect(null)
            setCropStart(null)
          }
          img.src = url
        }
      } catch (err) {
        console.error('Crop failed:', err)
      }
    }, 'image/png')
  }, [cropRect, image])

  const cancelCrop = useCallback(() => {
    setCropRect(null)
    setCropStart(null)
  }, [])

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

  const showInpaintButton = hasDrawn && (tool === 'brush' || tool === 'inpaint' || tool === 'eraser')
  const isAIClickTool = tool === 'auto-person' || tool === 'auto-sky'

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex items-center justify-center overflow-hidden relative"
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
          className="relative"
        >
          {/* 底层：图片 */}
          <canvas
            ref={canvasRef}
            className="max-w-none shadow-2xl rounded-sm block"
            style={{ imageRendering: zoom > 2 ? 'pixelated' : 'auto' }}
          />
          {/* 上层：画笔覆盖层 */}
          <canvas
            ref={overlayRef}
            className="absolute top-0 left-0 max-w-none"
            style={{
              imageRendering: zoom > 2 ? 'pixelated' : 'auto',
              pointerEvents: 'none',
            }}
          />
        </div>
      ) : null}

      {/* 画笔/修复模式：提交按钮 */}
      {showInpaintButton && !isProcessing && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 flex gap-3 animate-fadeIn">
          <button
            onClick={handleSubmitInpaint}
            className="px-6 py-2.5 rounded-xl bg-cake-600 hover:bg-cake-500 text-white font-medium text-sm shadow-lg shadow-cake-600/30 transition-all hover:scale-105 flex items-center gap-2"
          >
            ✨ AI 修复选区
          </button>
          <button
            onClick={clearOverlay}
            className="px-4 py-2.5 rounded-xl bg-dark-700 hover:bg-dark-600 text-dark-200 text-sm shadow-lg transition-all"
          >
            清除画笔
          </button>
        </div>
      )}

      {/* AI 一键工具：操作提示 */}
      {isAIClickTool && image && !isProcessing && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 animate-fadeIn">
          <div className="px-5 py-2.5 rounded-xl bg-dark-800/90 text-dark-200 text-sm shadow-lg backdrop-blur-sm border border-dark-600">
            {tool === 'auto-person' && '👆 点击图片，AI 自动识别并去除路人'}
            {tool === 'auto-sky' && '👆 点击图片，AI 自动替换天空'}
          </div>
        </div>
      )}

      {/* 裁剪选区遮罩 */}
      {cropRect && tool === 'crop' && (
        <>
          {/* 半透明遮罩 */}
          <div className="absolute inset-0 pointer-events-none z-30" style={{
            background: `linear-gradient(to right, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.5) ${(cropRect.x * zoom + pan.x)}px, transparent ${(cropRect.x * zoom + pan.x)}px, transparent ${(cropRect.x + cropRect.w) * zoom + pan.x}px, rgba(0,0,0,0.5) ${(cropRect.x + cropRect.w) * zoom + pan.x}px)`,
          }} />
          {/* 选区边框 */}
          <div className="absolute pointer-events-none z-30 border-2 border-white shadow-lg"
            style={{
              left: `${cropRect.x * zoom + pan.x}px`,
              top: `${cropRect.y * zoom + pan.y}px`,
              width: `${cropRect.w * zoom}px`,
              height: `${cropRect.h * zoom}px`,
            }}
          >
            {/* 尺寸标注 */}
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-dark-950/80 rounded text-xs text-white whitespace-nowrap">
              {cropRect.w} × {cropRect.h}
            </div>
          </div>
          {/* 确认/取消按钮 */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 flex gap-3 animate-fadeIn">
            <button onClick={applyCrop}
              className="px-6 py-2.5 rounded-xl bg-green-600 hover:bg-green-500 text-white font-medium text-sm shadow-lg transition-all hover:scale-105">
              ✓ 确认裁剪
            </button>
            <button onClick={cancelCrop}
              className="px-4 py-2.5 rounded-xl bg-dark-700 hover:bg-dark-600 text-dark-200 text-sm shadow-lg transition-all">
              ✕ 取消
            </button>
          </div>
        </>
      )}

      {/* 裁剪模式提示 */}
      {tool === 'crop' && image && !cropRect && !isCropping && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 animate-fadeIn">
          <div className="px-5 py-2.5 rounded-xl bg-dark-800/90 text-dark-200 text-sm shadow-lg backdrop-blur-sm border border-dark-600">
            ✂️ 拖拽选择裁剪区域
          </div>
        </div>
      )}
    </div>
  )
}
