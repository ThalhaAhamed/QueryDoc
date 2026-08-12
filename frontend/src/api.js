const API_BASE = '/api';

export async function sendChatMessage(query, options = {}) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, ...options }),
  });
  if (!response.ok) throw new Error(`Chat API error: ${response.statusText}`);
  return response.json();
}

export async function fetchSystemStatus() {
  const response = await fetch(`${API_BASE}/status`);
  if (!response.ok) throw new Error(`Status API error: ${response.statusText}`);
  return response.json();
}

/**
 * Fetch documents with pagination and optional search.
 * @param {number} page - 1-indexed page number
 * @param {number} pageSize - Results per page
 * @param {string} search - Filename filter (optional)
 */
export async function fetchDocuments(page = 1, pageSize = 20, search = '') {
  const params = new URLSearchParams({ page, page_size: pageSize });
  if (search) params.set('search', search);
  const response = await fetch(`${API_BASE}/documents?${params}`);
  if (!response.ok) throw new Error(`Documents API error: ${response.statusText}`);
  return response.json();
}

export async function deleteDocument(docId) {
  const response = await fetch(`${API_BASE}/documents/${docId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Delete API error: ${response.statusText}`);
  return response.json();
}

/**
 * Upload files — returns immediately with job IDs (202 Accepted).
 * Poll fetchIngestionJobs() to track progress.
 */
export async function uploadDocuments(files) {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error(`Upload API error: ${response.statusText}`);
  return response.json();
}

/** Fetch all ingestion jobs (most recent first). */
export async function fetchIngestionJobs() {
  const response = await fetch(`${API_BASE}/documents/jobs`);
  if (!response.ok) throw new Error(`Jobs API error: ${response.statusText}`);
  return response.json();
}

/** Fetch a single ingestion job by ID. */
export async function fetchIngestionJob(jobId) {
  const response = await fetch(`${API_BASE}/documents/jobs/${jobId}`);
  if (!response.ok) throw new Error(`Job API error: ${response.statusText}`);
  return response.json();
}

export async function reindexDocument(docId) {
  const response = await fetch(`${API_BASE}/documents/${docId}/reindex`, { method: 'POST' });
  if (!response.ok) throw new Error(`Reindex API error: ${response.statusText}`);
  return response.json();
}
