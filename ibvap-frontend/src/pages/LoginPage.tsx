import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { useAuth } from '@/hooks'
import { Button, Badge } from '@/components/ui'

const DEMO_ACCOUNTS = [
  {
    role: 'Officer',
    email: 'officer@prhaar.local',
    password: 'Officer@123',
    zone: 'Zone Alpha — Northern Perimeter',
    badge: 'OFC-7721',
    description: 'Zone-scoped operator with fence monitoring & incident response',
  },
  {
    role: 'Commander',
    email: 'commander@prhaar.local',
    password: 'Commander@123',
    zone: 'Full Sector Command',
    badge: 'CMD-0042',
    description: 'Sector-wide tactical oversight & multi-camera intelligence',
  },
  {
    role: 'System Admin',
    email: 'admin@prhaar.local',
    password: 'Admin@123',
    zone: 'Infrastructure & Audits',
    badge: 'ADM-0001',
    description: 'Full administrative, compliance & cryptographic ledger access',
  },
]

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, status, error, clearError } = useAuth()

  const [email, setEmail] = useState('officer@prhaar.local')
  const [password, setPassword] = useState('Officer@123')
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const isSessionExpired = status === 'session_expired'
  const isLoading = status === 'loading'

  const from = (location.state as { from?: { pathname: string; search?: string } })?.from
  const fromPath = from && from.pathname !== '/' && from.pathname !== '/login'
    ? `${from.pathname}${from.search ?? ''}`
    : '/dashboard'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    clearError()

    if (!email.trim()) {
      setFormError('Operator email is required.')
      return
    }
    if (!password) {
      setFormError('Security credential is required.')
      return
    }

    try {
      await login({ email: email.trim(), password })
      navigate(fromPath, { replace: true })
    } catch {
      // Error handled by store
    }
  }

  const handleSelectDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    setFormError(null)
    clearError()
  }

  return (
    <div className="min-h-screen w-full bg-[#060A10] flex overflow-hidden relative">

      {/* ── LEFT PANEL — PRAHAAR Branding ── */}
      <div className="hidden lg:flex lg:w-[52%] flex-col items-center justify-center relative overflow-hidden">
        {/* Animated background grid */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `linear-gradient(#2FD5E0 1px, transparent 1px), linear-gradient(90deg, #2FD5E0 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
          }}
        />

        {/* Deep glow blobs */}
        <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-emerald-500/8 rounded-full blur-[100px] translate-x-1/4 translate-y-1/4 pointer-events-none" />

        {/* Scanline overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(47,213,224,0.012) 2px, rgba(47,213,224,0.012) 4px)`,
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col items-center text-center px-12 max-w-xl">
          {/* Logo */}
          <div className="relative mb-8">
            {/* Glow ring behind logo */}
            <div className="absolute inset-0 rounded-full bg-cyan-400/10 blur-2xl scale-125" />
            <div className="relative w-44 h-44 rounded-full overflow-hidden border-2 border-cyan-500/40 shadow-[0_0_60px_rgba(47,213,224,0.25),0_0_120px_rgba(47,213,224,0.08)]">
              <img
                src="/prahaar-logo.jpg"
                alt="PRAHAAR Logo"
                className="w-full h-full object-cover"
              />
            </div>
            {/* Live pulse ring */}
            <span className="absolute bottom-3 right-3 h-4 w-4 rounded-full border-2 border-[#060A10] bg-emerald-400 animate-pulse shadow-[0_0_12px_rgba(63,203,140,0.8)]" />
          </div>

          {/* PRAHAAR wordmark */}
          <div className="mb-2">
            <h1 className="text-6xl font-black tracking-tight text-white leading-none">
              PRH<span className="text-cyan-400">AAR</span>
            </h1>
            <p className="text-3xl font-bold text-cyan-300/60 tracking-[0.3em] mt-1" lang="hi">
              प्रहार
            </p>
          </div>

          {/* Tagline */}
          <p className="text-xs font-mono text-slate-400 uppercase tracking-[0.25em] mb-1">
            Intelligent Border Video Analytics Platform
          </p>
          <p className="text-[11px] font-mono text-slate-500 tracking-wider mb-8">
            Sashastra Seema Bal · Smart India Hackathon 2024
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap gap-2 justify-center mb-10">
            {[
              'Virtual Fence Engine',
              'AI Risk Scoring',
              'Multi-Camera Tracking',
              'ANPR Intelligence',
              'Tamper-Evident Ledger',
              'GIS Digital Twin',
            ].map((f) => (
              <span
                key={f}
                className="text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5 text-cyan-300/70"
              >
                {f}
              </span>
            ))}
          </div>

          {/* Status bar */}
          <div className="w-full rounded-xl border border-[#1e2d40] bg-[#0d131d]/60 px-5 py-3 flex items-center justify-between backdrop-blur">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(63,203,140,0.8)]" />
              <span className="text-[11px] font-mono text-emerald-300">SYSTEM OPERATIONAL</span>
            </div>
            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
              <span>7 Components Active</span>
              <span className="text-slate-600">|</span>
              <span>PHASE 2</span>
            </div>
          </div>

          {/* Bottom classification strip */}
          <div className="mt-8 text-[9px] font-mono text-slate-600 uppercase tracking-[0.3em] flex items-center gap-3">
            <span className="h-px w-8 bg-slate-700" />
            <span>RESTRICTED GOVERNMENT SYSTEM</span>
            <span className="h-px w-8 bg-slate-700" />
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL — Login Form ── */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-10 relative">
        {/* Mobile grid bg */}
        <div
          className="absolute inset-0 opacity-[0.03] pointer-events-none lg:hidden"
          style={{
            backgroundImage: `linear-gradient(#2FD5E0 1px, transparent 1px), linear-gradient(90deg, #2FD5E0 1px, transparent 1px)`,
            backgroundSize: '40px 40px',
          }}
        />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-80 h-80 bg-cyan-500/8 rounded-full blur-3xl pointer-events-none lg:hidden" />

        <div className="w-full max-w-sm relative z-10">

          {/* Mobile logo + title (hidden on desktop) */}
          <div className="flex flex-col items-center text-center mb-8 lg:hidden">
            <div className="relative mb-4">
              <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-cyan-500/40 shadow-[0_0_30px_rgba(47,213,224,0.2)]">
                <img src="/prahaar-logo.jpg" alt="PRAHAAR" className="w-full h-full object-cover" />
              </div>
              <span className="absolute bottom-1 right-1 h-3 w-3 rounded-full bg-emerald-400 border-2 border-[#060A10] animate-pulse" />
            </div>
            <h1 className="text-3xl font-black text-white">
              PRH<span className="text-cyan-400">AAR</span>
            </h1>
            <p className="text-sm text-cyan-300/50 font-bold tracking-[0.3em]" lang="hi">प्रहार</p>
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mt-1">
              Intelligent Border Video Analytics
            </p>
          </div>

          {/* Card */}
          <div className="bg-[#0d131d] border border-[#1e2d40] rounded-2xl p-6 shadow-2xl">
            <div className="mb-6">
              <h2 className="text-base font-semibold text-white">Command Console Access</h2>
              <p className="text-[11px] text-slate-500 mt-0.5 font-mono">Authenticate to begin surveillance operations</p>
            </div>

            {/* Session expired banner */}
            {isSessionExpired && (
              <div className="mb-5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 flex items-start gap-3">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs text-amber-200">
                  <p className="font-semibold">Security Session Expired</p>
                  <p className="text-amber-300/80 mt-0.5">Re-authenticate to resume surveillance operations.</p>
                </div>
              </div>
            )}

            {/* Error banner */}
            {(formError || error) && (
              <div className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 flex items-start gap-3">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-xs text-red-200 font-medium">{formError || error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>Operator Account</span>
                  <span className="text-[10px] text-slate-500 font-mono">PKI / LDAP</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setFormError(null); clearError() }}
                    placeholder="operator@prhaar.local"
                    className="w-full rounded-lg border border-[#1e2d40] bg-[#080c12] pl-9 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 transition-colors"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>Security Passphrase</span>
                  <span className="text-[10px] text-slate-500 font-mono">End-to-End Encrypted</span>
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Lock className="h-4 w-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setFormError(null); clearError() }}
                    placeholder="••••••••••••"
                    className="w-full rounded-lg border border-[#1e2d40] bg-[#080c12] pl-9 pr-10 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 transition-colors"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isLoading}
                className="w-full mt-2 font-semibold tracking-wide justify-center"
              >
                {isLoading ? 'Authenticating...' : 'Access Command Console'}
                {!isLoading && <ArrowRight className="h-4 w-4 ml-1.5" />}
              </Button>
            </form>

            {/* Demo accounts */}
            <div className="mt-6 pt-5 border-t border-[#1e2d40]">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Demo Profiles
                </span>
                <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                  Judge Access
                </span>
              </div>

              <div className="space-y-1.5">
                {DEMO_ACCOUNTS.map((acc) => {
                  const isSelected = email === acc.email
                  return (
                    <button
                      key={acc.email}
                      type="button"
                      onClick={() => handleSelectDemo(acc.email, acc.password)}
                      className={`w-full text-left p-2.5 rounded-xl border transition-all duration-150 flex items-center justify-between gap-2 ${
                        isSelected
                          ? 'border-cyan-500/50 bg-cyan-500/10 text-slate-100'
                          : 'border-[#1e2d40] bg-[#080c12]/60 hover:bg-[#141d2c] hover:border-slate-700 text-slate-400'
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-200">{acc.role}</span>
                          <span className="text-[10px] font-mono text-slate-500">({acc.badge})</span>
                        </div>
                        <p className="text-[10px] text-slate-500 truncate mt-0.5">{acc.description}</p>
                      </div>
                      {isSelected ? (
                        <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0" />
                      ) : (
                        <span className="text-[10px] font-mono text-slate-600 shrink-0">Select</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center mt-5 text-[10px] text-slate-600 flex flex-col items-center gap-1">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-3 w-3 text-emerald-400/60" />
              <span>Restricted Government System · All Access Logged & Audited</span>
            </div>
            <span className="text-slate-700 font-mono">Team Apex Code · SIH 2024 · IBVAP-PRAHAAR</span>
          </div>
        </div>
      </div>

      {/* Vertical divider between panels */}
      <div className="hidden lg:block absolute left-[52%] top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-cyan-500/20 to-transparent" />
    </div>
  )
}
