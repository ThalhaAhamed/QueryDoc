import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FileText, Trash2, RefreshCw, Upload, Search, ChevronLeft, ChevronRight,
  CheckCircle, AlertCircle, Clock, Loader, X, FileUp,
} from 'lucide-react';
import { fetchDocuments, deleteDocument, uploadDocuments, fetchIngestionJobs, reindexDocument } from '../api';
import './DocumentsView.css';

// ── helpers ──────────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const map = {
    ready:      { color: 'var(--status-success)', Icon: CheckCircle,  label: 'Ready'      },
    processing: { color: '#60A5FA',               Icon: Loader,       label: 'Processing' },
    queued:     { color: 'var(--status-warning)', Icon: Clock,        label: 'Queued'     },
    error:      { color: '#F87171',               Icon: AlertCircle,  label: 'Error'      },
  };
  const cfg = map[status] || map['error'];
  const spinning = status === 'processing';
  return (
    <span className="status-badge" style={{ color: cfg.color, borderColor: cfg.color + '44', background: cfg.color + '11' }}>
      <cfg.Icon size={10} className={spinning ? 'spin' : ''} />
      {cfg.label}
    </span>
  );
}

function JobRow({ job }) {
  const icons = {
    ready:      <CheckCircle size={14} color="var(--status-success)" />,
    processing: <Loader      size={14} color="#60A5FA" className="spin" />,
    queued:     <Clock       size={14} color="var(--status-warning)" />,
    error:      <AlertCircle size={14} color="#F87171" />,
  };
  return (
    <div className="job-row">
      <span className="job-icon">{icons[job.status] || icons.error}</span>
      <span className="job-filename" title={job.filename}>{job.filename}</span>
      <span className="job-detail">
        {job.status === 'ready' && `${job.chunk_count} chunks`}
        {job.status === 'error' && (job.error_message || 'Failed')}
        {(job.status === 'queued' || job.status === 'processing') && job.status}
      </span>
    </div>
  );
}

