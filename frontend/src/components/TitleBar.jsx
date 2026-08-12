import React, { useState, useEffect } from 'react';
import { Minus, Square, X, Copy } from 'lucide-react';
import './TitleBar.css';

/**
 * Custom window title bar for the frameless pywebview window.
 * Provides minimize, maximize/restore, and close buttons.
 * The entire bar acts as a drag region via the `pywebview-drag-region` class.
 */
export default function TitleBar() {
  const [isMaximized, setIsMaximized] = useState(true); // starts maximized
  const [isPywebview, setIsPywebview] = useState(false);

  useEffect(() => {
    // pywebview injects window.pywebview after DOM ready
    const check = () => {
      if (window.pywebview && window.pywebview.api) {
        setIsPywebview(true);
      }
    };
    check();
    // Also listen for the pywebview ready event
    window.addEventListener('pywebviewready', check);
    // Fallback poll in case event was already fired
    const timer = setTimeout(check, 500);
    return () => {
      window.removeEventListener('pywebviewready', check);
      clearTimeout(timer);
    };
  }, []);

  // Don't render in browser mode (when not running inside pywebview)
  if (!isPywebview) return null;

  const handleMinimize = () => {
    window.pywebview.api.minimize();
  };

  const handleToggleMaximize = async () => {
    const nowMaximized = await window.pywebview.api.toggle_maximize();
    setIsMaximized(nowMaximized);
  };

  const handleClose = () => {
    window.pywebview.api.close();
  };

  return (
    <div className="titlebar pywebview-drag-region" id="custom-titlebar">
      {/* Left: app title in drag region */}
      <div className="titlebar-title">QueryDoc</div>

      {/* Right: window control buttons (must NOT be drag region) */}
      <div className="titlebar-controls">
        <button
          className="titlebar-btn titlebar-btn--minimize"
          onClick={handleMinimize}
          title="Minimize"
          id="btn-minimize"
        >
          <Minus size={14} strokeWidth={2} />
        </button>
        <button
          className="titlebar-btn titlebar-btn--maximize"
          onClick={handleToggleMaximize}
          title={isMaximized ? 'Restore' : 'Maximize'}
          id="btn-maximize"
        >
          {isMaximized ? <Copy size={12} strokeWidth={2} /> : <Square size={12} strokeWidth={2} />}
        </button>
        <button
          className="titlebar-btn titlebar-btn--close"
          onClick={handleClose}
          title="Close"
          id="btn-close"
        >
          <X size={14} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
