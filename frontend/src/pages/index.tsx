import { useState, useEffect } from 'react'
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
          .catch(() => {})
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
      
      // Check if response contains a draft email
      const responseText = response.data.response
      if (responseText.includes('Subject:') || responseText.toLowerCase().includes('draft email')) {
        setDraftEmail(responseText)
        setShowDraft(true)
        setMessages(prev => [...prev, { role: 'assistant', content: "Here's a draft email. Review and click Send to confirm, or edit below.", draft: true }])
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: responseText }])
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error: Could not reach backend'
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
      const response = await axios.post(`${BACKEND_URL}/api/gmail/send`, {
        user_id: userId,
        to: draftEmail.match(/to\s+([^\s]+@[^\s]+)/)?.[1] || 'recipient@example.com',
        subject: draftEmail.match(/Subject:\s*(.+)/)?.[1] || 'No Subject',
        body: draftEmail.replace(/Subject:.+/i, '').trim()
      })
      
      setShowDraft(false)
      setDraftEmail('')
      setMessages(prev => [...prev, { role: 'assistant', content: 'Email sent successfully!' }])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send email')
    } finally {
      setLoading(false)
    }
  }

  if (!isLoggedIn) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        fontFamily: 'system-ui',
        backgroundColor: '#f5f5f5'
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '40px',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          textAlign: 'center'
        }}>
          <h1 style={{ marginBottom: '10px' }}>Cortex Agent</h1>
          <p style={{ color: '#666', marginBottom: '30px' }}>
            Your personal AI assistant for email, calendar, and tasks
          </p>
          <button
            onClick={handleLogin}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              backgroundColor: '#4285f4',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Sign in with Google
          </button>
          {error && <p style={{ color: 'red', marginTop: '10px' }}>{error}</p>}
        </div>
      </div>
    )
  }

  return (
    <div style={{
      maxWidth: '900px',
      margin: '0 auto',
      padding: '20px',
      fontFamily: 'system-ui',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        borderBottom: '1px solid #eee',
        paddingBottom: '15px'
      }}>
        <div>
          <h1 style={{ margin: 0 }}>Cortex Agent</h1>
          {userName && <p style={{ margin: '5px 0 0 0', color: '#666', fontSize: '14px' }}>{userName} ({userEmail})</p>}
        </div>
        <button
          onClick={handleLogout}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            backgroundColor: '#f0f0f0',
            border: '1px solid #ccc',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Logout
        </button>
      </div>

      <div style={{
        flex: 1,
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px',
        overflowY: 'auto',
        backgroundColor: '#fafafa'
      }}>
        {messages.length === 0 && (
          <p style={{ color: '#999', textAlign: 'center', marginTop: '50px' }}>
            Start a conversation with your AI assistant
          </p>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} style={{
            marginBottom: '16px',
            padding: '12px',
            borderRadius: '6px',
            backgroundColor: msg.role === 'user' ? '#e3f2fd' : '#f0f4f8',
            marginLeft: msg.role === 'user' ? '40px' : '0',
            marginRight: msg.role === 'user' ? '0' : '40px'
          }}>
            <strong style={{ color: msg.role === 'user' ? '#1976d2' : '#424242' }}>
              {msg.role === 'user' ? 'You' : 'Agent'}
            </strong>
            <p style={{ margin: '8px 0 0 0', whiteSpace: 'pre-wrap' }}>{msg.content}</p>
          </div>
        ))}
        {loading && (
          <div style={{ color: '#999', fontStyle: 'italic' }}>
            Agent is thinking...
          </div>
        )}
        
        {/* Draft Email UI */}
        {showDraft && (
          <div style={{
            marginTop: '20px',
            padding: '16px',
            backgroundColor: '#fff',
            border: '2px solid #0066cc',
            borderRadius: '8px'
          }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#0066cc' }}>Draft Email</h3>
            <textarea
              value={draftEmail}
              onChange={(e) => setDraftEmail(e.target.value)}
              style={{
                width: '100%',
                minHeight: '150px',
                padding: '12px',
                fontSize: '14px',
                fontFamily: 'monospace',
                border: '1px solid #ddd',
                borderRadius: '4px',
                resize: 'vertical'
              }}
            />
            <div style={{ marginTop: '12px', display: 'flex', gap: '8px' }}>
              <button
                onClick={handleSendDraft}
                disabled={loading}
                style={{
                  padding: '10px 24px',
                  fontSize: '14px',
                  backgroundColor: loading ? '#ccc' : '#0066cc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold'
                }}
              >
                {loading ? 'Sending...' : 'Send Email'}
              </button>
              <button
                onClick={() => { setShowDraft(false); setDraftEmail(''); }}
                style={{
                  padding: '10px 16px',
                  fontSize: '14px',
                  backgroundColor: '#f0f0f0',
                  border: '1px solid #ccc',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: '#ffebee',
          color: '#c62828',
          borderRadius: '4px',
          marginBottom: '12px'
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
          placeholder="Ask me anything..."
          disabled={loading}
          style={{
            flex: 1,
            padding: '12px',
            fontSize: '14px',
            border: '1px solid #ddd',
            borderRadius: '6px',
            fontFamily: 'system-ui'
          }}
        />
        <button
          onClick={handleSendMessage}
          disabled={loading || !message.trim()}
          style={{
            padding: '12px 24px',
            fontSize: '14px',
            backgroundColor: loading || !message.trim() ? '#ccc' : '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: loading || !message.trim() ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
