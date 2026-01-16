import { useState, useEffect } from 'react'
import axios from 'axios'
import { useRouter } from 'next/router'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export default function Home() {
  const router = useRouter()
  const [userId, setUserId] = useState('')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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

    try {
      const response = await axios.post(`${BACKEND_URL}/api/chat`, {
        message: userMessage,
        user_id: userId
      })
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }])
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Error: Could not reach backend'
      setError(errorMsg)
      setMessages(prev => [...prev, { role: 'assistant', content: errorMsg }])
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
        <h1 style={{ margin: 0 }}>Cortex Agent</h1>
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
