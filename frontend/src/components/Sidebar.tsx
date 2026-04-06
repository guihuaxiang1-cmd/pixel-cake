import React, { useState, useRef } from 'react'
import { ImageInfo, AdjustMode, AdjustParams, AIFeature } from '../App'

interface SidebarProps {
  image: ImageInfo | null
  mode: AdjustMode
  onModeChange: (mode: AdjustMode) => void
  params: AdjustParams
  onParamsChange: (params: Partial<AdjustParams>) => void
  onAIFeature: (feature: AIFeature) => void
  selectedFilter: string | null
  onFilterSelect: (name: string, intensity?: number) => void
  filterIntensity: number
  onFilterIntensityChange: (v: number) => void
  isProcessing: boolean
  onShowToast: (msg: string, type?: 'error' | 'info') => void
  onColorMatch: (refFile: File) => void
  onLocalAdjust: (mode: 'subject' | 'background', adj: { brightness?: number; contrast?: number; saturation?: number; warmth?: number }) => void
  onMakeupCustom: (opts: { lipstick?: number; blush?: number; eyeshadow?: number }) => void
}

const tabs: Array<{ id: AdjustMode; label: string; icon: string }> = [
  { id: 'basic', label: '基础', icon: '🎚️' },
  { id: 'color', label: '色彩', icon: '🎨' },
  { id: 'detail', label: '细节', icon: '🔍' },
  { id: 'filter', label: '滤镜', icon: '✨' },
  { id: 'ai', label: 'AI', icon: '🤖' },
]

const filters = [
  '青木胶片', '暖咖画报', '日系清新', '复古胶片',
  '森系自然', '赛博朋克', '莫兰迪', '哈苏色彩', '徕卡色调',
]

