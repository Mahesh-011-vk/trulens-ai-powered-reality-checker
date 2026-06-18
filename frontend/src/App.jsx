import { useState, useEffect, useRef } from 'react'
import './App.css'
import * as api from './api.js'

// Inline SVG Icons for clean rendering without external dependencies
const ICONS = {
  dashboard: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="7" height="9" x="3" y="3" rx="1" />
      <rect width="7" height="5" x="14" y="3" rx="1" />
      <rect width="7" height="9" x="14" y="12" rx="1" />
      <rect width="7" height="5" x="3" y="16" rx="1" />
    </svg>
  ),
  model: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  history: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5M12 7v5l4 2" />
    </svg>
  ),
  settings: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  search: (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  ),
  video: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 8-6 4 6 4V8Z" />
      <rect width="14" height="12" x="2" y="6" rx="2" ry="2" />
    </svg>
  ),
  weather: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  ),
  check: (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  ),
  globe: (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </svg>
  )
};

const formatExplanation = (text) => {
  if (!text) return null;
  return text.split('\n').map((line, i) => {
    let formatted = line;
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue); text-decoration: underline; font-weight: 600;">$1</a>');
    
    if (line.startsWith('### ')) {
      return <h4 key={i} style={{ color: 'var(--text-primary)', marginTop: '16px', marginBottom: '6px', fontSize: '0.9rem', fontWeight: '800' }}>{line.replace('### ', '')}</h4>;
    } else if (line.startsWith('- ')) {
      return (
        <div key={i} style={{ paddingLeft: '8px', margin: '6px 0', fontSize: '0.82rem', color: 'var(--text-primary)', opacity: 0.9, lineHeight: '1.4', display: 'flex', gap: '6px' }}>
          <span>•</span>
          <span dangerouslySetInnerHTML={{ __html: formatted.substring(2) }} />
        </div>
      );
    } else {
      return (
        <p key={i} style={{ margin: '6px 0', fontSize: '0.82rem', color: 'var(--text-primary)', opacity: 0.8, lineHeight: '1.4' }} dangerouslySetInnerHTML={{ __html: formatted }} />
      );
    }
  });
};

