import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid } from 'recharts';
import { Activity, Clock, Database, Search } from 'lucide-react';

const mockActivityData = [
  { name: 'Mon', queries: 12 },
  { name: 'Tue', queries: 19 },
  { name: 'Wed', queries: 15 },
  { name: 'Thu', queries: 25 },
  { name: 'Fri', queries: 22 },
  { name: 'Sat', queries: 8 },
  { name: 'Sun', queries: 5 },
];

const mockLatencyData = [
  { time: '10:00', latency: 0.8 },
  { time: '12:00', latency: 1.2 },
  { time: '14:00', latency: 0.9 },
  { time: '16:00', latency: 0.7 },
  { time: '18:00', latency: 1.5 },
];

export default function AnalyticsView() {
  return (
    <div style={{ padding: 'var(--spacing-xl)', height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>Analytics Dashboard</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Monitor system performance and query metrics.</p>
      </div>

      {/* Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(124, 58, 237, 0.1)', color: 'var(--accent-primary)', borderRadius: '12px' }}>
            <Search size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Queries Today</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>106</div>
          </div>
        </div>
        
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: 'var(--status-success)', borderRadius: '12px' }}>
            <Clock size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Avg Response Time</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>0.82s</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(245, 158, 11, 0.1)', color: 'var(--status-warning)', borderRadius: '12px' }}>
            <Activity size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Active Users</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>12</div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(161, 161, 170, 0.1)', color: 'var(--text-muted)', borderRadius: '12px' }}>
            <Database size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Storage Used</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>45 MB</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 500, marginBottom: '1.5rem' }}>Query Volume (7 Days)</h3>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockActivityData}>
                <XAxis dataKey="name" stroke="var(--border-color)" tick={{ fill: 'var(--text-muted)' }} />
                <YAxis stroke="var(--border-color)" tick={{ fill: 'var(--text-muted)' }} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-color)', borderRadius: '8px' }} 
                />
                <Bar dataKey="queries" fill="var(--accent-primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '1rem', fontWeight: 500, marginBottom: '1.5rem' }}>System Latency</h3>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockLatencyData}>
                <defs>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--status-success)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--status-success)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="time" stroke="var(--border-color)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis stroke="var(--border-color)" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-color)', borderRadius: '8px' }} 
                />
                <Area type="monotone" dataKey="latency" stroke="var(--status-success)" fillOpacity={1} fill="url(#colorLatency)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