export default function Sidebar({
  image,
  mode,
  onModeChange,
  params,
  onParamsChange,
  onAIFeature,
  selectedFilter,
  onFilterSelect,
  filterIntensity,
  onFilterIntensityChange,
  isProcessing,
  onShowToast,
  onColorMatch,
  onLocalAdjust,
  onMakeupCustom,
}: SidebarProps) {
  return (
    <div className="w-72 bg-dark-900 border-l border-dark-700 flex flex-col shrink-0 overflow-hidden">
      {/* Tab 标签 */}
      <div className="flex border-b border-dark-700 shrink-0">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => onModeChange(tab.id)}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              mode === tab.id
                ? 'text-cake-400 border-b-2 border-cake-500 bg-dark-850'
                : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800'
            }`}
          >
            <span className="block text-base mb-0.5">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* 面板内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {mode === 'basic' && (
          <BasicPanel params={params} onChange={onParamsChange} />
        )}
        {mode === 'color' && (
          <ColorPanel
            params={params}
            onChange={onParamsChange}
            onLocalAdjust={onLocalAdjust}
            hasImage={!!image}
            isProcessing={isProcessing}
          />
        )}
        {mode === 'detail' && (
          <DetailPanel
            params={params}
            onChange={onParamsChange}
            onAIFeature={onAIFeature}
            onMakeupCustom={onMakeupCustom}
            hasImage={!!image}
            isProcessing={isProcessing}
          />
        )}
        {mode === 'filter' && (
          <FilterPanel
            filters={filters}
            selected={selectedFilter}
            onSelect={onFilterSelect}
            intensity={filterIntensity}
            onIntensityChange={onFilterIntensityChange}
            onColorMatch={onColorMatch}
            hasImage={!!image}
            isProcessing={isProcessing}
          />
        )}
        {mode === 'ai' && (
          <AIPanel
            onFeature={onAIFeature}
            isProcessing={isProcessing}
            hasImage={!!image}
          />
        )}
      </div>
    </div>
  )
}

// ─── 基础调色 ───

function BasicPanel({
  params,
  onChange,
}: {
  params: AdjustParams
  onChange: (p: Partial<AdjustParams>) => void
}) {
  return (
    <div className="space-y-4">
      <Slider label="曝光" value={params.brightness} min={-1} max={1} step={0.01}
        onChange={v => onChange({ brightness: v })} />
      <Slider label="对比度" value={params.contrast} min={-1} max={1} step={0.01}
        onChange={v => onChange({ contrast: v })} />
      <Slider label="高光" value={params.highlights} min={-1} max={1} step={0.01}
        onChange={v => onChange({ highlights: v })} />
      <Slider label="阴影" value={params.shadows} min={-1} max={1} step={0.01}
        onChange={v => onChange({ shadows: v })} />
      <Slider label="白色色阶" value={params.vibrance} min={-1} max={1} step={0.01}
        onChange={v => onChange({ vibrance: v })} />
      <Slider label="黑色色阶" value={params.clarity} min={-1} max={1} step={0.01}
        onChange={v => onChange({ clarity: v })} />
    </div>
  )
}

// ─── 色彩 + 局部调色 ───

function ColorPanel({
  params,
  onChange,
  onLocalAdjust,
  hasImage,
  isProcessing,
}: {
  params: AdjustParams
  onChange: (p: Partial<AdjustParams>) => void
  onLocalAdjust: (mode: 'subject' | 'background', adj: { brightness?: number; contrast?: number; saturation?: number; warmth?: number }) => void
  hasImage: boolean
  isProcessing: boolean
}) {
  const [localMode, setLocalMode] = useState<'subject' | 'background' | null>(null)
  const [localAdj, setLocalAdj] = useState({ brightness: 0, contrast: 0, saturation: 0, warmth: 0 })

  const handleApply = () => {
    if (!localMode) return
    onLocalAdjust(localMode, localAdj)
    setLocalMode(null)
  }

  return (
    <div className="space-y-4">
      <Slider label="色温" value={params.warmth} min={-1} max={1} step={0.01}
        onChange={v => onChange({ warmth: v })} />
      <Slider label="色调" value={params.tint} min={-1} max={1} step={0.01}
        onChange={v => onChange({ tint: v })} />
      <Slider label="饱和度" value={params.saturation} min={-1} max={1} step={0.01}
        onChange={v => onChange({ saturation: v })} />
      <Slider label="自然饱和度" value={params.vibrance} min={-1} max={1} step={0.01}
        onChange={v => onChange({ vibrance: v })} />

      <div className="pt-2 border-t border-dark-700">
        <h4 className="text-xs text-dark-400 mb-3 font-medium">局部调色</h4>
        <div className="grid grid-cols-3 gap-2">
          <MiniButton
            label="主体"
            icon="👤"
            active={localMode === 'subject'}
            onClick={() => setLocalMode(localMode === 'subject' ? null : 'subject')}
          />
          <MiniButton
            label="背景"
            icon="🏔️"
            active={localMode === 'background'}
            onClick={() => setLocalMode(localMode === 'background' ? null : 'background')}
          />
          <MiniButton label="径向" icon="⭕" onClick={() => {}} disabled />
          <MiniButton label="线性" icon="📐" onClick={() => {}} disabled />
          <MiniButton label="画笔" icon="🖌️" onClick={() => {}} disabled />
          <MiniButton label="吸管" icon="💧" onClick={() => {}} disabled />
        </div>

        {localMode && (
          <div className="mt-3 p-3 bg-dark-800 rounded-lg space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between">
              <span className="text-xs text-dark-200 font-medium">
                {localMode === 'subject' ? '👤 主体调色' : '🏔️ 背景调色'}
              </span>
              <button
                onClick={() => setLocalMode(null)}
                className="text-dark-400 hover:text-dark-200 text-xs"
              >✕</button>
            </div>
            <Slider label="亮度" value={localAdj.brightness} min={-1} max={1} step={0.01}
              onChange={v => setLocalAdj(p => ({ ...p, brightness: v }))} />
            <Slider label="对比度" value={localAdj.contrast} min={-1} max={1} step={0.01}
              onChange={v => setLocalAdj(p => ({ ...p, contrast: v }))} />
            <Slider label="饱和度" value={localAdj.saturation} min={-1} max={1} step={0.01}
              onChange={v => setLocalAdj(p => ({ ...p, saturation: v }))} />
            <Slider label="色温" value={localAdj.warmth} min={-1} max={1} step={0.01}
              onChange={v => setLocalAdj(p => ({ ...p, warmth: v }))} />
            <button
              onClick={handleApply}
              disabled={!hasImage || isProcessing}
              className="w-full py-2 rounded-lg bg-cake-600 hover:bg-cake-500 disabled:opacity-40 text-sm font-medium transition-colors"
            >
              ✨ 应用局部调色
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── 细节 + 人像精修 + 妆容 ───

function DetailPanel({
  params,
  onChange,
  onAIFeature,
  onMakeupCustom,
  hasImage,
  isProcessing,
}: {
  params: AdjustParams
  onChange: (p: Partial<AdjustParams>) => void
  onAIFeature: (f: AIFeature) => void
  onMakeupCustom: (opts: { lipstick?: number; blush?: number; eyeshadow?: number }) => void
  hasImage: boolean
  isProcessing: boolean
}) {
  const [showMakeup, setShowMakeup] = useState(false)
  const [lipstick, setLipstick] = useState(0.4)
  const [blush, setBlush] = useState(0.3)
  const [eyeshadow, setEyeshadow] = useState(0.2)

  return (
    <div className="space-y-4">
      <Slider label="锐化" value={params.sharpness} min={0} max={1} step={0.01}
        onChange={v => onChange({ sharpness: v })} />
      <Slider label="降噪" value={params.denoise} min={0} max={1} step={0.01}
        onChange={v => onChange({ denoise: v })} />
      <Slider label="清晰度" value={params.clarity} min={-1} max={1} step={0.01}
        onChange={v => onChange({ clarity: v })} />

      <div className="pt-2 border-t border-dark-700">
        <h4 className="text-xs text-dark-400 mb-3 font-medium">人像精修</h4>
        <div className="space-y-2">
          <FeatureButton
            label="中性灰磨皮"
            desc="广告级光影重塑"
            icon="✨"
            disabled={!hasImage || isProcessing}
            onClick={() => onAIFeature('skin-smooth')}
          />
          <FeatureButton
            label="3D美型"
            desc="骨骼定位精修"
            icon="💎"
            disabled={!hasImage || isProcessing}
            onClick={() => onAIFeature('face-slim')}
          />
          <FeatureButton
            label="发丝处理"
            desc="祛碎发/毛躁发丝"
            icon="💇"
            disabled={!hasImage || isProcessing}
            onClick={() => onAIFeature('hair-smooth')}
          />
          <FeatureButton
            label="牙齿美白"
            desc="自动检测美白"
            icon="😁"
            disabled={!hasImage || isProcessing}
            onClick={() => onAIFeature('teeth-whiten')}
          />
          <FeatureButton
            label="妆容调整"
            desc="口红/腮红/眼影"
            icon="💄"
            disabled={!hasImage || isProcessing}
            onClick={() => setShowMakeup(!showMakeup)}
          />

          {showMakeup && (
            <div className="p-3 bg-dark-800 rounded-lg space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <span className="text-xs text-dark-200 font-medium">💄 妆容参数</span>
                <button onClick={() => setShowMakeup(false)} className="text-dark-400 hover:text-dark-200 text-xs">✕</button>
              </div>
              <Slider label="口红" value={lipstick} min={0} max={1} step={0.01}
                onChange={v => setLipstick(v)} />
              <Slider label="腮红" value={blush} min={0} max={1} step={0.01}
                onChange={v => setBlush(v)} />
              <Slider label="眼影" value={eyeshadow} min={0} max={1} step={0.01}
                onChange={v => setEyeshadow(v)} />
              <button
                onClick={() => onMakeupCustom({ lipstick, blush, eyeshadow })}
                disabled={!hasImage || isProcessing}
                className="w-full py-2 rounded-lg bg-cake-600 hover:bg-cake-500 disabled:opacity-40 text-sm font-medium transition-colors"
              >
                💄 应用妆容
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── 滤镜 + AI 追色 ───

function FilterPanel({
  filters,
  selected,
  onSelect,
  intensity,
  onIntensityChange,
  onColorMatch,
  hasImage,
  isProcessing,
}: {
  filters: string[]
  selected: string | null
  onSelect: (name: string, intensity?: number) => void
  intensity: number
  onIntensityChange: (v: number) => void
  onColorMatch: (refFile: File) => void
  hasImage: boolean
  isProcessing: boolean
}) {
  const refInput = useRef<HTMLInputElement>(null)

  const handleRefFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onColorMatch(file)
    e.target.value = ''
  }

  return (
    <div>
      <div className="grid grid-cols-2 gap-2">
        {filters.map(name => (
          <button
            key={name}
            onClick={() => onSelect(name)}
            className={`p-3 rounded-lg text-center text-sm transition-all ${
              selected === name
                ? 'bg-cake-600/20 ring-1 ring-cake-500 text-cake-300'
                : 'bg-dark-800 hover:bg-dark-700 text-dark-200'
            }`}
          >
            <div className="w-full aspect-square rounded-md bg-gradient-to-br from-dark-600 to-dark-700 mb-2 flex items-center justify-center text-2xl">
              🎨
            </div>
            {name}
          </button>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-dark-700">
        <Slider label="滤镜强度" value={intensity} min={0} max={1} step={0.01}
          onChange={(v) => { onIntensityChange(v); if (selected) onSelect(selected, v); }} />
      </div>

      <div className="mt-3">
        <h4 className="text-xs text-dark-400 mb-2 font-medium">AI 追色 2.0</h4>
        <input ref={refInput} type="file" accept="image/*" className="hidden" onChange={handleRefFile} />
        <button
          onClick={() => refInput.current?.click()}
          disabled={!hasImage || isProcessing}
          className="w-full py-2.5 rounded-lg bg-dark-800 hover:bg-dark-700 disabled:opacity-40 text-sm text-dark-200 transition-colors flex items-center justify-center gap-2"
        >
          📷 导入参考图追色
        </button>
      </div>
    </div>
  )
}

// ─── AI 功能 ───

function AIPanel({
  onFeature,
  isProcessing,
  hasImage,
}: {
  onFeature: (f: AIFeature) => void
  isProcessing: boolean
  hasImage: boolean
}) {
  const aiFeatures: Array<{
    id: AIFeature
    icon: string
    label: string
    desc: string
  }> = [
    { id: 'remove-person', icon: '🚶', label: 'AI去路人', desc: '语义识别自动移除' },
    { id: 'remove-tattoo', icon: '💉', label: 'AI祛纹身', desc: '保留自然肤色纹理' },
    { id: 'remove-stubble', icon: '🧔', label: 'AI去胡渣', desc: '面部细小胡须去除' },
    { id: 'remove-flaw', icon: '🔧', label: 'AI消除穿帮', desc: '发网/胶痕/电线' },
    { id: 'relight', icon: '💡', label: 'AI补光', desc: '智能光照调整' },
    { id: 'fill-grass', icon: '🌿', label: 'AI补草地', desc: '自动生成草地纹理' },
    { id: 'sky-replace', icon: '🌅', label: '换天空', desc: '无缝天空替换' },
    { id: 'skin-smooth', icon: '✨', label: '中性灰磨皮', desc: '保留纹理的磨皮' },
    { id: 'teeth-whiten', icon: '😁', label: '牙齿美白', desc: '自动检测美白' },
    { id: 'face-slim', icon: '💎', label: '3D美型', desc: 'AI智能瘦脸' },
    { id: 'hair-smooth', icon: '💇', label: '发丝处理', desc: '祛碎发/毛躁' },
    { id: 'makeup', icon: '💄', label: '妆容调整', desc: '口红/腮红/眼影' },
    { id: 'color-match', icon: '🎯', label: 'AI追色 2.0', desc: '光影氛围全匹配' },
  ]

  return (
    <div className="space-y-2">
      <div className="mb-3">
        <h4 className="text-sm font-medium text-dark-200 mb-1">🤖 AI 智能修图</h4>
        <p className="text-xs text-dark-500">选择功能，AI 自动处理</p>
      </div>

      {aiFeatures.map(f => (
        <button
          key={f.id}
          onClick={() => hasImage && !isProcessing && onFeature(f.id)}
          disabled={!hasImage || isProcessing}
          className="w-full p-3 rounded-lg bg-dark-800 hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition-colors group"
        >
          <div className="flex items-center gap-3">
            <span className="text-xl group-hover:scale-110 transition-transform">{f.icon}</span>
            <div>
              <div className="text-sm font-medium text-dark-100">{f.label}</div>
              <div className="text-xs text-dark-500">{f.desc}</div>
            </div>
          </div>
        </button>
      ))}

      <div className="mt-4 pt-3 border-t border-dark-700">
        <h4 className="text-xs text-dark-400 mb-2 font-medium">⚡ 批量AI</h4>
        <button className="w-full py-2.5 rounded-lg bg-cake-600/20 hover:bg-cake-600/30 text-sm text-cake-300 transition-colors">
          🚀 一键全套修图
        </button>
      </div>
    </div>
  )
}

// ─── 通用组件 ───

function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
}) {
  const percent = ((value - min) / (max - min)) * 100

  return (
    <div>
      <div className="flex justify-between mb-1.5">
        <span className="text-xs text-dark-300">{label}</span>
        <span className="text-xs text-dark-400 tabular-nums w-10 text-right">
          {value > 0 ? '+' : ''}{(value * 100).toFixed(0)}
        </span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="w-full"
          style={{
            background: `linear-gradient(to right, #ec4899 ${percent}%, #334155 ${percent}%)`,
          }}
        />
      </div>
    </div>
  )
}

function MiniButton({ label, icon, onClick, active, disabled }: {
  label: string
  icon: string
  onClick?: () => void
  active?: boolean
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`p-2 rounded-lg text-center transition-colors ${
        active
          ? 'bg-cake-600/20 ring-1 ring-cake-500'
          : 'bg-dark-800 hover:bg-dark-700'
      } ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      <span className="text-lg block">{icon}</span>
      <span className="text-[10px] text-dark-400">{label}</span>
    </button>
  )
}

function FeatureButton({
  label,
  desc,
  icon,
  disabled,
  onClick,
}: {
  label: string
  desc: string
  icon: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full p-2.5 rounded-lg bg-dark-800 hover:bg-dark-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition-colors"
    >
      <div className="flex items-center gap-2">
        <span>{icon}</span>
        <div>
          <div className="text-sm text-dark-200">{label}</div>
          <div className="text-[10px] text-dark-500">{desc}</div>
        </div>
      </div>
    </button>
  )
}
