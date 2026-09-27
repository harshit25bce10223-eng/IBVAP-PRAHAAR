// Barrel re-export for all domain types
export * from './auth'
export * from './surveillance'
export * from './geo'
export * from './api'
export * from './camera'
export * from './zone'
export * from './track'
export * from './risk'
export * from './incident'
export * from './cameraHealth'
export * from './evidence'
export * from './eventCorrelation'
export * from './detection'
export * from './tracking'
export * from './shell'
// Command Center (Main Command Dashboard, Sub-Component 2)
export * from './commandDashboard'
// GIS / Digital Twin (SIH screenshot 4)
export * from './gis'
// Incident Intelligence (SIH screenshot 5)
export * from './incidentIntelligence'
// Field Intelligence & Resilience (SIH screenshot 6)
export * from './fieldResilience'
// Route Risk Analysis (USP 5 - SIH screenshot 7)
export * from './routeAnalysis'
// ANPR + Vehicle Intelligence (Component 7)
export * from './anpr'
// Explicit re-exports resolve type clashes:
// - `Reliability`: between ./track and ./eventCorrelation
// - `TrackObservation`: keep Component 1's simulation type canonical on the barrel,
//   and provide `TrackingObservation` / `TrackObservationRecord` for Component 6.
export type { Reliability, TrackObservation } from './track'
export type { TrackObservation as TrackingObservation, TrackObservationRecord } from './tracking'