function App() {
  const [text, setText] = useState('')
  const [modelType, setModelType] = useState('ml') // 'ml' (Logistic Regression) or 'cnn' (PyTorch 1D CNN)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [activeTab, setActiveTab] = useState('dashboard')
  const [email, setEmail] = useState('')
  const [emailStatus, setEmailStatus] = useState('')
  const [backendOnline, setBackendOnline] = useState(null) // null=checking, true=online, false=offline
  const [stats, setStats] = useState({ total: 0, fake: 0, real: 0, fake_ratio: 0, avg_confidence: 0 })

  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let animationFrameId;

    const tick = () => {
      const duration = video.duration;
      const currentTime = video.currentTime;
      let opacity = 0;
      if (duration && duration > 0) {
        if (currentTime < 0.5) {
          opacity = currentTime / 0.5;
        } else if (currentTime > duration - 0.5) {
          opacity = Math.max(0, (duration - currentTime) / 0.5);
        } else {
          opacity = 1;
        }
      }
      video.style.opacity = opacity;
      animationFrameId = requestAnimationFrame(tick);
    };

    const handlePlay = () => {
      animationFrameId = requestAnimationFrame(tick);
    };

    const handlePause = () => {
      cancelAnimationFrame(animationFrameId);
    };

    const handleEnded = () => {
      cancelAnimationFrame(animationFrameId);
      video.style.opacity = 0;
      setTimeout(() => {
        if (video) {
          video.currentTime = 0;
          video.play().catch(err => console.log("Video play interrupted:", err));
        }
      }, 100);
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);

    video.muted = true;
    video.playsInline = true;
    video.play().catch(err => console.log("Auto-play blocked:", err));

    return () => {
      cancelAnimationFrame(animationFrameId);
      if (video) {
        video.removeEventListener('play', handlePlay);
        video.removeEventListener('pause', handlePause);
        video.removeEventListener('ended', handleEnded);
      }
    };
  }, []);

  // ── Health check: poll every 15s ─────────────────────────────────────────
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.fetchHealth()
        setBackendOnline(true)
      } catch {
        setBackendOnline(false)
      }
    }
    checkHealth()
    const id = setInterval(checkHealth, 15000)
    return () => clearInterval(id)
  }, [])

  // ── Load history + stats on mount ────────────────────────────────────────
  const loadHistory = async () => {
    try {
      const data = await api.fetchHistory()
      setHistory(data)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  const loadStats = async () => {
    try {
      const data = await api.fetchStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  useEffect(() => {
    loadHistory()
    loadStats()
  }, [])

  const handleSendEmail = async () => {
    if (!email.trim() || !result) return
    setEmailStatus('Sending...')
    try {
      await api.sendReport({
        to_email: email,
        text: result.text,
        prediction: result.prediction,
        confidence: result.confidence,
        explanation: result.explanation,
      })
      setEmailStatus('Report sent!')
      setEmail('')
      setTimeout(() => setEmailStatus(''), 5000)
    } catch (err) {
      setEmailStatus('Error: ' + (err.message || 'Send failed'))
      console.error(err)
    }
  }

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear all prediction history?')) return
    try {
      await api.clearHistory()
      setHistory([])
      setResult(null)
      loadStats()
    } catch (err) {
      console.error('Failed to clear history:', err)
    }
  }

  const handleDeleteItem = async (e, id) => {
    e.stopPropagation()
    try {
      await api.deletePrediction(id)
      setHistory(prev => prev.filter(item => item.id !== id))
      if (result && result.id === id) setResult(null)
      loadStats()
    } catch (err) {
      console.error('Failed to delete item:', err)
    }
  }

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setEmailStatus('')
    try {
      const data = await api.analyzeNews(text, modelType)
      setResult(data)
      loadHistory()
      loadStats()
    } catch (err) {
      setError(err.message || 'Failed to connect to the analysis engine. Please ensure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleHistorySelect = (item) => {
    setText(item.text)
    setResult(item)
    setEmailStatus('')
    // Try to guess model type if the confidence schema matches
    if (item.confidence && item.confidence.REAL !== undefined) {
      // History DB just stores FAKE/REAL confidence, we preserve it
      setResult({
        text: item.text,
        prediction: item.prediction,
        confidence: item.confidence,
        explanation: item.explanation
      })
    }
  }

  const [currentDateTime, setCurrentDateTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDateTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const currentDate = currentDateTime.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  })

  const currentTime = currentDateTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  })

  return (
    <div className="dashboard-wrapper">
      <div className="video-background-wrapper">
        <video
          ref={videoRef}
          id="bg-video"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260328_065045_c44942da-53c6-4804-b734-f9e07fc22e08.mp4"
          muted
          playsInline
        />
        <div className="blurred-overlay-shape"></div>
      </div>
      {/* 1. LEFT SIDEBAR */}
      <aside className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">T</div>
          <span className="logo-text">TruthLens</span>
        </div>

        <nav className="nav-menu">
          <button 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            {ICONS.dashboard}
            <span>Dashboard</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'models' ? 'active' : ''}`}
            onClick={() => setActiveTab('models')}
          >
            {ICONS.model}
            <span>Models</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            {ICONS.history}
            <span>History</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            {ICONS.settings}
            <span>Settings</span>
          </button>
        </nav>

        <div className="user-profile">
          <div className="avatar">
            <span>MS</span>
          </div>
          <div className="user-info">
            <span className="user-name">Mahesh S</span>
            <span className="user-role">Lead Analyst</span>
          </div>
        </div>
      </aside>

      {/* 2. MAIN WORKSPACE */}
      <main className="main-content">
        
        {/* Top Header Panel */}
        <header className="content-header">
          <div className="header-left">
            <h1>Reality Checker</h1>
            <span className="current-date">{currentDate} • {currentTime}</span>
          </div>

          <div className="header-actions">
            <div className="status-widget">
              {ICONS.weather}
              <span>23°C</span>
            </div>
            <div className="search-bar">
              {ICONS.search}
              <input type="text" placeholder="Type searching..." />
            </div>
            {/* Backend health indicator */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px',
              background: 'rgba(255,255,255,0.06)', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
                background: backendOnline === null ? '#f59e0b' : backendOnline ? '#22c55e' : '#ef4444',
                boxShadow: backendOnline ? '0 0 6px #22c55e' : backendOnline === false ? '0 0 6px #ef4444' : '0 0 6px #f59e0b',
                flexShrink: 0 }} />
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)', opacity: 0.8 }}>
                {backendOnline === null ? 'Connecting...' : backendOnline ? 'API Online' : 'API Offline'}
              </span>
            </div>
            <div className="bell-icon">
              <span>🔔</span>
              <span className="badge">3</span>
            </div>
          </div>
        </header>

        {activeTab === 'dashboard' && (
          <div className="dashboard-grid">
            
            {/* Left Main Column */}
            <div className="grid-left-col">
              
              {/* Timeline/Model Settings Row */}
              <div className="model-selector-container">
                <span className="section-label">Classifier Engine</span>
                <div className="model-toggle">
                  <button 
                    className={modelType === 'ml' ? 'active' : ''} 
                    onClick={() => setModelType('ml')}
                  >
                    Classical ML (LogReg)
                  </button>
                  <button 
                    className={modelType === 'cnn' ? 'active' : ''} 
                    onClick={() => setModelType('cnn')}
                  >
                    Deep Learning (1D CNN)
                  </button>
                </div>
              </div>

              {/* Text Input Workstation */}
              <div className="workspace-card glass-card">
                <div className="card-header">
                  <h2>Claim Verification Terminal</h2>
                  <span className="char-count">{text.length} chars</span>
                </div>
                <textarea 
                  placeholder="Paste the news article body, social media claim, or headline here for real-time validation..." 
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
                <div className="workspace-footer">
                  <button 
                    className="verify-btn" 
                    onClick={handleAnalyze}
                    disabled={loading || !text.trim()}
                  >
                    {loading ? 'Analyzing Neural Pathways...' : 'Analyze Deeply'}
                  </button>
                </div>
              </div>

              {/* Error Display */}
              {error && (
                <div className="error-toast">
                  <span>⚠️</span> {error}
                </div>
              )}

              {/* Scan Results Panel */}
              {result && (
                <div className="result-card glass-card animate-slide-up">
                  <div className="result-header">
                    <h2>Verification Matrix</h2>
                    <span className={`prediction-badge ${result.prediction === 'FAKE' ? 'badge-fake' : 'badge-real'}`}>
                      {result.prediction}
                    </span>
                  </div>

                  <div className="confidence-metrics">
                    {['FAKE', 'REAL'].map(cls => {
                      const score = (result.confidence[cls] || 0) * 100;
                      return (
                        <div key={cls} className="metric-row">
                          <span className="metric-label">{cls}</span>
                          <div className="bar-track">
                            <div 
                              className={`bar-fill ${cls.toLowerCase()}`}
                              style={{ width: `${score}%` }}
                            />
                          </div>
                          <span className="metric-value">{score.toFixed(1)}%</span>
                        </div>
                      )
                    })}
                  </div>

                  {result.explanation && (
                    <div className="explanation-section" style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(0, 0, 0, 0.08)' }}>
                      <h3 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '10px', color: 'var(--text-primary)' }}>AI Analytical Explanation</h3>
                      <div className="explanation-content" style={{ display: 'flex', flexDirection: 'column', gap: '2px', textAlign: 'left' }}>
                        {formatExplanation(result.explanation)}
                      </div>
                    </div>
                  )}

                  {/* Real-time web sources from backend */}
                  {result.sources && result.sources.length > 0 && (
                    <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(0,0,0,0.08)' }}>
                      <h3 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '10px', color: 'var(--text-primary)' }}>🌐 Live Verification Sources</h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {result.sources.map((src, i) => (
                          <a key={i} href={src.url} target="_blank" rel="noopener noreferrer"
                            style={{ display: 'block', padding: '10px 12px', borderRadius: '10px',
                              background: 'rgba(255,255,255,0.45)', border: '1px solid rgba(0,0,0,0.06)',
                              textDecoration: 'none', transition: 'background 0.15s' }}
                            onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,0.7)'}
                            onMouseLeave={e => e.currentTarget.style.background='rgba(255,255,255,0.45)'}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                              <span style={{ fontSize: '0.78rem', fontWeight: '800', color: 'var(--accent-blue)' }}>{src.name}</span>
                              {src.rating && (
                                <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '2px 7px', borderRadius: '6px',
                                  background: 'rgba(0,0,0,0.07)', color: 'var(--text-primary)', textTransform: 'uppercase' }}>
                                  {src.rating}
                                </span>
                              )}
                            </div>
                            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-primary)', opacity: 0.75, lineHeight: 1.4,
                              overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                              {src.snippet}
                            </p>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Email Report Panel */}
                  <div className="email-report-section" style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(0, 0, 0, 0.08)' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: '800', marginBottom: '6px', color: 'var(--text-primary)' }}>Email Verification Report</h3>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '10px' }}>Send news verification report to inbox via Resend</p>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="email"
                        placeholder="recipient@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        style={{ flexGrow: 1, background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(0,0,0,0.06)',
                          borderRadius: '8px', padding: '8px 12px', fontSize: '0.85rem', outline: 'none', color: 'var(--text-primary)' }}
                      />
                      <button
                        onClick={handleSendEmail}
                        disabled={!email || emailStatus === 'Sending...'}
                        style={{ background: 'var(--dark-bg)', color: 'var(--dark-text)', border: 'none',
                          borderRadius: '8px', padding: '8px 16px', fontSize: '0.85rem', fontWeight: '700', cursor: 'pointer' }}
                      >
                        {emailStatus === 'Sending...' ? 'Sending...' : 'Send'}
                      </button>
                    </div>
                    {emailStatus && (
                      <p style={{ fontSize: '0.75rem', marginTop: '6px', fontWeight: '600',
                        color: emailStatus.includes('Error') || emailStatus.includes('failed') ? 'var(--status-fake)' : 'var(--status-real)' }}>
                        {emailStatus}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Files Table Section (Scanned Articles Queue) */}
              <div className="queue-card glass-card">
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h2>Verification Timeline Queue</h2>
                    <span className="badge">{history.length} items</span>
                  </div>
                  {history.length > 0 && (
                    <button 
                      onClick={handleClearHistory}
                      style={{ background: 'transparent', border: 'none', color: 'var(--status-fake)', fontSize: '0.8rem', fontWeight: '700', cursor: 'pointer', opacity: 0.8 }}
                      onMouseEnter={(e) => e.target.style.opacity = 1}
                      onMouseLeave={(e) => e.target.style.opacity = 0.8}
                    >
                      Clear All
                    </button>
                  )}
                </div>
                <div className="queue-list">
                  {history.slice(0, 5).map((item) => (
                    <div 
                      key={item.id} 
                      className="queue-item"
                      onClick={() => handleHistorySelect(item)}
                      style={{ position: 'relative', paddingRight: '48px' }}
                    >
                      <div className="queue-item-meta">
                        <span className={`prediction-dot ${item.prediction === 'FAKE' ? 'dot-fake' : 'dot-real'}`} />
                        <span className="queue-item-time">{new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      </div>
                      <div className="queue-item-body">
                        <p className="queue-text">{item.text}</p>
                      </div>
                      <div 
                        onClick={(e) => handleDeleteItem(e, item.id)}
                        className="delete-item-btn"
                        style={{ 
                          position: 'absolute', 
                          right: '16px', 
                          top: '50%', 
                          transform: 'translateY(-50%)', 
                          background: 'transparent', 
                          border: 'none', 
                          color: 'var(--text-muted)', 
                          fontSize: '1.2rem', 
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '24px',
                          height: '24px',
                          borderRadius: '6px',
                          transition: 'all 0.2s ease'
                        }}
                        onMouseEnter={(e) => { e.target.style.color = 'var(--status-fake)'; e.target.style.background = 'var(--status-fake-bg)'; }}
                        onMouseLeave={(e) => { e.target.style.color = 'var(--text-muted)'; e.target.style.background = 'transparent'; }}
                        title="Delete entry"
                      >
                        ×
                      </div>
                    </div>
                  ))}
                  {history.length === 0 && (
                    <div className="empty-state">No verification records found. Submit a claim above.</div>
                  )}
                </div>
              </div>

            </div>

            {/* Right Side Column */}
            <div className="grid-right-col">
              
              {/* Active Scan Hub (Dark glowing card with liquid sphere) */}
              <div className="scan-hub-card dark-card">
                <span className="card-tag">Neural Status</span>
                <h3>Active Analysis Hub</h3>
                
                <div className="sphere-container">
                  <div className={`analysis-sphere ${loading ? 'scanning' : ''}`}>
                    <div className="inner-glow"></div>
                  </div>
                  {loading && <div className="scanning-pulse"></div>}
                </div>

                <div className="hub-footer">
                  <span className="status-label">Engine status:</span>
                  <span className="status-val">{loading ? 'SCANNING...' : 'READY'}</span>
                </div>
              </div>

              {/* Live Stats Card */}
              <div className="trends-card glass-card">
                <div className="card-header">
                  <h3>Model Accuracy Trend</h3>
                  <span className="trend-percentage">91.0%</span>
                </div>
                <p className="trend-desc">General validation performance compared to baseline dataset.</p>

                <div className="svg-container">
                  <svg viewBox="0 0 100 30" width="100%" height="80">
                    <defs>
                      <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent-blue)" stopOpacity="0.4" />
                        <stop offset="100%" stopColor="var(--accent-blue)" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M 0 25 Q 20 10 40 18 T 80 5 T 100 12" fill="none" stroke="var(--accent-blue)" strokeWidth="1.5" />
                    <path d="M 0 25 Q 20 10 40 18 T 80 5 T 100 12 L 100 30 L 0 30 Z" fill="url(#gradient)" />
                  </svg>
                </div>

                <div className="stats-breakdown">
                  <div className="stat-item">
                    <span className="label">LogReg Accuracy</span>
                    <span className="val">90.8%</span>
                  </div>
                  <div className="stat-item">
                    <span className="label">CNN Accuracy</span>
                    <span className="val">85.7%</span>
                  </div>
                  <div className="stat-item">
                    <span className="label">Total Scans</span>
                    <span className="val">{stats.total}</span>
                  </div>
                  <div className="stat-item">
                    <span className="label">Fake Ratio</span>
                    <span className="val">{stats.fake_ratio}%</span>
                  </div>
                  <div className="stat-item">
                    <span className="label">Avg Confidence</span>
                    <span className="val">{stats.avg_confidence}%</span>
                  </div>
                </div>
              </div>

            </div>

          </div>
        )}

        {/* Models comparison Tab */}
        {activeTab === 'models' && (
          <div className="tab-panel glass-card">
            <h2>Model Architectures & Working Mechanics</h2>
            <p className="subtitle">Learn how the system detects fake news patterns in real-time</p>
            
            <div className="models-grid">
              <div className="model-card dark-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ color: 'var(--accent-blue)', fontSize: '1.25rem', fontWeight: '800' }}>TF-IDF + Logistic Regression (Classical ML)</h3>
                <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.75)', lineHeight: '1.6' }}>
                  <strong>How it works:</strong> The input text is tokenized into word and character n-grams. The Term Frequency-Inverse Document Frequency (TF-IDF) Vectorizer computes a numerical weight for each term based on its occurrence in the document relative to the entire training corpus. A Logistic Regression model then calculates the linear combination of these word weights, passing them through a Sigmoid function to output binary class probabilities.
                </p>
                <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.75)', lineHeight: '1.6' }}>
                  <strong>Strengths:</strong> Highly interpretable, extremely low latency (~4ms), and highly effective at spotting explicit sensational keywords and static fact markers.
                </p>
                <div className="model-specs" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div className="spec-row">
                    <span>Accuracy</span>
                    <span>90.86%</span>
                  </div>
                  <div className="spec-row">
                    <span>Extraction</span>
                    <span>TF-IDF Vectorizer</span>
                  </div>
                  <div className="spec-row">
                    <span>Inference Latency</span>
                    <span>~4ms</span>
                  </div>
                </div>
              </div>

              <div className="model-card dark-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ color: 'var(--accent-purple)', fontSize: '1.25rem', fontWeight: '800' }}>1D Convolutional Neural Network (Deep Learning)</h3>
                <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.75)', lineHeight: '1.6' }}>
                  <strong>How it works:</strong> Text is processed as a sequence of token IDs. An Embedding layer projects these IDs into a 50-dimensional continuous vector space. 1D Convolutional filters (kernel size=3) slide over these word embeddings, capturing local phrase contexts (such as bigrams/trigrams). Global Adaptive Max Pooling extracts the most dominant phrase indicators across the sequence, and a Fully Connected layer categorizes the dense representation.
                </p>
                <p style={{ fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.75)', lineHeight: '1.6' }}>
                  <strong>Strengths:</strong> Evaluates sequential word order and sentence phrasing. Excellent at spotting semantic and stylistic structures, clickbait tone, and patterns that simple bag-of-words methods miss.
                </p>
                <div className="model-specs" style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div className="spec-row">
                    <span>Accuracy</span>
                    <span>85.75%</span>
                  </div>
                  <div className="spec-row">
                    <span>Architecture</span>
                    <span>Conv1D + Global Max Pool</span>
                  </div>
                  <div className="spec-row">
                    <span>Inference Latency</span>
                    <span>~15ms</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="tab-panel glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2>Scan Archives</h2>
                <p className="subtitle" style={{ margin: '4px 0 0 0' }}>Browse full historical record of processed headlines and articles</p>
              </div>
              {history.length > 0 && (
                <button 
                  onClick={handleClearHistory}
                  style={{ background: 'var(--status-fake-bg)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--status-fake)', padding: '10px 20px', borderRadius: '12px', fontSize: '0.85rem', fontWeight: '700', cursor: 'pointer', transition: 'all 0.2s ease' }}
                  onMouseEnter={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.2)'}
                  onMouseLeave={(e) => e.target.style.background = 'var(--status-fake-bg)'}
                >
                  Clear Archive
                </button>
              )}
            </div>
            
            <div className="history-full-list" style={{ marginTop: '20px' }}>
              {history.map(item => (
                <div 
                  key={item.id} 
                  className="history-full-row" 
                  onClick={() => handleHistorySelect(item)}
                  style={{ position: 'relative', paddingRight: '56px' }}
                >
                  <div className="row-meta">
                    <span className={`prediction-badge ${item.prediction === 'FAKE' ? 'badge-fake' : 'badge-real'}`}>
                      {item.prediction}
                    </span>
                    <span className="timestamp">{new Date(item.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="row-text">{item.text}</p>

                  <div 
                    onClick={(e) => handleDeleteItem(e, item.id)}
                    style={{ 
                      position: 'absolute', 
                      right: '20px', 
                      top: '50%', 
                      transform: 'translateY(-50%)', 
                      background: 'transparent', 
                      border: 'none', 
                      color: 'var(--text-muted)', 
                      fontSize: '1.3rem', 
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '28px',
                      height: '28px',
                      borderRadius: '8px',
                      transition: 'all 0.2s ease'
                    }}
                    onMouseEnter={(e) => { e.target.style.color = 'var(--status-fake)'; e.target.style.background = 'var(--status-fake-bg)'; }}
                    onMouseLeave={(e) => { e.target.style.color = 'var(--text-muted)'; e.target.style.background = 'transparent'; }}
                    title="Delete entry"
                  >
                    ×
                  </div>
                </div>
              ))}
              {history.length === 0 && (
                <div className="empty-state">Your scanning archive is empty. Submit a text on the dashboard to start.</div>
              )}
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="tab-panel glass-card">
            <h2>System Configuration</h2>
            <p className="subtitle">Configure local system settings and directories</p>
            
            <div className="settings-list">
              <div className="setting-row">
                <div className="setting-desc">
                  <h3>Active Database</h3>
                  <p>SQL history database file path</p>
                </div>
                <code className="setting-val">/Users/maheshs/fakenewsdet/history.db</code>
              </div>
              <div className="setting-row">
                <div className="setting-desc">
                  <h3>ML Model Weights</h3>
                  <p>Path to classical model weights pickle</p>
                </div>
                <code className="setting-val">models/model.pkl</code>
              </div>
              <div className="setting-row">
                <div className="setting-desc">
                  <h3>CNN Model Weights</h3>
                  <p>Path to PyTorch CNN state dict weights</p>
                </div>
                <code className="setting-val">models/cnn_model.pth</code>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Row — live data from /stats endpoint */}
        <section className="dashboard-footer-metrics dark-card">
          <div className="metrics-summary">
            <h3>Analytics Breakdown</h3>
            <span className="badge">Live from API</span>
          </div>
          <div className="metrics-grid">
            <div className="metric-col">
              <span className="label">Total Scans</span>
              <span className="val">{stats.total}</span>
            </div>
            <div className="metric-col">
              <span className="label">Real Detections</span>
              <span className="val">{stats.real}</span>
            </div>
            <div className="metric-col">
              <span className="label">Fake Detections</span>
              <span className="val">{stats.fake}</span>
            </div>
            <div className="metric-col">
              <span className="label">Fake Ratio</span>
              <span className="val">{stats.fake_ratio}%</span>
            </div>
            <div className="metric-col">
              <span className="label">Avg Confidence</span>
              <span className="val">{stats.avg_confidence}%</span>
            </div>
          </div>
        </section>

      </main>
    </div>
  )
}

export default App
