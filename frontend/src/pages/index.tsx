import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { useRouter } from 'next/router'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export default function Home() {
  const router = useRouter()
  const [userId, setUserId] = useState('')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Array<{ role: string; content: string, draft?: boolean }>>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [draftEmail, setDraftEmail] = useState('')
  const [showDraft, setShowDraft] = useState(false)
  const [userEmail, setUserEmail] = useState('')
  const [userName, setUserName] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  useEffect(() => {
    // Check for auth token in URL (OAuth callback)
    const { token, user_id, warning, error } = router.query
    if (error) {
      setError(decodeURIComponent(error as string))
    }
    if (warning) {
      setError(decodeURIComponent(warning as string))
    }
    if (token && user_id) {
      localStorage.setItem('token', token as string)
      localStorage.setItem('userId', user_id as string)
      setIsLoggedIn(true)
      setUserId(user_id as string)
      router.replace('/')
    } else {
      const storedToken = localStorage.getItem('token')
      const storedUserId = localStorage.getItem('userId')
      if (storedToken && storedUserId) {
        setIsLoggedIn(true)
        setUserId(storedUserId)
        // Fetch user info
        fetch(`${BACKEND_URL}/api/auth/user/${storedUserId}`)
          .then(res => res.json())
          .then(data => {
            setUserEmail(data.email || '')
            setUserName(data.name || '')
          })
          .catch(() => { })
      }
    }
  }, [router])

  const handleLogin = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/login`)
      window.location.href = response.data.auth_url
    } catch (err) {
      setError('Failed to initiate login')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    setIsLoggedIn(false)
    setUserId('')
    setMessages([])
  }

  const handleSendMessage = async () => {
    if (!message.trim() || !userId) return

    const userMessage = message
    setMessage('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)
    setError('')
    setShowDraft(false)
    setDraftEmail('')

    try {
      const response = await axios.post(`${BACKEND_URL}/api/chat`, {
        message: userMessage,
        user_id: userId
      })

      const responseText = response.data.response

      // Check if response contains a draft email format
      if (responseText.includes('Subject:') && (responseText.includes('Body:') || responseText.length > 50)) {
        setDraftEmail(responseText)
        setShowDraft(true)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: "I've drafted that email for you. You can review and edit it below.",
          draft: true
        }])
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: responseText }])
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'I encountered an error connecting to the brain. Please try again.'
      setError(errorMsg)
      setMessages(prev => [...prev, { role: 'assistant', content: errorMsg }])
    } finally {
      setLoading(false)
    }
  }

  const handleSendDraft = async () => {
    if (!draftEmail.trim() || !userId) return

    try {
      setLoading(true)

      // Extract data from draft
      const toMatch = draftEmail.match(/To:\s*([^\n]+)/i) || draftEmail.match(/to\s+([^\s]+@[^\s]+)/i)
      const subMatch = draftEmail.match(/Subject:\s*([^\n]+)/i)

      const to = toMatch ? toMatch[1].trim() : 'recipient@example.com'
      const subject = subMatch ? subMatch[1].trim() : 'No Subject'
      const body = draftEmail
        .replace(/To:.+/i, '')
        .replace(/Subject:.+/i, '')
        .replace(/Body:.+/i, '')
        .trim()

      await axios.post(`${BACKEND_URL}/api/gmail/send`, {
        user_id: userId,
        to: to,
        subject: subject,
        body: body
      })

      setShowDraft(false)
      setDraftEmail('')
      setMessages(prev => [...prev, { role: 'assistant', content: `Success! I've sent the email to ${to}.` }])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send email. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="bg-mesh">
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          padding: '20px'
        }}>
          <div className="glass-card" style={{
            padding: '60px 40px',
            maxWidth: '500px',
            width: '100%',
            textAlign: 'center'
          }}>
            <h1 className="logo-text" style={{ fontSize: '3rem', marginBottom: '16px' }}>Cortex</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', marginBottom: '40px', lineHeight: '1.6' }}>
              Your intelligent Chief of Staff. Seamlessly managing your communications, schedule, and personal knowledge.
            </p>
            <button
              onClick={handleLogin}
              className="btn-send"
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '1.1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px'
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-4.53z" />
              </svg>
              Continue with Google
            </button>
            {error && <p style={{ color: '#ef4444', marginTop: '20px', fontSize: '0.9rem' }}>{error}</p>}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-mesh">
      <div className="chat-container">
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>C</div>
            <div>
              <h2 className="logo-text" style={{ fontSize: '1.5rem' }}>Cortex</h2>
              {userName && <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Connected as {userName}</p>}
            </div>
          </div>
          <button onClick={handleLogout} className="btn-secondary">Logout</button>
        </header>

        <main className="messages-area glass-card">
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: '100px', opacity: 0.5 }}>
              <div style={{ fontSize: '3rem', marginBottom: '16px' }}>👋</div>
              <h3>How can I help you today?</h3>
              <p style={{ marginTop: '8px' }}>Ask me about your emails, calendar, or to remember something.</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message-bubble ${msg.role === 'user' ? 'message-user' : 'message-agent'}`}
            >
              <div style={{ fontWeight: 600, fontSize: '0.75rem', marginBottom: '4px', opacity: 0.8 }}>
                {msg.role === 'user' ? 'YOU' : 'CORTEX'}
              </div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
            </div>
          ))}
          {loading && (
            <div className="typing-indicator">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
          )}

          {showDraft && (
            <div className="draft-card">
              <div className="draft-header">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                Email Draft
              </div>
              <textarea
                className="draft-textarea"
                value={draftEmail}
                onChange={(e) => setDraftEmail(e.target.value)}
              />
              <div className="draft-actions">
                <button
                  onClick={handleSendDraft}
                  disabled={loading}
                  className="btn-primary"
                  style={{ flex: 1 }}
                >
                  {loading ? 'Sending...' : 'Send Message'}
                </button>
                <button
                  onClick={() => { setShowDraft(false); setDraftEmail(''); }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        {error && (
          <div style={{ margin: '12px 0', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '12px', color: '#ef4444', fontSize: '0.9rem', textAlign: 'center' }}>
            {error}
          </div>
        )}

        <footer className="input-area">
          <input
            className="input-field"
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
            placeholder="Type your message..."
            disabled={loading}
          />
          <button
            className="btn-send"
            onClick={handleSendMessage}
            disabled={loading || !message.trim()}
          >
            {loading ? '...' : 'Send'}
          </button>
        </footer>
      </div>

      <style jsx global>{`
        body {
          overflow: hidden;
        }
      `}</style>
    </div>
  )
}
