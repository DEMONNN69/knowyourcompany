import { useMemo, useState } from 'react'
import './App.css'

type Sentiment = 'pos' | 'neg' | 'mixed' | 'neutral'
type Platform = 'reddit' | 'x' | 'glassdoor' | 'ambitionbox' | 'linkedin' | 'manual'

type SourceSignal = {
  platform: Platform
  url: string
  title?: string
  snippet?: string
  rating?: number
  review_count?: number
  sentiment?: Sentiment
}

type CompanyInsight = {
  name: string
  canonical_name: string
  website?: string
  authenticityScore?: number
  scamRisk: 'low' | 'medium' | 'high' | 'unknown'
  companyType?: string
  flags: string[]
  sources: SourceSignal[]
  lastCheckedAt: string
}

type CheckCompanyResponse = {
  success: boolean
  data?: CompanyInsight
  message?: string
  error?: string
}

const API_BASE = 'http://localhost:8000'

function App() {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [insight, setInsight] = useState<CompanyInsight | null>(null)

  const grouped = useMemo(() => {
    const groups: Record<Platform, SourceSignal[]> = {
      reddit: [],
      x: [],
      glassdoor: [],
      ambitionbox: [],
      linkedin: [],
      manual: [],
    }
    insight?.sources.forEach(s => {
      if (groups[s.platform]) groups[s.platform].push(s)
    })
    return groups
  }, [insight])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setInsight(null)
    if (!name.trim()) {
      setError('Please enter a company name.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/check-company`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const data: CheckCompanyResponse = await res.json()
      if (!data.success) {
        setError(data.error || 'Request failed')
      } else {
        setInsight(data.data || null)
      }
    } catch (err: any) {
      setError(err?.message || 'Network error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <header>
        <h1>Know Your Company</h1>
        <p>Enter a company name to analyze authenticity and signals.</p>
      </header>

      <form className="search-form" onSubmit={onSubmit}>
        <input
          type="text"
          placeholder="e.g. TCS, Capgemini, GitHub"
          value={name}
          onChange={e => setName(e.target.value)}
          aria-label="Company name"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Checking…' : 'Check Company'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {insight && (
        <div className="results">
          <section className="summary">
            <h2>Summary</h2>
            <div className="summary-grid">
              <div>
                <span className="label">Company:</span>
                <span>{insight.name}</span>
              </div>
              <div>
                <span className="label">Authenticity Score:</span>
                <span>{insight.authenticityScore ?? '—'}</span>
              </div>
              <div>
                <span className="label">Risk:</span>
                <span className={`risk ${insight.scamRisk}`}>{insight.scamRisk}</span>
              </div>
              <div>
                <span className="label">Type:</span>
                <span>{insight.companyType ?? '—'}</span>
              </div>
              <div className="flags">
                <span className="label">Flags:</span>
                {insight.flags?.length ? (
                  <ul>
                    {insight.flags.map(f => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                ) : (
                  <span>None</span>
                )}
              </div>
            </div>
          </section>

          <section className="connectors">
            <h2>Signals by Connector</h2>
            <div className="connector-grid">
              {(['glassdoor','ambitionbox','linkedin','reddit','x','manual'] as Platform[]).map((p) => (
                <ConnectorCard key={p} platform={p} signals={grouped[p]} />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function ConnectorCard({ platform, signals }: { platform: Platform; signals: SourceSignal[] }) {
  return (
    <div className="connector-card">
      <div className="connector-header">
        <span className="connector-name">{platformLabel(platform)}</span>
        <span className="badge">{signals.length}</span>
      </div>
      {signals.length === 0 ? (
        <div className="empty">No signals</div>
      ) : (
        <ul className="signal-list">
          {signals.map((s, idx) => (
            <li key={idx} className="signal-item">
              <div className="signal-title">
                {s.title || '(untitled)'}
              </div>
              <div className="signal-meta">
                {s.rating != null && <span className="pill">Rating: {s.rating}</span>}
                {s.review_count != null && <span className="pill">Reviews: {s.review_count}</span>}
                {s.sentiment && <span className={`pill sentiment ${s.sentiment}`}>Sentiment: {s.sentiment}</span>}
              </div>
              {s.snippet && <div className="signal-snippet">{s.snippet}</div>}
              <a href={s.url} target="_blank" rel="noreferrer" className="signal-link">Open source</a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function platformLabel(p: Platform): string {
  switch (p) {
    case 'glassdoor': return 'Glassdoor'
    case 'ambitionbox': return 'AmbitionBox'
    case 'linkedin': return 'LinkedIn'
    case 'reddit': return 'Reddit'
    case 'x': return 'X (Twitter)'
    case 'manual': return 'Manual'
    default: return p
  }
}

export default App
