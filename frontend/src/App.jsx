import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TitleBar from './components/TitleBar';
import ChatView from './pages/ChatView';
import DocumentsView from './pages/DocumentsView';
import AnalyticsView from './pages/AnalyticsView';
import { Moon } from 'lucide-react';

export default function App() {
  return (
    <Router>
      <div className="app-root">
        {/* Custom window controls — only visible inside pywebview */}
        <TitleBar />

        <div className="app-container">
          <Sidebar />
          
          <main className="main-workspace">
            <header className="topbar">
              <div className="topbar-left">
                {/* Could be breadcrumbs or collection selector */}
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  Personal Workspace / <strong style={{color: 'var(--text-main)', fontWeight: 500}}>All Collections</strong>
                </span>
              </div>
              <div className="topbar-right" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <button className="btn-ghost" title="Toggle Theme">
                  <Moon size={18} />
                </button>
              </div>
            </header>
            
            <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <Routes>
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<ChatView />} />
                <Route path="/documents" element={<DocumentsView />} />
                <Route path="/analytics" element={<AnalyticsView />} />
                {/* Placeholders for other routes */}
                <Route path="/collections" element={<div style={{padding: '2rem'}}>Collections - Coming Soon</div>} />
                <Route path="/settings" element={<div style={{padding: '2rem'}}>Settings - Coming Soon</div>} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </Router>
  );
}
