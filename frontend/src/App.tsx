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
  | 'teeth-whiten'   // FIX: added
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
  const [filterIntensity, setFilterIntensity] = useState(1.0)
  // FIX: Add error message state for user-visible feedback
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Auto-clear error after 5 seconds
  useEffect(() => {
    if (errorMsg) {
      const timer = setTimeout(() => setErrorMsg(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [errorMsg])

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
    setFilterIntensity(1.0)
  }, [])

  // ─── AI 操作 ───

  const handleAIFeature = useCallback(async (feature: AIFeature) => {
    if (!image) return
    setIsProcessing(true)
    setErrorMsg(null)

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
          if (!segRes.ok) throw new Error(`分割失败 (${segRes.status})`)
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId }),
            })
            if (!inpRes.ok) throw new Error(`修复失败 (${inpRes.status})`)
            blob = await inpRes.blob()
          }
          break
        }
        case 'remove-tattoo':
        case 'remove-stubble': {
          // FIX: Use 'skin' mode (now supported by backend)
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'skin' }),
          })
          if (!segRes.ok) throw new Error(`皮肤检测失败 (${segRes.status})`)
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId }),
            })
            if (!inpRes.ok) throw new Error(`修复失败 (${inpRes.status})`)
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
          if (!res.ok) throw new Error(`补光失败 (${res.status})`)
          blob = await res.blob()
          break
        }
        case 'sky-replace': {
          const res = await fetch('/api/sky/replace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id: image.imageId, sky_type: 'sunset', blend_strength: 0.7 }),
          })
          if (!res.ok) throw new Error(`换天空失败 (${res.status})`)
          blob = await res.blob()
          break
        }
        case 'fill-grass': {
          // FIX: Use 'ground' mode (now supported by backend)
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'ground' }),
          })
          if (!segRes.ok) throw new Error(`地面检测失败 (${segRes.status})`)
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId, fill_type: 'grass' }),
            })
            if (!inpRes.ok) throw new Error(`补草地失败 (${inpRes.status})`)
            blob = await inpRes.blob()
          }
          break
        }
        case 'skin-smooth': {
          // FIX: skin_smooth field now accepted by backend
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
          if (!res.ok) throw new Error(`磨皮失败 (${res.status})`)
          blob = await res.blob()
          break
        }
        case 'teeth-whiten': {
          // FIX: Now properly implemented
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id: image.imageId, mode: 'teeth' }),
          })
          if (!segRes.ok) throw new Error(`牙齿检测失败 (${segRes.status})`)
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id: image.imageId, mask_id: maskId, fill_type: 'whiten' }),
            })
            if (!inpRes.ok) throw new Error(`美白失败 (${inpRes.status})`)
            blob = await inpRes.blob()
          }
          break
        }
        case 'color-match': {
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
          if (!res.ok) throw new Error(`追色失败 (${res.status})`)
          blob = await res.blob()
          break
        }
      }

      if (blob) {
        const url = URL.createObjectURL(blob)
        setResultUrl(url)
        setHistory(prev => [...prev.slice(0, historyIndex + 1), url])
        setHistoryIndex(prev => prev + 1)
      } else {
        // FIX: No result = show error
        setErrorMsg('处理未返回结果，请检查图片是否正确上传')
      }
    } catch (err: any) {
      console.error('AI处理失败:', err)
      // FIX: User-visible error message
      setErrorMsg(`AI 处理失败: ${err.message || '未知错误'}`)
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
      // FIX: Send ALL parameters to backend
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
          highlights: merged.highlights,
          shadows: merged.shadows,
          vibrance: merged.vibrance,
          clarity: merged.clarity,
          tint: merged.tint,
        }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`调色失败 (${res.status}): ${text}`)
      }
      const blob = await res.blob()
      setResultUrl(URL.createObjectURL(blob))
    } catch (err: any) {
      console.error('调色失败:', err)
      setErrorMsg(`调色失败: ${err.message}`)
    }
  }, [image, params])

  // ─── 滤镜 ───

  const handleFilter = useCallback(async (filterName: string, intensity?: number) => {
    if (!image) return
    setSelectedFilter(filterName)
    const effIntensity = intensity ?? filterIntensity
    if (intensity !== undefined) setFilterIntensity(intensity)
    setIsProcessing(true)
    setErrorMsg(null)
    try {
      const res = await fetch('/api/enhance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: image.imageId,
          filter: filterName,
          filter_intensity: effIntensity,
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
      } else {
        const text = await res.text()
        throw new Error(`滤镜失败 (${res.status}): ${text}`)
      }
    } catch (err: any) {
      console.error('滤镜失败:', err)
      setErrorMsg(`滤镜失败: ${err.message}`)
    } finally {
      setIsProcessing(false)
    }
  }, [image, filterIntensity])

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

  // ─── 画笔提交修复 ───

  const handleMaskInpaint = useCallback(async (maskBlob: Blob) => {
    if (!image) return
    setIsProcessing(true)
    setErrorMsg(null)
    try {
      // 上传 mask
      const maskForm = new FormData()
      maskForm.append('file', maskBlob, 'mask.png')
      const maskUploadRes = await fetch('/api/upload', { method: 'POST', body: maskForm })
      if (!maskUploadRes.ok) throw new Error('Mask 上传失败')
      const maskData = await maskUploadRes.json()
      const maskId = maskData.image_id

      // 调用 inpaint
      const res = await fetch('/api/inpaint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: image.imageId, mask_id: maskId }),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`修复失败 (${res.status}): ${text}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      setResultUrl(url)
      setHistory(prev => [...prev.slice(0, historyIndex + 1), url])
      setHistoryIndex(prev => prev + 1)
    } catch (err: any) {
      console.error('画笔修复失败:', err)
      setErrorMsg(`修复失败: ${err.message}`)
    } finally {
      setIsProcessing(false)
    }
  }, [image, historyIndex])

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
              onZoomChange={setZoom}
              isProcessing={isProcessing}
              onAIFeature={handleAIFeature}
              onMaskInpaint={handleMaskInpaint}
              onClearTool={() => setTool('select')}
              onError={setErrorMsg}
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

          {/* FIX: 错误提示浮层 */}
          {errorMsg && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-red-900/90 text-red-100 px-6 py-3 rounded-lg shadow-lg flex items-center gap-3 animate-fadeIn">
              <span className="text-lg">⚠️</span>
              <span className="text-sm">{errorMsg}</span>
              <button
                onClick={() => setErrorMsg(null)}
                className="ml-2 text-red-300 hover:text-white transition-colors"
              >
                ✕
              </button>
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
          filterIntensity={filterIntensity}
          onFilterIntensityChange={setFilterIntensity}
          isProcessing={isProcessing}
        />
      </div>
    </div>
  )
}
