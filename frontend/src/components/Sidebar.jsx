import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  MessageSquare, 
  Files, 
  FolderOpen, 
  BarChart2, 
  Settings, 
  Server,
  Database,
  FileSearch
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { icon: MessageSquare, label: 'Chats', path: '/chat' },
  { icon: Files, label: 'Documents', path: '/documents' },
  { icon: FolderOpen, label: 'Collections', path: '/collections' },
  { icon: BarChart2, label: 'Analytics', path: '/analytics' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon-wrapper">
            <FileSearch className="logo-icon" size={18} />
          </div>
          <div className="logo-text-group">
            <span className="logo-text">QueryDoc</span>
            <span className="logo-badge">RAG</span>
          </div>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <div className="nav-group-label">Workspace</div>
        {navItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path} 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon size={14} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-metric">
          <Server size={12} />
          <span>Llama 3.1 8B</span>
        </div>
        <div className="footer-metric">
          <Database size={12} />
          <span>18 Docs (45MB)</span>
        </div>
      </div>
    </aside>
  );
}
