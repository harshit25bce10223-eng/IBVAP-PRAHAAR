import { Suspense, lazy, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom'
import { AppShell } from '@/components/layout'
import { LoginPage } from '@/pages/LoginPage'
import { useAuth } from '@/hooks'

const SingleCameraDetail = lazy(() =>
  import('@/pages/SingleCameraDetail').then(m => ({ default: m.SingleCameraDetail }))
)

const Dashboard = lazy(() =>
  import('@/pages/Dashboard').then(m => ({ default: m.Dashboard }))
)

const EvidenceLedger = lazy(() =>
  import('@/pages/EvidenceLedger').then(m => ({ default: m.EvidenceLedger }))
)

const EventsPage = lazy(() =>
  import('@/pages/EventsPage').then(m => ({ default: m.EventsPage }))
)

const IncidentDetail = lazy(() =>
  import('@/pages/IncidentDetail').then(m => ({ default: m.IncidentDetail }))
)

const CameraWall = lazy(() =>
  import('@/pages/CameraWall').then(m => ({ default: m.CameraWall }))
)

const CameraHealthPage = lazy(() =>
  import('@/pages/CameraHealth').then(m => ({ default: m.CameraHealthPage }))
)

const TrackDetailPage = lazy(() =>
  import('@/pages/TrackDetail').then(m => ({ default: m.TrackDetailPage }))
)

const GISTwin = lazy(() =>
  import('@/pages/GIS').then(m => ({ default: m.GISTwin }))
)

const IncidentIntelligence = lazy(() =>
  import('@/pages/IncidentIntelligence').then(m => ({ default: m.IncidentIntelligence }))
)

const FieldIntelligence = lazy(() =>
  import('@/pages/Field').then(m => ({ default: m.FieldIntelligence }))
)

const RouteAnalysis = lazy(() =>
  import('@/pages/RouteAnalysis').then(m => ({ default: m.RouteAnalysis }))
)

const ANPRPage = lazy(() =>
  import('@/pages/ANPRPage').then(m => ({ default: m.ANPRPage }))
)

const DetectionIntelligence = lazy(() =>
  import('@/pages/DetectionIntelligence').then(m => ({ default: m.DetectionIntelligence }))
)

const CameraVehicles = lazy(() =>
  import('@/pages/CameraVehicles').then(m => ({ default: m.CameraVehicles }))
)

const VehicleDetail = lazy(() =>
  import('@/pages/VehicleDetail').then(m => ({ default: m.VehicleDetail }))
)

function ProtectedLayout() {
  const { isAuthenticated, status } = useAuth()
  const location = useLocation()

  // 'loading' and the pre-restore 'idle' both mean "session not yet resolved".
  // Treating 'idle' as unauthenticated would bounce a deep link to /login on the
  // first paint, before restoreSession() has had a chance to hydrate the token.
  if (status === 'loading' || status === 'idle') {
    return <PageSkeleton />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return (
    <AppShell>
      <Suspense fallback={<PageSkeleton />}>
        <Outlet />
      </Suspense>
    </AppShell>
  )
}

function PageSkeleton() {
  return (
    <div className="h-full w-full flex items-center justify-center bg-ssb-navy-deep">
      <div className="flex flex-col items-center gap-4 text-ssb-text-muted">
        <div className="relative">
          <div className="w-12 h-12 rounded-lg border border-ssb-green/40 bg-ssb-green/10 flex items-center justify-center animate-pulse">
            <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-ssb-green-bright">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
        </div>
        <div className="text-center font-mono">
          <div className="text-xs text-ssb-text font-semibold tracking-wider uppercase">प्रहार</div>
          <div className="text-[11px] text-ssb-text-muted mt-0.5">Initializing security session…</div>
        </div>
      </div>
    </div>
  )
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route 
        path="/login" 
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} 
      />
      <Route element={<ProtectedLayout />}>
        <Route path="/camera/:id" element={<SingleCameraDetail />} />
        <Route path="/virtual-fence" element={<SingleCameraDetail />} />
        <Route path="/health" element={<CameraHealthPage />} />
        <Route path="/camera-health" element={<CameraHealthPage />} />
        <Route path="/wall" element={<CameraWall />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/gis" element={<GISTwin />} />
        <Route path="/incident-intel" element={<IncidentIntelligence />} />
        <Route path="/field" element={<FieldIntelligence />} />
        <Route path="/route-analysis" element={<RouteAnalysis />} />
        <Route path="/evidence" element={<EvidenceLedger />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/detections" element={<DetectionIntelligence />} />
        <Route path="/incident/:correlationId" element={<IncidentDetail />} />
        <Route path="/track/:trackId" element={<TrackDetailPage />} />
        <Route path="/anpr" element={<ANPRPage />} />
        <Route path="/camera/:cameraId/vehicles" element={<CameraVehicles />} />
        <Route path="/vehicle/:vehicleId" element={<VehicleDetail />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  const { restoreSession } = useAuth()

  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
