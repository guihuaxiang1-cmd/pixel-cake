import React, { useState, useRef, useCallback } from 'react'

interface BatchImage {
  id: string
  file: File
  preview: string
  status: 'pending' | 'processing' | 'done' | 'error'
  resultUrl?: string
}

export default function BatchProcess() {
  const [images, setImages] = useState<BatchImage[]>([])
  const [action, setAction] = useState('auto_remove')
  const [isRunning, setIsRunning] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback((files: FileList) => {
    const newImages: BatchImage[] = Array.from(files)
      .filter(f => f.type.startsWith('image/'))
      .map(file => ({
        id: Math.random().toString(36).slice(2, 10),
        file,
        preview: URL.createObjectURL(file),
        status: 'pending' as const,
      }))
    setImages(prev => [...prev, ...newImages])
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  const handleStart = useCallback(async () => {
    setIsRunning(true)

    for (let i = 0; i < images.length; i++) {
      if (images[i].status === 'done') continue

      setImages(prev => prev.map((img, idx) =>
        idx === i ? { ...img, status: 'processing' } : img
      ))

      try {
        // 上传
        const fd = new FormData()
        fd.append('file', images[i].file)
        const uploadRes = await fetch('/api/upload', { method: 'POST', body: fd })
        const { image_id } = await uploadRes.json()

        // 处理
        let resultUrl = ''
        if (action === 'auto_remove') {
          const segRes = await fetch('/api/auto-segment', {
            method: 'POST',
            body: new URLSearchParams({ image_id, mode: 'person' }),
          })
          const maskId = segRes.headers.get('X-Mask-Id')
          if (maskId) {
            const inpRes = await fetch('/api/inpaint', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_id, mask_id: maskId }),
            })
            resultUrl = URL.createObjectURL(await inpRes.blob())
          }
        } else if (action === 'enhance') {
          const res = await fetch('/api/enhance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_id,
              brightness: 0.05,
              contrast: 0.1,
              saturation: 0.05,
            }),
          })
          resultUrl = URL.createObjectURL(await res.blob())
        } else if (action === 'sky_replace') {
          const res = await fetch('/api/sky/replace', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_id, sky_type: 'sunset' }),
          })
          resultUrl = URL.createObjectURL(await res.blob())
        }

        setImages(prev => prev.map((img, idx) =>
          idx === i ? { ...img, status: 'done', resultUrl } : img
        ))
      } catch {
        setImages(prev => prev.map((img, idx) =>
          idx === i ? { ...img, status: 'error' } : img
        ))
      }
    }

    setIsRunning(false)
  }, [images, action])

  const doneCount = images.filter(i => i.status === 'done').length

  return (
    <div className="w-full h-full p-6 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-xl font-semibold text-dark-100 mb-6">
          📦 批量处理
        </h2>

        {/* 上传区 */}
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          className="border-2 border-dashed border-dark-600 rounded-xl p-8 text-center mb-6 hover:border-cake-500/50 transition-colors"
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={e => e.target.files && handleFiles(e.target.files)}
          />
          <div className="text-4xl mb-3">📸</div>
          <p className="text-dark-300 mb-2">拖拽图片到此处，或</p>
          <button
            onClick={() => fileRef.current?.click()}
            className="px-4 py-2 bg-cake-600 hover:bg-cake-500 rounded-lg text-sm font-medium transition-colors"
          >
            选择文件
          </button>
          <p className="text-xs text-dark-500 mt-2">支持 JPG、PNG、RAW 格式</p>
        </div>

        {/* 操作选择 */}
        <div className="flex gap-3 mb-6">
          {[
            { id: 'auto_remove', label: '🚶 AI去路人', desc: '自动检测移除' },
            { id: 'enhance', label: '🎨 智能调色', desc: '自动优化色彩' },
            { id: 'sky_replace', label: '🌅 换天空', desc: '统一天空风格' },
          ].map(a => (
            <button
              key={a.id}
              onClick={() => setAction(a.id)}
              className={`flex-1 p-3 rounded-lg text-left transition-all ${
                action === a.id
                  ? 'bg-cake-600/20 ring-1 ring-cake-500'
                  : 'bg-dark-800 hover:bg-dark-700'
              }`}
            >
              <div className="text-sm font-medium text-dark-100">{a.label}</div>
              <div className="text-xs text-dark-400">{a.desc}</div>
            </button>
          ))}
        </div>

        {/* 图片网格 */}
        {images.length > 0 && (
          <>
            <div className="grid grid-cols-4 gap-3 mb-6">
              {images.map((img, idx) => (
                <div
                  key={img.id}
                  className="relative aspect-square rounded-lg overflow-hidden bg-dark-800 group"
                >
                  <img
                    src={img.resultUrl || img.preview}
                    alt={img.file.name}
                    className="w-full h-full object-cover"
                  />
                  {/* 状态标识 */}
                  <div className="absolute top-2 right-2">
                    {img.status === 'pending' && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-dark-800/80 text-dark-300">
                        待处理
                      </span>
                    )}
                    {img.status === 'processing' && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-yellow-500/80 text-white animate-pulse">
                        处理中...
                      </span>
                    )}
                    {img.status === 'done' && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-green-500/80 text-white">
                        ✓ 完成
                      </span>
                    )}
                    {img.status === 'error' && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-red-500/80 text-white">
                        ✗ 失败
                      </span>
                    )}
                  </div>
                  {/* 文件名 */}
                  <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-dark-950/80">
                    <p className="text-[10px] text-dark-200 truncate">{img.file.name}</p>
                  </div>
                  {/* 删除按钮 */}
                  <button
                    onClick={() => setImages(prev => prev.filter((_, i) => i !== idx))}
                    className="absolute top-2 left-2 w-5 h-5 rounded-full bg-dark-950/70 text-dark-300 hover:text-red-400 text-xs hidden group-hover:flex items-center justify-center"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            {/* 进度 & 操作 */}
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cake-500 rounded-full transition-all duration-300"
                    style={{ width: images.length ? `${(doneCount / images.length) * 100}%` : 0 }}
                  />
                </div>
                <p className="text-xs text-dark-400 mt-1">
                  {doneCount} / {images.length} 完成
                </p>
              </div>
              <button
                onClick={handleStart}
                disabled={isRunning || images.length === 0}
                className="px-6 py-2.5 bg-cake-600 hover:bg-cake-500 disabled:opacity-40 rounded-lg text-sm font-medium transition-colors"
              >
                {isRunning ? '⏳ 处理中...' : '🚀 开始批量处理'}
              </button>
              {doneCount > 0 && (
                <button className="px-4 py-2.5 bg-dark-700 hover:bg-dark-600 rounded-lg text-sm transition-colors">
                  💾 全部下载
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
