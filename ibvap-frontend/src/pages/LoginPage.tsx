import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ShieldAlert, Eye, EyeOff, Lock, Mail, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react'
import { useAuth } from '@/hooks'
import { Button, Badge } from '@/components/ui'

const DEMO_ACCOUNTS = [
  {
    role: 'Officer',
    email: 'officer@prhaar.local',
    password: 'Officer@123',
    zone: 'Zone Alpha (Northern Perimeter)',
    badge: 'OFC-7721',
    description: 'Zone-scoped operator view with fence monitoring'
  },
  {
    role: 'Commander',
    email: 'commander@prhaar.local',
    password: 'Commander@123',
    zone: 'Full Sector Command',
    badge: 'CMD-0042',
    description: 'Sector-wide tactical oversight & multi-camera intel'
  },
  {
    role: 'System Admin',
    email: 'admin@prhaar.local',
    password: 'Admin@123',
    zone: 'Infrastructure & Audits',
    badge: 'ADM-0001',
    description: 'Full administrative, compliance & cryptographic access'
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

  const fromPath = (location.state as { from?: { pathname: string } })?.from?.pathname || '/camera/CAM-07'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    clearError()

    if (!email.trim()) {
      setFormError('Operator email is required.')
      return
    }
    if (!password) {
      setFormError('Security credential password is required.')
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
    <div className="min-h-screen w-full bg-[#080c12] flex flex-col justify-center items-center p-4 relative overflow-hidden">
      {/* Background grid */}
      <div 
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(#22d3ee 1px, transparent 1px), linear-gradient(90deg, #22d3ee 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }}
      />

      {/* Glow effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Header Branding */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="h-14 w-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.2)] mb-4">
            <ShieldAlert className="h-7 w-7 text-cyan-400" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2" aria-label="PRHAAR">
            PRH<span className="text-cyan-400">AAR</span>
            <span className="font-mono text-sm font-normal text-slate-400" lang="hi">प्रहार</span>
            <Badge variant="cyan" size="sm" className="font-mono text-[10px] uppercase tracking-wider">
              SSB India
            </Badge>
          </h1>
          <p className="text-xs font-mono text-slate-400 uppercase tracking-widest mt-1">
            Intelligent Border Video Analytics
          </p>
          <div className="flex items-center gap-2 mt-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] text-slate-400 font-mono">
              Virtual Fence & Risk Engine Component 1 Active
            </span>
          </div>
        </div>

        {/* Login Card */}
        <div className="bg-[#0d131d] border border-[#1e2d40] rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
          {/* Session Expired Banner */}
          {isSessionExpired && (
            <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-200">
                <p className="font-semibold">Security Session Expired</p>
                <p className="text-amber-300/80 mt-0.5">Please re-authenticate with your security credentials to resume surveillance operations.</p>
              </div>
            </div>
          )}

          {/* Form Error Banner */}
          {(formError || error) && (
            <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-200 font-medium">{formError || error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Operational Account / Email</span>
                <span className="text-[10px] text-slate-500 font-mono">PKI / LDAP</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                   placeholder="operator@prhaar.local"
                  className="w-full rounded-lg border border-[#1e2d40] bg-[#080c12] pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-colors"
                  required
                />
              </div>
            </div>

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
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full rounded-lg border border-[#1e2d40] bg-[#080c12] pl-9 pr-10 py-2 text-sm text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400 transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="w-full mt-2 font-medium tracking-wide justify-center"
            >
              {isLoading ? 'Authenticating...' : 'Sign In to Command Console'}
              {!isLoading && <ArrowRight className="h-4 w-4 ml-1.5" />}
            </Button>
          </form>

          {/* Quick-select Demo Users */}
          <div className="mt-8 pt-6 border-t border-[#1e2d40]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Quick Dev Profiles
              </span>
              <span className="text-[10px] font-mono text-cyan-400/80 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                MockAuth Service
              </span>
            </div>

            <div className="space-y-2">
              {DEMO_ACCOUNTS.map((acc) => {
                const isSelected = email === acc.email
                return (
                  <button
                    key={acc.email}
                    type="button"
                    onClick={() => handleSelectDemo(acc.email, acc.password)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-all duration-150 flex items-center justify-between ${
                      isSelected
                        ? 'border-cyan-500/50 bg-cyan-500/10 text-slate-100'
                        : 'border-[#1e2d40] bg-[#080c12]/60 hover:bg-[#141d2c] hover:border-slate-700 text-slate-400'
                    }`}
                  >
                    <div className="min-w-0 flex-1 pr-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-200">{acc.role}</span>
                        <span className="text-[10px] font-mono text-slate-400">({acc.badge})</span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5 font-mono">
                        {acc.email}
                      </p>
                    </div>
                    {isSelected ? (
                      <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0" />
                    ) : (
                      <span className="text-[10px] font-mono text-slate-500 shrink-0">Use</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Security Footer */}
        <div className="text-center mt-6 text-[11px] text-slate-500 flex items-center justify-center gap-2">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          <span>Restricted Government System &bull; All Access Logged & Audited</span>
        </div>
      </div>
    </div>
  )
}
