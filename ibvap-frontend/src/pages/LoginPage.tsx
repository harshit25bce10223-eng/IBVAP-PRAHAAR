import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { useAuth } from '@/hooks'
import { Button } from '@/components/ui'
import './login.css'

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

/** Decorative brand artwork only; no connection to camera or inference state. */
function LoginLandscape() {
  return (
    <div className="login-landscape" aria-hidden="true">
      <svg viewBox="0 0 560 200" fill="none" focusable="false">
        <defs>
          <linearGradient id="login-sky" x2="0" y2="200" gradientUnits="userSpaceOnUse">
            <stop stopColor="#253b2e" /><stop offset="1" stopColor="#101c17" />
          </linearGradient>
          <linearGradient id="login-beam" x1="136" y1="70" x2="520" y2="70" gradientUnits="userSpaceOnUse">
            <stop stopColor="#dbe3b5" stopOpacity=".32" /><stop offset="1" stopColor="#dbe3b5" stopOpacity="0" />
          </linearGradient>
          <radialGradient id="login-moon">
            <stop stopColor="#e4e5c6" stopOpacity=".15" /><stop offset="1" stopColor="#e4e5c6" stopOpacity="0" />
          </radialGradient>
        </defs>
        <path fill="url(#login-sky)" d="M0 0h560v200H0z" />
        <circle cx="434" cy="44" r="56" fill="url(#login-moon)" />
        <circle cx="434" cy="44" r="13" fill="#dbe0bc" opacity=".8" />
        <g fill="#dbe0bc" opacity=".55">
          <circle cx="54" cy="29" r="1" /><circle cx="252" cy="22" r="1.2" />
          <circle cx="338" cy="48" r="1" /><circle cx="499" cy="25" r="1" />
        </g>
        <path d="M0 143 78 104 127 127 218 48 269 104 329 69 398 121 457 94 560 144V200H0Z" fill="#3d5340" />
        <path d="m190 79 28-31 28 31-18-6-10 9-12-11Z" fill="#a7b593" opacity=".65" />
        <path d="M0 165 62 139 149 165 265 118 356 150 435 115 560 158V200H0Z" fill="#273e2b" />
        <path d="M0 185Q114 149 224 177T440 164T560 185V200H0Z" fill="#152a20" />
        <path d="M352 141q-80 18-25 30t-23 29" stroke="#99ad90" strokeWidth="3" opacity=".4" />
        <g className="login-light-beam">
          <path d="M136 67 554 2V166Z" fill="url(#login-beam)" />
          <path d="m136 67 418-65" stroke="#dbe3b5" strokeOpacity=".13" />
        </g>
        <g stroke="#acb78c" strokeWidth="2" strokeLinejoin="round">
          <path d="m98 177 11-72h29l13 72M105 129l38 31m-4-38-36 38M111 105l28 24" />
          <path d="M96 105h55V79H96z" fill="#14281e" />
          <path d="m90 79 33-18 35 18Z" fill="#354d36" />
          <path d="M104 88h11v10h-11zm27 0h11v10h-11z" fill="#bdcb91" stroke="none" />
          <path d="M124 60V43m-6 0h12" />
          <path d="m132 65 16-4 3 6-17 5Z" fill="#c2cb99" />
        </g>
        <g stroke="#c2cb99" strokeWidth="1.4" fill="none" className="login-signal">
          <path d="M132 39q8 4 8 11m-4-18q12 5 12 17" />
        </g>
        <g fill="#0d2118">
          <path d="m43 123-17 34h10l-16 21h46l-16-21h10Zm440-8-18 36h11l-17 25h48l-17-25h11Zm41 24-14 28h8l-13 19h38l-13-19h8Z" />
        </g>
        <path d="M18 188h524" stroke="#c2cb99" strokeOpacity=".15" />
      </svg>
      <div className="login-landscape-caption"><span>Inspired by the PRAHAAR emblem</span><span>Illustrative scene</span></div>
    </div>
  )
}

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
    : '/demo'

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
    <div className="login-experience min-h-screen w-full bg-bg flex overflow-hidden relative">

      {/* ── LEFT PANEL — PRAHAAR Branding ── */}
      <div className="hidden lg:flex lg:w-[52%] flex-col items-center justify-center relative overflow-hidden">
        {/* Animated background grid */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `linear-gradient(#c2cb99 1px, transparent 1px), linear-gradient(90deg, #c2cb99 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
          }}
        />

        {/* Deep glow blobs */}
        <div className="absolute top-0 left-0 w-[600px] h-[600px] bg-brand/10 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-emerald-500/8 rounded-full blur-[100px] translate-x-1/4 translate-y-1/4 pointer-events-none" />

        {/* Scanline overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(194,203,153,0.012) 2px, rgba(194,203,153,0.012) 4px)`,
          }}
        />

        {/* Content */}
        <div className="login-brand-content relative z-10 flex flex-col items-center text-center px-12 py-8 max-w-xl">
          {/* Logo */}
          <div className="relative mb-4">
            {/* Glow ring behind logo */}
            <div className="absolute inset-0 rounded-full bg-brand/10 blur-2xl scale-125" />
            <div className="relative w-24 h-24 rounded-full overflow-hidden border-2 border-brand/40 shadow-[0_0_60px_rgba(194,203,153,0.15)]">
              <img
                src="/prahaar-logo.jpg"
                alt="PRAHAAR Logo"
                className="w-full h-full object-cover"
              />
            </div>
          </div>

          {/* PRAHAAR wordmark */}
          <div className="login-wordmark mb-2">
            <span className="login-eyebrow">TEAM APEX CODE / SIH 2026</span>
            <h1 className="text-5xl font-black tracking-tight text-white leading-none">
              PRA<span className="text-brand">HAAR</span>
            </h1>
            <p className="text-3xl font-bold text-brand tracking-[0.3em] mt-1" lang="hi">
              प्रहार
            </p>
          </div>

          {/* Tagline */}
          <p className="text-xs font-mono text-slate-400 uppercase tracking-[0.25em] mb-1">
            Intelligent Border Video Analytics Platform
          </p>
          <p className="text-[11px] font-mono text-slate-500 tracking-wider mb-6">
            Sashastra Seema Bal · Smart India Hackathon 2026
          </p>

          <LoginLandscape />

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
            backgroundImage: `linear-gradient(#c2cb99 1px, transparent 1px), linear-gradient(90deg, #c2cb99 1px, transparent 1px)`,
            backgroundSize: '40px 40px',
          }}
        />
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-80 h-80 bg-brand/8 rounded-full blur-3xl pointer-events-none lg:hidden" />

        <div className="w-full max-w-sm relative z-10">

          {/* Mobile logo + title (hidden on desktop) */}
          <div className="flex flex-col items-center text-center mb-8 lg:hidden">
            <div className="relative mb-4">
              <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-brand/40 shadow-[0_0_30px_rgba(194,203,153,0.2)]">
                <img src="/prahaar-logo.jpg" alt="PRAHAAR" className="w-full h-full object-cover" />
              </div>
              <span className="absolute bottom-1 right-1 h-3 w-3 rounded-full bg-emerald-400 border-2 border-bg animate-pulse" />
            </div>
            <h1 className="text-3xl font-black text-white">
              PRA<span className="text-brand">HAAR</span>
            </h1>
            <p className="text-sm text-brand font-bold tracking-[0.3em]" lang="hi">प्रहार</p>
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mt-1">
              Intelligent Border Video Analytics
            </p>
          </div>

          {/* Card */}
          <div className="login-access-card bg-surface border border-border rounded-2xl p-6 shadow-2xl">
            <div className="mb-6">
              <div className="login-form-eyebrow"><Lock size={13} aria-hidden="true" /> ACCOUNT ACCESS</div>
              <h2 className="text-2xl font-semibold tracking-tight text-white">Welcome to PRAHAAR.</h2>
              <p className="text-sm text-slate-400 mt-2">Sign in to your workspace, or choose a demo profile below.</p>
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
                    className="w-full rounded-lg border border-border bg-bg pl-9 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 transition-colors"
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
                    className="w-full rounded-lg border border-border bg-bg pl-9 pr-10 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/50 transition-colors"
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
            <div className="mt-6 pt-5 border-t border-border">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Demo Profiles
                </span>
                <span className="text-[10px] font-mono text-brand/80 bg-brand/10 px-2 py-0.5 rounded border border-brand/20">
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
                          ? 'border-brand/50 bg-brand/10 text-slate-100'
                          : 'border-border bg-bg/60 hover:bg-ssb-navy-raised hover:border-slate-700 text-slate-400'
                      }`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-slate-200">{acc.role}</span>
                          <span className="text-[10px] font-mono text-slate-500">({acc.badge})</span>
                        </div>
                        <p className="text-[11px] leading-relaxed text-slate-400 whitespace-normal mt-0.5">{acc.description}</p>
                      </div>
                      {isSelected ? (
                        <CheckCircle2 className="h-4 w-4 text-brand shrink-0" />
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
            <span className="text-slate-700 font-mono">Team Apex Code · SIH 2026 · IBVAP-PRAHAAR</span>
          </div>
        </div>
      </div>

      {/* Vertical divider between panels */}
      <div className="hidden lg:block absolute left-[52%] top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-brand/20 to-transparent" />
    </div>
  )
}
