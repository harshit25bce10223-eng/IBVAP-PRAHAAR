import { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  X,
  Camera,
  Activity,
  ShieldAlert,
  Compass,
  FileCheck,
  Cpu,
  Car,
  Layers,
  ArrowRight,
} from 'lucide-react'

interface SearchItem {
  id: string
  title: string
  subtitle: string
  category: 'CAMERAS' | 'TRACKS' | 'INCIDENTS' | 'COMMAND MODULES'
  route: string
  badge?: string
  badgeColor?: string
}

const SEARCH_DATABASE: SearchItem[] = [
  // Cameras
  { id: 'CAM-01', title: 'CAM-01 · Northern Border Pass', subtitle: 'PTZ Thermal/Optical · Sector Alpha · Active', category: 'CAMERAS', route: '/camera/CAM-01', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-02', title: 'CAM-02 · Ridge Overlook Tower', subtitle: 'Fixed High-Res · Sector Alpha · Active', category: 'CAMERAS', route: '/camera/CAM-02', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-03', title: 'CAM-03 · Riverbank Sentry Station', subtitle: 'Dual-Spectrum IR · Sector Bravo · Active', category: 'CAMERAS', route: '/camera/CAM-03', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-04', title: 'CAM-04 · Forest Outpost Alpha', subtitle: 'Low-Light Optical · Sector Bravo · Active', category: 'CAMERAS', route: '/camera/CAM-04', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-05', title: 'CAM-05 · Valley Checkpoint Road', subtitle: 'ANPR High-Speed · Sector Charlie · Active', category: 'CAMERAS', route: '/camera/CAM-05', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-06', title: 'CAM-06 · Valley Approach Bend', subtitle: 'Fixed Sensor · Sector Charlie · Degraded', category: 'CAMERAS', route: '/camera/CAM-06', badge: 'DEGRADED', badgeColor: '#F5A623' },
  { id: 'CAM-07', title: 'CAM-07 · Northern Perimeter Fence', subtitle: 'Primary Virtual Fence · Sector Alpha · 2 Active Zones', category: 'CAMERAS', route: '/camera/CAM-07', badge: 'INTRUSION', badgeColor: '#F0455B' },
  { id: 'CAM-08', title: 'CAM-08 · Highway Ingress Gate', subtitle: 'ANPR + Overview · Sector Delta · Active', category: 'CAMERAS', route: '/camera/CAM-08', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-09', title: 'CAM-09 · Border Pillar 42 Post', subtitle: 'Fixed Thermal · Sector Delta · Active', category: 'CAMERAS', route: '/camera/CAM-09', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-10', title: 'CAM-10 · Eastern Foothill Sentry', subtitle: 'Dual-Spectrum · Sector Echo · Active', category: 'CAMERAS', route: '/camera/CAM-10', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-11', title: 'CAM-11 · Restricted Valley Culvert', subtitle: 'PTZ IR · Sector Echo · Active', category: 'CAMERAS', route: '/camera/CAM-11', badge: 'ONLINE', badgeColor: '#3FCB8C' },
  { id: 'CAM-12', title: 'CAM-12 · Secondary Perimeter Fence', subtitle: 'Virtual Fence Line B · Sector Alpha · Active', category: 'CAMERAS', route: '/camera/CAM-12', badge: 'ONLINE', badgeColor: '#3FCB8C' },

  // Active Tracks
  { id: 'TRK-1042', title: 'TRK-1042 · Human Intrusion Target', subtitle: 'CAM-07 → CAM-12 · Speed 1.4 m/s · Zone Breached', category: 'TRACKS', route: '/track/TRK-1042', badge: 'CRITICAL', badgeColor: '#F0455B' },
  { id: 'TRK-0703', title: 'TRK-0703 · High-Speed Vehicle', subtitle: 'CAM-05 Checkpoint · Speed 18.2 m/s · Heading North', category: 'TRACKS', route: '/track/TRK-0703', badge: 'EVALUATED', badgeColor: '#F5A623' },
  { id: 'TRK-8781', title: 'TRK-8781 · Animal / Wildlife Sighting', subtitle: 'CAM-03 Riverbank · Speed 0.8 m/s · Natural Path', category: 'TRACKS', route: '/track/TRK-8781', badge: 'BENIGN', badgeColor: '#3FCB8C' },
  { id: 'TRK-9902', title: 'TRK-9902 · Multi-Camera Track Corridor', subtitle: 'CAM-01 → CAM-02 · Re-ID Match 94.2%', category: 'TRACKS', route: '/track/TRK-9902', badge: 'CORRELATED', badgeColor: '#2FD5E0' },

  // Correlated Incidents
  { id: 'COR-1042', title: 'COR-1042 · Perimeter Breach & Re-ID Handover', subtitle: 'CAM-07 + CAM-12 · 4 Signals · Risk Score 88/100', category: 'INCIDENTS', route: '/incident/COR-1042', badge: 'SCORE 88', badgeColor: '#F0455B' },
  { id: 'COR-1047', title: 'COR-1047 · Restricted Culvert Movement', subtitle: 'CAM-11 + CAM-09 · 2 Signals · Risk Score 64/100', category: 'INCIDENTS', route: '/incident/COR-1047', badge: 'SCORE 64', badgeColor: '#F5A623' },
  { id: 'COR-1051', title: 'COR-1051 · Unverified Vehicle Approaching Gate', subtitle: 'CAM-08 + CAM-05 · 3 Signals · Risk Score 42/100', category: 'INCIDENTS', route: '/incident/COR-1051', badge: 'SCORE 42', badgeColor: '#2FD5E0' },

  // Command Modules
  { id: 'MOD-DASH', title: 'Command Dashboard · Real-Time Overview', subtitle: 'Tactical HUD · Active Alerts · KPI Stream', category: 'COMMAND MODULES', route: '/dashboard', badge: 'CORE', badgeColor: '#2FD5E0' },
  { id: 'MOD-SUTRA', title: 'SUTRA · Correlated Incident Intelligence', subtitle: 'Multi-Camera Incident Dossiers · Signal Timelines', category: 'COMMAND MODULES', route: '/incident-intel', badge: 'सूत्र', badgeColor: '#F0455B' },
  { id: 'MOD-PRAMAAN', title: 'PRAMAAN · Evidence & Tamper-Proof Ledger', subtitle: 'Section 65B(4) Legal Certificate · SHA-256 Hashes', category: 'COMMAND MODULES', route: '/evidence', badge: 'प्रमाण', badgeColor: '#2FD5E0' },
  { id: 'MOD-PARAKH', title: 'PARAKH · Virtual Fence & Risk Engine', subtitle: 'Polygon Zones · Dwell Thresholds · Multi-Factor Risk', category: 'COMMAND MODULES', route: '/camera/CAM-07', badge: 'परख', badgeColor: '#3FCB8C' },
  { id: 'MOD-WALL', title: 'PARAKH · Live Camera Wall', subtitle: '12 Simultaneous Sensor Feeds · Fleet Detector Grid', category: 'COMMAND MODULES', route: '/wall', badge: '12 FEEDS', badgeColor: '#3FCB8C' },
  { id: 'MOD-SAKSHAM-H', title: 'SAKSHAM · Camera Health & Diagnostics', subtitle: 'Occlusion · Defocus · Viewpoint Shift · Illumination', category: 'COMMAND MODULES', route: '/camera-health', badge: 'सक्षम', badgeColor: '#2FD5E0' },
  { id: 'MOD-SAKSHAM-F', title: 'SAKSHAM · Field Intelligence & Resilience', subtitle: 'Human/Animal Classification · Offline Local Sync', category: 'COMMAND MODULES', route: '/field', badge: 'OFFLINE', badgeColor: '#F5A623' },
  { id: 'MOD-MARG-R', title: 'MARGDARSHAN · Tactical Route Analysis', subtitle: 'Risk-Aware Patrol Corridors · A/B/C Comparison', category: 'COMMAND MODULES', route: '/route-analysis', badge: 'मार्गदर्शन', badgeColor: '#3FCB8C' },
  { id: 'MOD-MARG-G', title: 'MARGDARSHAN · GIS / Digital Twin', subtitle: 'Geospatial Perimeter Map · Polygon Topology', category: 'COMMAND MODULES', route: '/gis', badge: 'GIS', badgeColor: '#2FD5E0' },
  { id: 'MOD-ANPR', title: 'ANPR · Vehicle Intelligence & OCR', subtitle: 'License Plate Recognition · Sighting History', category: 'COMMAND MODULES', route: '/anpr', badge: 'OCR', badgeColor: '#2FD5E0' },
  { id: 'MOD-EVENTS', title: 'Live Events & Signal Audit Log', subtitle: 'Full Operational Telemetry Audit Trail', category: 'COMMAND MODULES', route: '/events', badge: 'LOG', badgeColor: '#94A3B8' },
  { id: 'MOD-DET', title: 'Fleet-Wide Detection Intelligence', subtitle: 'Raw Object Observations & Confidence Metrics', category: 'COMMAND MODULES', route: '/detections', badge: 'RAW', badgeColor: '#94A3B8' },
]

interface CommandSearchModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CommandSearchModal({ isOpen, onClose }: CommandSearchModalProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50)
      setSelectedIndex(0)
    } else {
      setQuery('')
    }
  }, [isOpen])

  // Filter items
  const filtered = useMemo(() => {
    if (!query.trim()) {
      return SEARCH_DATABASE.slice(0, 10)
    }
    const q = query.toLowerCase().trim()
    return SEARCH_DATABASE.filter(item =>
      item.id.toLowerCase().includes(q) ||
      item.title.toLowerCase().includes(q) ||
      item.subtitle.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    )
  }, [query])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => (prev + 1) % Math.max(1, filtered.length))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => (prev - 1 + filtered.length) % Math.max(1, filtered.length))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filtered[selectedIndex]) {
          navigate(filtered[selectedIndex].route)
          onClose()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, filtered, selectedIndex, navigate, onClose])

  if (!isOpen) return null

  const getCategoryIcon = (category: SearchItem['category']) => {
    switch (category) {
      case 'CAMERAS':
        return <Camera size={14} className="text-[#2FD5E0]" />
      case 'TRACKS':
        return <Activity size={14} className="text-[#3FCB8C]" />
      case 'INCIDENTS':
        return <ShieldAlert size={14} className="text-[#F0455B]" />
      case 'COMMAND MODULES':
        return <Layers size={14} className="text-[#F5A623]" />
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-xl border border-[#2FD5E0]/30 bg-[#080B10] shadow-[0_0_40px_rgba(0,0,0,0.8),0_0_15px_rgba(47,213,224,0.15)] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[#1e2d40] bg-[#0d1117]">
          <Search size={18} className="text-[#2FD5E0] flex-shrink-0 animate-pulse" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            placeholder="Search cameras (CAM-07), tracks (TRK-1042), incidents, modules..."
            className="flex-1 bg-transparent text-sm font-mono text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded text-slate-400 hover:text-white"
            >
              <X size={14} />
            </button>
          )}
          <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[#1e2d40] bg-[#080c12] text-slate-400">
            ESC TO CLOSE
          </span>
        </div>

        {/* Results List */}
        <div className="max-h-[420px] overflow-y-auto p-2 divide-y divide-[#1e2d40]/40">
          {filtered.length === 0 ? (
            <div className="py-12 text-center">
              <Search size={28} className="mx-auto text-slate-600 mb-2 opacity-50" />
              <p className="text-xs font-mono text-slate-400">No matching camera, track, incident, or module found.</p>
              <p className="text-[11px] text-slate-600 mt-1">Try "CAM", "TRK", "COR", "Fence", or "Route"</p>
            </div>
          ) : (
            filtered.map((item, index) => {
              const isSelected = index === selectedIndex
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    navigate(item.route)
                    onClose()
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#2FD5E0]/15 border border-[#2FD5E0]/30 text-white'
                      : 'hover:bg-[#121a24] text-slate-300 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-7 w-7 rounded border border-white/10 bg-[#0d1117] flex items-center justify-center flex-shrink-0">
                      {getCategoryIcon(item.category)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-slate-100 truncate">
                          {item.title}
                        </span>
                        {item.badge && (
                          <span
                            className="text-[9px] font-mono font-bold px-1.5 py-px rounded border"
                            style={{
                              borderColor: `${item.badgeColor}40`,
                              backgroundColor: `${item.badgeColor}15`,
                              color: item.badgeColor,
                            }}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">
                        {item.subtitle}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 text-[10px] font-mono text-slate-500">
                    <span className="hidden sm:inline uppercase tracking-widest text-[9px] px-1.5 py-0.5 rounded bg-white/5 border border-white/5">
                      {item.category}
                    </span>
                    <ArrowRight size={13} className={isSelected ? 'text-[#2FD5E0] translate-x-0.5 transition-transform' : 'opacity-40'} />
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-[#1e2d40] bg-[#0d1117] flex items-center justify-between text-[10px] font-mono text-slate-500">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="text-[#2FD5E0]/80">PRAHAAR COMMAND INTELLIGENCE</span>
        </div>
      </div>
    </div>
  )
}
