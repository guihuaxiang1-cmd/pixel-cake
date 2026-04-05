import React, { useRef } from 'react'

interface HeaderProps {
  filename?: string
  onUpload: (file: File) => void
  onDownload: () => void
  onUndo: () => void
  onRedo: () => void
  canUndo: boolean
  canRedo: boolean
  showBeforeAfter: boolean
  onToggleCompare: () => void
  showBatch: boolean
  onToggleBatch: () => void
  zoom: number
  onZoomChange: (z: number) => void
}

export default function Header({
  filename,
  onUpload,
  onDownload,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  showBeforeAfter,
  onToggleCompare,
  showBatch,
  onToggleBatch,
  zoom,
  onZoomChange,
}: HeaderProps) {
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    e.target.value = ''
  }

  return (
    <header className="h-12 bg-dark-900 border-b border-dark-700 flex items-center px-4 gap-3 select-none shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 mr-4">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cake-400 to-cake-600 flex items-center justify-center">
          <span className="text-white font-bold text-sm">P</span>
        </div>
        <span className="font-semibold text-dark-100 hidden sm:inline">Pixel Cake</span>
      </div>

      {/* 文件操作 */}
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
      <button
        onClick={() => fileRef.current?.click()}
        className="px-3 py-1.5 bg-cake-600 hover:bg-cake-500 rounded-md text-sm font-medium transition-colors"
      >
        📂 打开图片
      </button>

      {filename && (
        <span className="text-sm text-dark-400 truncate max-w-[200px]">{filename}</span>
      )}

      <div className="flex-1" />

      {/* 缩放 */}
      <div className="flex items-center gap-2 text-sm text-dark-300">
        <button
          onClick={() => onZoomChange(Math.max(0.1, zoom - 0.1))}
          className="w-7 h-7 rounded hover:bg-dark-700 flex items-center justify-center"
        >
          −
        </button>
        <span className="w-12 text-center">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => onZoomChange(Math.min(5, zoom + 0.1))}
          className="w-7 h-7 rounded hover:bg-dark-700 flex items-center justify-center"
        >
          +
        </button>
        <button
          onClick={() => onZoomChange(1)}
          className="px-2 py-1 rounded hover:bg-dark-700 text-xs"
        >
          适配
        </button>
      </div>

      <div className="w-px h-6 bg-dark-700" />

      {/* 操作按钮 */}
      <div className="flex items-center gap-1">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className="w-8 h-8 rounded hover:bg-dark-700 disabled:opacity-30 flex items-center justify-center text-dark-300"
          title="撤销 (Ctrl+Z)"
        >
          ↩
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className="w-8 h-8 rounded hover:bg-dark-700 disabled:opacity-30 flex items-center justify-center text-dark-300"
          title="重做 (Ctrl+Shift+Z)"
        >
          ↪
        </button>
      </div>

      <div className="w-px h-6 bg-dark-700" />

      {/* 对比 & 批量 */}
      <button
        onClick={onToggleCompare}
        className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
          showBeforeAfter ? 'bg-cake-600 text-white' : 'hover:bg-dark-700 text-dark-300'
        }`}
      >
        ⚖️ 对比
      </button>
      <button
        onClick={onToggleBatch}
        className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
          showBatch ? 'bg-cake-600 text-white' : 'hover:bg-dark-700 text-dark-300'
        }`}
      >
        📦 批量
      </button>

      <div className="w-px h-6 bg-dark-700" />

      {/* 导出 */}
      <button
        onClick={onDownload}
        className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-md text-sm text-dark-200 transition-colors"
      >
        💾 导出
      </button>
    </header>
  )
}
