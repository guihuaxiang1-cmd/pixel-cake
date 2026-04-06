import React, { useState, useCallback, useRef, useEffect } from 'react'
import Toolbar from './components/Toolbar'
import Sidebar from './components/Sidebar'
import Canvas from './components/Canvas'
import BeforeAfter from './components/BeforeAfter'
import BatchProcess from './components/BatchProcess'
import Header from './components/Header'

// ─── 类型定义 ───

export interface ImageInfo {
  imageId: string
  filename: string
  width: number
  height: number
  url: string
}

export interface MaskInfo {
  maskId: string
  points: Array<{ x: number; y: number; label: number }>
}

export type Tool =
  | 'select'
  | 'brush'
  | 'eraser'
  | 'auto-person'
  | 'auto-sky'
  | 'inpaint'
  | 'crop'
  | 'hand'

export type AIFeature =
  | 'remove-person'
  | 'remove-tattoo'
  | 'remove-stubble'
  | 'remove-flaw'
  | 'relight'
  | 'fill-grass'
  | 'sky-replace'
  | 'skin-smooth'
  | 'teeth-whiten'
  | 'color-match'

export type AdjustMode = 'basic' | 'color' | 'detail' | 'filter' | 'ai'

export interface AdjustParams {
  brightness: number
  contrast: number
  saturation: number
  warmth: number
  sharpness: number
  denoise: number
  highlights: number
  shadows: number
  vibrance: number
  clarity: number
  tint: number
}

export const defaultParams: AdjustParams = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  warmth: 0,
  sharpness: 0,
  denoise: 0,
  highlights: 0,
  shadows: 0,
  vibrance: 0,
  clarity: 0,
  tint: 0,
}

