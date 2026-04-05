import React from 'react'
import { Tool } from '../App'

interface ToolbarProps {
  tool: Tool
  onToolChange: (tool: Tool) => void
  brushSize: number
  onBrushSizeChange: (size: number) => void
}

const tools: Array<{ id: Tool; icon: string; label: string; shortcut?: string }> = [
  { id: 'select', icon: '👆', label: '选择', shortcut: 'V' },
  { id: 'hand', icon: '✋', label: '平移', shortcut: 'H' },
  { id: 'brush', icon: '🖌️', label: '画笔', shortcut: 'B' },
  { id: 'eraser', icon: '🧹', label: '橡皮', shortcut: 'E' },
  { id: 'auto-person', icon: '👤', label: 'AI识人' },
  { id: 'auto-sky', icon: '🌤️', label: 'AI识天' },
  { id: 'inpaint', icon: '✨', label: 'AI修复' },
  { id: 'crop', icon: '✂️', label: '裁剪', shortcut: 'C' },
]

export default function Toolbar({ tool, onToolChange, brushSize, onBrushSizeChange }: ToolbarProps) {
  return (
    <div className="w-14 bg-dark-900 border-r border-dark-700 flex flex-col items-center py-3 gap-1 shrink-0">
      {tools.map(t => (
        <button
          key={t.id}
          onClick={() => onToolChange(t.id)}
          className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg transition-all ${
            tool === t.id
              ? 'bg-cake-600/20 text-cake-400 ring-1 ring-cake-500/50'
              : 'text-dark-300 hover:bg-dark-700 hover:text-dark-100'
          }`}
          title={`${t.label}${t.shortcut ? ` (${t.shortcut})` : ''}`}
        >
          {t.icon}
        </button>
      ))}

      {/* 画笔大小 */}
      {(tool === 'brush' || tool === 'eraser') && (
        <div className="mt-2 px-1 w-full">
          <input
            type="range"
            min="1"
            max="100"
            value={brushSize}
            onChange={e => onBrushSizeChange(Number(e.target.value))}
            className="w-full"
            style={{
              writingMode: 'vertical-lr',
              height: '80px',
              width: '4px',
              transform: 'rotate(180deg)',
            }}
          />
          <span className="text-[10px] text-dark-400 text-center block mt-1">
            {brushSize}px
          </span>
        </div>
      )}
    </div>
  )
}