// ── main component ─────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function DocumentsView() {
  // Documents
  const [documents, setDocuments]     = useState([]);
  const [total, setTotal]             = useState(0);
  const [totalPages, setTotalPages]   = useState(1);
  const [page, setPage]               = useState(1);
  const [search, setSearch]           = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [isLoading, setIsLoading]     = useState(true);

  // Upload
  const [isDragging, setIsDragging]   = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef                  = useRef(null);

  // Jobs panel
  const [jobs, setJobs]               = useState([]);
  const [showJobs, setShowJobs]       = useState(false);
  const [hasActiveJobs, setHasActiveJobs] = useState(false);
  const jobPollRef                    = useRef(null);

  // Confirm delete
  const [deleteTarget, setDeleteTarget] = useState(null);

  // ── data fetching ────────────────────────────────────────────────────────

  const loadDocs = useCallback(async (p = page, s = search) => {
    setIsLoading(true);
    try {
      const data = await fetchDocuments(p, PAGE_SIZE, s);
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (e) {
      console.error('Failed to load documents:', e);
    }
    setIsLoading(false);
  }, [page, search]);

  useEffect(() => { loadDocs(page, search); }, [page, search]);

  // ── job polling ──────────────────────────────────────────────────────────

  const pollJobs = useCallback(async () => {
    try {
      const data = await fetchIngestionJobs();
      setJobs(data.jobs || []);
      const active = (data.active_count || 0) > 0;
      setHasActiveJobs(active);
      if (active) setShowJobs(true);
      // If jobs just finished, refresh document list
      if (!active && hasActiveJobs) {
        loadDocs(page, search);
      }
    } catch (e) { /* ignore */ }
  }, [hasActiveJobs, loadDocs, page, search]);

  useEffect(() => {
    pollJobs();
    jobPollRef.current = setInterval(pollJobs, 2000);
    return () => clearInterval(jobPollRef.current);
  }, [pollJobs]);

  // ── upload logic ──────────────────────────────────────────────────────────

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setShowJobs(true);
    try {
      await uploadDocuments(files);
      await pollJobs(); // immediately refresh jobs panel
    } catch (e) {
      console.error('Upload error:', e);
    }
    setIsUploading(false);
  };

  const onDragOver  = (e) => { e.preventDefault(); setIsDragging(true);  };
  const onDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const onDrop      = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  // ── search ────────────────────────────────────────────────────────────────

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const clearSearch = () => {
    setSearchInput('');
    setSearch('');
    setPage(1);
  };

  // ── delete ─────────────────────────────────────────────────────────────────

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteDocument(deleteTarget.id);
      setDeleteTarget(null);
      loadDocs(page, search);
    } catch (e) {
      console.error('Delete error:', e);
      setDeleteTarget(null);
    }
  };

  // ── reindex ────────────────────────────────────────────────────────────────

  const handleReindex = async (docId) => {
    try {
      await reindexDocument(docId);
      setShowJobs(true);
      await pollJobs();
    } catch (e) {
      console.error('Reindex error:', e);
    }
  };

  // ── active job count badge ─────────────────────────────────────────────────

  const activeCount = jobs.filter(j => j.status === 'queued' || j.status === 'processing').length;

  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="docs-container">

      {/* ── Header ── */}
      <div className="docs-header">
        <div>
          <h2 className="docs-title">Documents</h2>
          <p className="docs-subtitle">
            {total > 0 ? `${total} document${total === 1 ? '' : 's'} indexed` : 'No documents yet'}
          </p>
        </div>
        <div className="docs-header-actions">
          {jobs.length > 0 && (
            <button
              className={`btn-ghost jobs-toggle ${activeCount > 0 ? 'has-active' : ''}`}
              onClick={() => setShowJobs(v => !v)}
              title="Toggle ingestion jobs"
            >
              <Clock size={14} />
              Jobs
              {activeCount > 0 && <span className="jobs-badge">{activeCount}</span>}
            </button>
          )}
          <button
            className="btn-primary upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            <Upload size={14} />
            {isUploading ? 'Uploading…' : 'Upload'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.md,.csv"
            style={{ display: 'none' }}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      </div>

      {/* ── Jobs Panel ── */}
      {showJobs && jobs.length > 0 && (
        <div className="jobs-panel">
          <div className="jobs-panel-header">
            <span className="jobs-panel-title">
              <FileUp size={13} /> Ingestion Queue
            </span>
            <button className="btn-ghost" onClick={() => setShowJobs(false)} style={{ padding: 2 }}>
              <X size={13} />
            </button>
          </div>
          <div className="jobs-list">
            {jobs.map(job => <JobRow key={job.job_id} job={job} />)}
          </div>
        </div>
      )}

      {/* ── Drop Zone ── */}
      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={20} className="drop-icon" />
        <span className="drop-text">
          {isDragging ? 'Drop files here' : 'Drag & drop files, or click to browse'}
        </span>
        <span className="drop-hint">PDF, DOCX, TXT, MD, CSV</span>
      </div>

      {/* ── Search Bar ── */}
      <form className="search-bar" onSubmit={handleSearch}>
        <Search size={14} className="search-icon" />
        <input
          type="text"
          className="search-input"
          placeholder="Filter by filename…"
          value={searchInput}
          onChange={e => setSearchInput(e.target.value)}
        />
        {searchInput && (
          <button type="button" className="btn-ghost" onClick={clearSearch} style={{ padding: '2px 4px' }}>
            <X size={12} />
          </button>
        )}
        <button type="submit" className="btn-outline search-btn">Search</button>
      </form>

      {/* ── Document Grid ── */}
      {isLoading && documents.length === 0 ? (
        <div className="docs-loading">
          <Loader size={18} className="spin" />
          <span>Loading documents…</span>
        </div>
      ) : documents.length === 0 ? (
        <div className="docs-empty">
          <FileText size={40} className="docs-empty-icon" />
          <p>{search ? `No documents matching "${search}"` : 'Upload your first document to get started.'}</p>
        </div>
      ) : (
        <div className={`docs-grid ${isLoading ? 'is-loading' : ''}`}>
          {documents.map((doc) => (
            <div key={doc.id} className="doc-card">
              <div className="doc-card-top">
                <div className="doc-type-icon">
                  <FileText size={14} />
                </div>
                <div className="doc-card-actions">
                  <button
                    className="btn-ghost doc-action-btn"
                    title="Re-index document"
                    onClick={() => handleReindex(doc.id)}
                  >
                    <RefreshCw size={12} />
                  </button>
                  <button
                    className="btn-ghost doc-action-btn delete-btn"
                    title="Delete document"
                    onClick={() => setDeleteTarget(doc)}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              <h4 className="doc-filename" title={doc.filename}>
                {doc.filename}
              </h4>

              <div className="doc-meta">
                <div className="doc-meta-row">
                  <span className="meta-label">Size</span>
                  <span className="meta-value">{doc.file_size_display || '—'}</span>
                </div>
                <div className="doc-meta-row">
                  <span className="meta-label">Chunks</span>
                  <span className="meta-value">{doc.chunk_count ?? '—'}</span>
                </div>
                <div className="doc-meta-row">
                  <span className="meta-label">Type</span>
                  <span className="meta-value">{doc.file_type?.toUpperCase() || '—'}</span>
                </div>
                <div className="doc-meta-row">
                  <span className="meta-label">Date</span>
                  <span className="meta-value">
                    {doc.upload_date ? new Date(doc.upload_date).toLocaleDateString() : '—'}
                  </span>
                </div>
              </div>

              <div className="doc-card-footer">
                <StatusBadge status={doc.status} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="btn-ghost pag-btn"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="pag-info">
            Page {page} of {totalPages} — {total} total
          </span>
          <button
            className="btn-ghost pag-btn"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* ── Delete Confirmation Modal ── */}
      {deleteTarget && (
        <div className="modal-backdrop" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3 className="modal-title">Delete document?</h3>
            <p className="modal-body">
              <strong>{deleteTarget.filename}</strong> will be permanently removed and its embeddings deleted.
            </p>
            <div className="modal-actions">
              <button className="btn-outline" onClick={() => setDeleteTarget(null)}>Cancel</button>
              <button className="btn-danger" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
