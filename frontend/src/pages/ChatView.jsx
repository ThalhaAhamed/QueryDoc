import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, FileText, UploadCloud, ChevronDown } from 'lucide-react';
import { sendChatMessage } from '../api';
import './ChatView.css';

export default function ChatView() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [currentSources, setCurrentSources] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setIsLoading(true);

    try {
      const result = await sendChatMessage(userQuery);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: result.response
      }]);
      setCurrentSources(result.sources || []);
      setMetadata(result.metadata);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to connect to backend.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-layout">
      {/* 70% Conversation Area */}
      <div className="chat-main">
        <div className="messages-area">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2 className="empty-title">Welcome back</h2>
              <div className="empty-grid">
                <div className="empty-section">
                  <div className="empty-label">Search across:</div>
                  <div className="empty-stat">• 18 Documents</div>
                  <div className="empty-stat">• 4 Collections</div>
                </div>
                <div className="empty-section">
                  <div className="empty-label">Suggested queries</div>
                  <button className="empty-btn" onClick={() => setInput("Summarize my resume")}>Summarize my resume</button>
                  <button className="empty-btn" onClick={() => setInput("Compare research papers")}>Compare research papers</button>
                  <button className="empty-btn" onClick={() => setInput("Find every AI project")}>Find every AI project</button>
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="message-row">
                <div className="message-role">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                <div className="message-content">
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <div className="markdown-body"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                  )}
                </div>
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="message-row">
              <div className="message-role">Assistant</div>
              <div className="message-content text-muted">Retrieving context...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Dense Single-Row Input */}
        <div className="input-row-container">
          <div className="input-row">
            <button className="btn-icon" title="Upload Document">
              <UploadCloud size={16} />
            </button>
            <button className="btn-select">
              All Collections <ChevronDown size={14} />
            </button>
            <button className="btn-select">
              Llama 3.1 <ChevronDown size={14} />
            </button>
            <textarea
              className="input-textarea"
              placeholder="Ask a question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button 
              className="btn-send" 
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* 30% Sources & Metadata Panel */}
      <aside className="sources-panel">
        <div className="panel-section metadata-section">
          <div className="panel-header">Retrieval Metadata</div>
          <div className="metadata-grid">
            <div className="meta-item">
              <span className="meta-label">Model</span>
              <span className="meta-val">Llama 3.1</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Latency</span>
              <span className="meta-val">{metadata?.total_time_ms ? (metadata.total_time_ms / 1000).toFixed(2) : '—'} s</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Sources</span>
              <span className="meta-val">{metadata?.chunks_retrieved || 0}</span>
            </div>
          </div>
        </div>

        <div className="panel-section">
          <div className="panel-header">Sources</div>
          <div className="sources-list">
            {currentSources.length === 0 ? (
              <div className="text-muted" style={{fontSize: '0.8rem'}}>No sources retrieved yet.</div>
            ) : (
              currentSources.map((src, idx) => (
                <div key={idx} className="source-row">
                  <div className="source-row-top">
                    <FileText size={14} className="text-muted" />
                    <span className="source-filename">{src.document}</span>
                    <span className="source-score">{(src.similarity_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="source-preview">
                    {src.text_preview}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
