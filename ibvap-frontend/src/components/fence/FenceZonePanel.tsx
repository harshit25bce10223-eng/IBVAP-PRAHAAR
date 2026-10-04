// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — FenceZonePanel (Elevated Zone Management & Rule Configuration)
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  AlertTriangle,
  CheckCircle2,
  Plus,
  Trash2,
  Save,
  X,
  Pencil,
  Loader2,
  Undo2,
  Eraser,
  Clock,
  Shield,
  Layers,
  ChevronRight,
} from 'lucide-react'
import { Badge, Button } from '@/components/ui'
import { useFenceStore, useCameraStore } from '@/store'
import { zoneService } from '@/services/zoneService'
import { asApiError } from '@/services/api'
import {
  validateZonePolygon,
  formatActiveTimeWindow,
  formatMonitoredObjects,
  formatZoneRuleSummary,
} from './polygonValidation'
import type { ObjectType, Zone, ZoneRules } from '@/types'

const OBJECT_TYPES: ObjectType[] = ['HUMAN', 'VEHICLE', 'ANIMAL']

export function FenceZonePanel() {
  const {
    zones,
    mode,
    editingId,
    draftPoints,
    saving,
    error,
    setZones,
    setMode,
    beginDrawing,
    clearDraft,
    removeDraftPoint,
    setSaving,
    setError,
  } = useFenceStore()
  const cameraId = useCameraStore(s => s.selectedCameraId)
  const [ruleDraft, setRuleDraft] = useState<{ name: string; active: boolean; rules: ZoneRules } | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [inspectZone, setInspectZone] = useState<Zone | null>(null)

  const isDrawing = mode === 'draw'
  const isEditing = mode === 'edit'
  const pointCount = draftPoints.length

  // Instant client-side validation
  const validation = useMemo(() => validateZonePolygon(draftPoints), [draftPoints])
  const polygonValid = validation.valid

  const saveZone = async () => {
    if (!polygonValid || saving) return
    setSaving(true)
    setError(null)
    try {
      const payload = ruleDraft
        ? {
            camera_id: cameraId,
            polygon: draftPoints,
            name: ruleDraft.name,
            active: ruleDraft.active,
            rules: ruleDraft.rules,
          }
        : { camera_id: cameraId, polygon: draftPoints }
      const saved = await zoneService.create(payload)
      setZones([...zones, saved])
      clearDraft()
      setRuleDraft(null)
    } catch (err) {
      setError(asApiError(err).message)
    } finally {
      setSaving(false)
    }
  }

  const saveEdit = async () => {
    if (!editingId || !polygonValid || saving) return
    setSaving(true)
    setError(null)
    try {
      const patch = ruleDraft
        ? {
            polygon: draftPoints,
            name: ruleDraft.name,
            active: ruleDraft.active,
            rules: ruleDraft.rules,
          }
        : { polygon: draftPoints }
      const saved = await zoneService.update(editingId, patch)
      setZones(zones.map(z => (z.zone_id === editingId ? saved : z)))
      clearDraft()
      setRuleDraft(null)
    } catch (err) {
      setError(asApiError(err).message)
    } finally {
      setSaving(false)
    }
  }

  const deleteZone = async (zone: Zone) => {
    if (confirmDeleteId !== zone.zone_id) {
      setConfirmDeleteId(zone.zone_id)
      return
    }
    setConfirmDeleteId(null)
    try {
      await zoneService.remove(zone.zone_id)
      setZones(zones.filter(z => z.zone_id !== zone.zone_id))
      if (inspectZone?.zone_id === zone.zone_id) setInspectZone(null)
    } catch (err) {
      setError(asApiError(err).message)
    }
  }

  const cancelEditing = () => {
    clearDraft()
    setRuleDraft(null)
    setConfirmDeleteId(null)
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-100">Virtual Fence Zones</h3>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <span className="text-slate-500">Camera:</span>
          <span className="text-cyan-300 font-bold">{cameraId}</span>
        </div>
      </div>

      {/* Editing / Drawing Controls Card */}
      {(isDrawing || isEditing) && (
        <div className="rounded-xl border border-cyan-500/40 bg-cyan-500/5 p-3.5 space-y-3">
          <div className="flex items-center justify-between gap-2 border-b border-cyan-500/20 pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300 font-mono">
              {isDrawing ? 'Create Virtual Zone' : 'Reshape Virtual Zone'}
            </span>
            <span
              className={clsx(
                'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px]',
                polygonValid
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
              )}
            >
              {polygonValid ? (
                <>
                  <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                  Valid ({pointCount} pts)
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                  {pointCount} pts
                </>
              )}
            </span>
          </div>

          {!polygonValid && validation.reason && (
            <p className="text-[11px] font-mono text-amber-300/90 bg-amber-500/10 border border-amber-500/20 p-2 rounded">
              {validation.reason}
            </p>
          )}

          {/* Zone Rules Configuration Form */}
          <ZoneRuleForm
            zone={isEditing ? zones.find(z => z.zone_id === editingId) ?? null : null}
            draft={ruleDraft}
            onChange={setRuleDraft}
          />

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-cyan-500/20">
            <Button
              size="sm"
              variant="primary"
              className="flex-1 font-mono text-xs"
              disabled={!polygonValid || saving}
              onClick={isEditing ? saveEdit : saveZone}
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              {saving ? 'Saving…' : isEditing ? 'Save Changes' : `Save Zone (${pointCount} pts)`}
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={() => pointCount > 0 && removeDraftPoint(pointCount - 1)}
              disabled={pointCount === 0 || saving}
              title="Undo last vertex"
            >
              <Undo2 className="h-3.5 w-3.5" />
              Undo
            </Button>

            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                clearDraft()
                setRuleDraft(null)
              }}
              disabled={saving}
              title="Clear all vertices"
            >
              <Eraser className="h-3.5 w-3.5" />
              Clear
            </Button>

            <Button size="sm" variant="ghost" onClick={cancelEditing} disabled={saving}>
              <X className="h-3.5 w-3.5" />
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
          <p className="text-xs font-semibold text-red-400 font-mono">Zone Operation Failed</p>
          <p className="text-[11px] text-red-300/90 mt-0.5">{error}</p>
        </div>
      )}

      {/* Zone List Section */}
      <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Configured Zones ({zones.length})</span>
          <span>Status</span>
        </div>

        {zones.length === 0 && !isDrawing && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center border border-dashed border-slate-800 rounded-xl">
            <Layers className="h-6 w-6 text-slate-600 mb-2" />
            <p className="text-xs font-mono font-medium text-slate-400">No Virtual Zones Configured</p>
            <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
              Draw a polygon over the camera feed to monitor border sector boundaries.
            </p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {zones.map(zone => (
            <ZoneRow
              key={zone.zone_id}
              zone={zone}
              editing={editingId === zone.zone_id}
              confirmingDelete={confirmDeleteId === zone.zone_id}
              onEdit={() => {
                setMode('edit')
                setRuleDraft(null)
                setConfirmDeleteId(null)
              }}
              onInspect={() => setInspectZone(zone)}
              onDelete={() => deleteZone(zone)}
              onCancelDelete={() => setConfirmDeleteId(null)}
            />
          ))}
        </div>
      </div>

      {/* Draw New Zone CTA */}
      {!isDrawing && !isEditing && (
        <Button
          variant="outline"
          size="sm"
          className="w-full font-mono text-xs border-cyan-500/30 hover:border-cyan-500/60 text-cyan-300 hover:bg-cyan-500/10"
          onClick={() => {
            beginDrawing()
            setRuleDraft({
              name: `Zone ${zones.length + 1}`,
              active: true,
              rules: {},
            })
          }}
        >
          <Plus className="h-4 w-4" />
          Draw New Virtual Zone
        </Button>
      )}

      {/* Zone Detail Drawer / Inspection Dialog */}
      {inspectZone && (
        <div className="fixed inset-y-0 right-0 w-80 bg-surface border-l border-border shadow-2xl p-4 flex flex-col gap-4 z-50">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500">Zone Configuration</span>
              <h4 className="text-sm font-bold font-mono text-cyan-300">{inspectZone.name}</h4>
            </div>
            <button
              onClick={() => setInspectZone(null)}
              className="p-1 rounded hover:bg-white/5 text-slate-400 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Zone ID</span>
              <p className="text-slate-200 mt-0.5">{inspectZone.zone_id}</p>
            </div>
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Camera</span>
              <p className="text-slate-200 mt-0.5">{inspectZone.camera_id}</p>
            </div>
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Operational Rule Summary</span>
              <p className="text-slate-300 mt-0.5 font-sans leading-relaxed">
                {formatZoneRuleSummary(inspectZone.rules)}
              </p>
            </div>
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Active Schedule</span>
              <p className="text-slate-200 mt-0.5">
                {formatActiveTimeWindow(inspectZone.rules.active_start, inspectZone.rules.active_end)}
              </p>
            </div>
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Monitored Entities</span>
              <p className="text-slate-200 mt-0.5">
                {formatMonitoredObjects(inspectZone.rules.allowed_object_types)}
              </p>
            </div>
            <div>
              <span className="text-slate-500 uppercase text-[10px]">Polygon Vertices</span>
              <p className="text-slate-200 mt-0.5">{inspectZone.polygon.length} points defined</p>
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-border flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="flex-1 font-mono text-xs"
              onClick={() => {
                setInspectZone(null)
                setMode('edit')
              }}
            >
              <Pencil className="h-3.5 w-3.5" />
              Reshape Zone
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function ZoneRow({
  zone,
  editing,
  confirmingDelete,
  onEdit,
  onInspect,
  onDelete,
  onCancelDelete,
}: {
  zone: Zone
  editing: boolean
  confirmingDelete: boolean
  onEdit: () => void
  onInspect: () => void
  onDelete: () => void
  onCancelDelete: () => void
}) {
  const summary = formatZoneRuleSummary(zone.rules)

  return (
    <div
      className={clsx(
        'group flex flex-col gap-1.5 rounded-lg border p-2.5 transition-colors',
        editing
          ? 'border-cyan-500/60 bg-cyan-500/10 ring-1 ring-cyan-500/30'
          : 'border-border/70 bg-bg/60 hover:bg-bg hover:border-slate-700'
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={clsx(
              'h-2 w-2 rounded-full flex-shrink-0',
              zone.active ? 'bg-emerald-400' : 'bg-slate-500'
            )}
            title={zone.active ? 'Active' : 'Inactive'}
          />
          <button
            onClick={onInspect}
            className="text-xs font-semibold text-slate-200 hover:text-cyan-300 font-mono truncate text-left"
          >
            {zone.name}
          </button>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <Badge variant={zone.active ? 'safe' : 'offline'} size="sm">
            {zone.active ? 'Active' : 'Inactive'}
          </Badge>
          <span className="font-mono text-[10px] text-slate-500 tabular-nums">
            {zone.polygon.length} pts
          </span>
        </div>
      </div>

      <p className="text-[11px] text-slate-400 font-sans leading-snug truncate">
        {summary}
      </p>

      {confirmingDelete ? (
        <div className="mt-1 flex items-center justify-between bg-red-500/10 border border-red-500/30 p-1.5 rounded">
          <span className="text-[10px] text-red-300 font-mono">Delete zone?</span>
          <div className="flex gap-2">
            <button
              onClick={onDelete}
              className="text-[11px] font-semibold font-mono text-red-400 underline"
            >
              Confirm
            </button>
            <button
              onClick={onCancelDelete}
              className="text-[11px] font-mono text-slate-400 hover:text-white"
            >
              Keep
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-0.5 flex items-center justify-between border-t border-white/[0.04] pt-1">
          <button
            onClick={onInspect}
            className="text-[10px] font-mono text-slate-500 hover:text-cyan-300 flex items-center gap-0.5"
          >
            Details <ChevronRight className="h-3 w-3" />
          </button>
          <div className="flex items-center gap-1">
            <button
              onClick={onEdit}
              className="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-white/5"
              title="Reshape zone vertices"
            >
              <Pencil className="h-3 w-3" />
            </button>
            <button
              onClick={onDelete}
              className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-white/5"
              title="Delete zone"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ZoneRuleForm({
  zone,
  draft,
  onChange,
}: {
  zone: Zone | null
  draft: { name: string; active: boolean; rules: ZoneRules } | null
  onChange: (d: { name: string; active: boolean; rules: ZoneRules } | null) => void
}) {
  const value = draft ?? (zone ? { name: zone.name, active: zone.active, rules: zone.rules } : null)

  const toggle = (type: ObjectType) => {
    if (!value) return
    const current = value.rules.allowed_object_types ?? []
    const has = current.includes(type)
    const allowed_object_types = has ? current.filter(t => t !== type) : [...current, type]
    onChange({ ...value, rules: { ...value.rules, allowed_object_types } })
  }

  const setTimeWindow = (start?: string, end?: string) => {
    if (!value) return
    onChange({
      ...value,
      rules: {
        ...value.rules,
        active_start: start || undefined,
        active_end: end || undefined,
      },
    })
  }

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Zone Name & Active Toggle */}
      <div className="flex items-center gap-2">
        <label className="text-[11px] text-slate-400" htmlFor="zone-name">
          Name:
        </label>
        <input
          id="zone-name"
          className="min-w-0 flex-1 rounded border border-white/10 bg-bg px-2 py-1 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
          value={value?.name ?? ''}
          onChange={e => value && onChange({ ...value, name: e.target.value })}
          placeholder="e.g. Zone B (North Fence)"
        />
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={value?.active ?? true}
            onChange={e => value && onChange({ ...value, active: e.target.checked })}
            className="accent-emerald-500"
          />
          Active
        </label>
      </div>

      {/* Monitored Objects */}
      <div>
        <p className="text-[11px] text-slate-400 mb-1">Monitored Objects:</p>
        <div className="flex gap-1.5" role="group">
          {OBJECT_TYPES.map(type => {
            const selected = (value?.rules.allowed_object_types ?? []).includes(type)
            return (
              <button
                key={type}
                type="button"
                className={clsx(
                  'rounded border px-2 py-1 text-xs font-mono transition-colors',
                  selected
                    ? 'border-cyan-400/80 bg-cyan-400/20 text-cyan-200 font-semibold'
                    : 'border-white/10 bg-white/[0.02] text-slate-400 hover:text-slate-200'
                )}
                onClick={() => toggle(type)}
              >
                {type === 'HUMAN' ? 'Human' : type === 'VEHICLE' ? 'Vehicle' : 'Animal'}
              </button>
            )
          })}
        </div>
        <p className="text-[10px] text-slate-500 mt-1">
          {(value?.rules.allowed_object_types ?? []).length === 0
            ? 'Monitoring all entity classes.'
            : `Only ${(value?.rules.allowed_object_types ?? []).join(', ')} trigger risk evaluation.`}
        </p>
      </div>

      {/* Active Time Window */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <Clock className="h-3 w-3 text-cyan-400" />
            Active Time Window:
          </span>
          <span className="text-[10px] text-slate-500">24h format (UTC)</span>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="22:00"
            maxLength={5}
            value={value?.rules.active_start ?? ''}
            onChange={e =>
              value &&
              onChange({
                ...value,
                rules: { ...value.rules, active_start: e.target.value },
              })
            }
            className="w-20 rounded border border-white/10 bg-bg px-2 py-1 text-xs text-center text-slate-200 focus:border-cyan-400 focus:outline-none"
          />
          <span className="text-slate-500">to</span>
          <input
            type="text"
            placeholder="05:00"
            maxLength={5}
            value={value?.rules.active_end ?? ''}
            onChange={e =>
              value &&
              onChange({
                ...value,
                rules: { ...value.rules, active_end: e.target.value },
              })
            }
            className="w-20 rounded border border-white/10 bg-bg px-2 py-1 text-xs text-center text-slate-200 focus:border-cyan-400 focus:outline-none"
          />
        </div>

        {/* Quick window presets */}
        <div className="flex items-center gap-1.5 mt-1.5">
          <button
            type="button"
            onClick={() => setTimeWindow(undefined, undefined)}
            className="text-[10px] px-1.5 py-0.5 rounded border border-white/5 bg-white/[0.02] text-slate-400 hover:text-white"
          >
            24/7 Always
          </button>
          <button
            type="button"
            onClick={() => setTimeWindow('22:00', '05:00')}
            className="text-[10px] px-1.5 py-0.5 rounded border border-white/5 bg-white/[0.02] text-slate-400 hover:text-white"
          >
            Night (22:00–05:00)
          </button>
          <button
            type="button"
            onClick={() => setTimeWindow('06:00', '18:00')}
            className="text-[10px] px-1.5 py-0.5 rounded border border-white/5 bg-white/[0.02] text-slate-400 hover:text-white"
          >
            Day (06:00–18:00)
          </button>
        </div>
      </div>
    </div>
  )
}