export default function App() {
  // 状态
  const [image, setImage] = useState<ImageInfo | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [tool, setTool] = useState<Tool>('select')
  const [adjustMode, setAdjustMode] = useState<AdjustMode>('basic')
  const [params, setParams] = useState<AdjustParams>(defaultParams)
  const [brushSize, setBrushSize] = useState(20)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showBeforeAfter, setShowBeforeAfter] = useState(false)
  const [showBatch, setShowBatch] = useState(false)
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [zoom, setZoom] = useState(1)
  const [selectedFilter, setSelectedFilter] = useState<string | null>(null)

  // ─── 上传图片 ───

  const handleUpload = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()

    const imgInfo: ImageInfo = {
      imageId: data.image_id,
      filename: data.filename,
      width: data.width,
      height: data.height,
      url: `/api/image/${data.image_id}`,
    }
    setImage(imgInfo)
    setResultUrl(null)
    setHistory([imgInfo.url])
    setHistoryIndex(0)
    setParams(defaultParams)
    setSelectedFilter(null)
  }, [])

  // ─── AI 操作 ───

  const handleAIFeature = useCallback(async (feature: AIFeature) => {
    if (!image) return
    setIsProcessing(true)

    try {
      let blob: Blob | null = null

      switch (feature) {
        case 'remove-person':
        case 'remove-flaw': {
          // 自动检测 + inpaint
          const mode = feature === 'remove-person' ? 'person' : 'all'
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode }),
          })
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId }),
            })
            blob = await inpRes.blob()
          }
          break
        }
        case 'remove-tattoo':
        case 'remove-stubble': {
          // 皮肤区域检测 + inpaint
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'skin' }),
          })
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId }),
            })
            blob = await inpRes.blob()
          }
          break
        }
        case 'relight': {
          const fd = new FormData()
          fd.append('image_id', image.imageId)
          fd.append('brightness', '0.3')
          fd.append('warmth', '0.1')
          const res = await fetch('/api/relight', { method: 'POST', body: fd })
          blob = await res.blob()
          break
        }
        case 'sky-replace': {
          const res = await fetch('/api/sky/replace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id: image.imageId, sky_type: 'sunset', blend_strength: 0.7 }),
          })
          blob = await res.blob()
          break
        }
        case 'fill-grass': {
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'ground' }),
          })
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId, fill_type: 'grass' }),
            })
            blob = await inpRes.blob()
          }
          break
        }
        case 'skin-smooth': {
          const res = await fetch('/api/enhance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_id: image.imageId,
              brightness: 0,
              contrast: 0,
              saturation: 0,
              warmth: 0,
              sharpness: 0,
              denoise: 0.4,
              skin_smooth: true,
            }),
          })
          blob = await res.blob()
          break
        }
        case 'color-match': {
          // AI追色：需要参考图，暂时用自动调色代替
          const res = await fetch('/api/enhance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_id: image.imageId,
              brightness: 0.05,
              contrast: 0.1,
              saturation: 0.08,
              warmth: 0.05,
              sharpness: 0.1,
              denoise: 0.1,
            }),
          })
          blob = await res.blob()
          break
        }
        case 'teeth-whiten': {
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'teeth' }),
          })
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId, fill_type: 'whiten' }),
            })
            blob = await inpRes.blob()
          }
          break
        }
      }

      if (blob) {
        const url = URL.createObjectURL(blob)
        setResultUrl(url)
        setHistory(prev => [...prev.slice(0, historyIndex + 1), url])
        setHistoryIndex(prev => prev + 1)
      }
    } catch (err) {
      console.error('AI处理失败:', err)
    } finally {
      setIsProcessing(false)
    }
  }, [image, historyIndex])

  // ─── 调色 ───

  const handleAdjust = useCallback(async (newParams: Partial<AdjustParams>) => {
    if (!image) return
    const merged = { ...params, ...newParams }
    setParams(merged)

    try {
      const res = await fetch('/api/enhance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: image.imageId,
          brightness: merged.brightness,
          contrast: merged.contrast,
          saturation: merged.saturation,
          warmth: merged.warmth,
          sharpness: merged.sharpness,
          denoise: merged.denoise,
        }),
      })
      const blob = await res.blob()
      setResultUrl(URL.createObjectURL(blob))
    } catch (err) {
      console.error('调色失败:', err)
    }
  }, [image, params])

  // ─── 滤镜 ───

  const handleFilter = useCallback(async (filterName: string) => {
    if (!image) return
    setSelectedFilter(filterName)
    setIsProcessing(true)
    try {
      const res = await fetch('/api/enhance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: image.imageId,
          filter: filterName,
          brightness: 0,
          contrast: 0,
          saturation: 0,
          warmth: 0,
          sharpness: 0,
          denoise: 0,
        }),
      })
      if (res.ok) {
        const blob = await res.blob()
        setResultUrl(URL.createObjectURL(blob))
      }
    } catch (err) {
      console.error('滤镜失败:', err)
    } finally {
      setIsProcessing(false)
    }
  }, [image])

  // ─── 撤销/重做 ───

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      setHistoryIndex(prev => prev - 1)
      setResultUrl(history[historyIndex - 1])
    }
  }, [historyIndex, history])

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(prev => prev + 1)
      setResultUrl(history[historyIndex + 1])
    }
  }, [historyIndex, history])

  // ─── 下载 ───

  const handleDownload = useCallback(() => {
    const url = resultUrl || image?.url
    if (!url) return
    const a = document.createElement('a')
    a.href = url
    a.download = image?.filename || 'edited.jpg'
    a.click()
  }, [resultUrl, image])

  return (
    <div className="h-screen flex flex-col bg-dark-950 overflow-hidden">
      {/* 顶栏 */}
      <Header
        filename={image?.filename}
        onUpload={handleUpload}
        onDownload={handleDownload}
        onUndo={undo}
        onRedo={redo}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
        showBeforeAfter={showBeforeAfter}
        onToggleCompare={() => setShowBeforeAfter(!showBeforeAfter)}
        showBatch={showBatch}
        onToggleBatch={() => setShowBatch(!showBatch)}
        zoom={zoom}
        onZoomChange={setZoom}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧工具栏 */}
        <Toolbar
          tool={tool}
          onToolChange={setTool}
          brushSize={brushSize}
          onBrushSizeChange={setBrushSize}
        />

        {/* 中间画布 */}
        <div className="flex-1 relative overflow-hidden bg-dark-900">
          {showBatch ? (
            <BatchProcess />
          ) : showBeforeAfter && image && resultUrl ? (
            <BeforeAfter original={image.url} result={resultUrl} />
          ) : (
            <Canvas
              image={image}
              resultUrl={resultUrl}
              tool={tool}
              brushSize={brushSize}
              zoom={zoom}
              isProcessing={isProcessing}
            />
          )}

          {/* 无图片时的引导 */}
          {!image && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center animate-fadeIn">
                <div className="w-32 h-32 mx-auto mb-6 rounded-3xl bg-dark-800 flex items-center justify-center">
                  <svg className="w-16 h-16 text-dark-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-semibold text-dark-200 mb-2">
                  开始你的 AI 修图之旅
                </h2>
                <p className="text-dark-400 mb-6">
                  拖拽图片到此处，或点击上方上传按钮
                </p>
                <div className="flex gap-3 justify-center text-sm text-dark-500">
                  <span className="px-3 py-1 bg-dark-800 rounded-full">AI去路人</span>
                  <span className="px-3 py-1 bg-dark-800 rounded-full">AI换天空</span>
                  <span className="px-3 py-1 bg-dark-800 rounded-full">智能调色</span>
                  <span className="px-3 py-1 bg-dark-800 rounded-full">中性灰磨皮</span>
                </div>
              </div>
            </div>
          )}

          {/* 处理中遮罩 */}
          {isProcessing && (
            <div className="absolute inset-0 bg-dark-950/70 flex items-center justify-center z-50">
              <div className="text-center">
                <div className="w-16 h-16 border-4 border-cake-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-lg text-dark-200">AI 处理中...</p>
                <p className="text-sm text-dark-400 mt-1">这可能需要几秒钟</p>
              </div>
            </div>
          )}
        </div>

        {/* 右侧面板 */}
        <Sidebar
          image={image}
          mode={adjustMode}
          onModeChange={setAdjustMode}
          params={params}
          onParamsChange={handleAdjust}
          onAIFeature={handleAIFeature}
          selectedFilter={selectedFilter}
          onFilterSelect={handleFilter}
          isProcessing={isProcessing}
        />
      </div>
    </div>
  )
}
