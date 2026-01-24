
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Bar, Area } from 'recharts';
import Swal from 'sweetalert2';

const LabPage = () => {
    const [ticker, setTicker] = useState('SOXL');
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [simId, setSimId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState([]);

    const runSimulation = async () => {
        setLoading(true);
        setResults([]);
        try {
            const res = await fetch('/api/lab/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, date })
            });
            const data = await res.json();
            if (data.status === 'success') {
                setSimId(data.simulation_id);
                pollResults(data.simulation_id);
            } else {
                Swal.fire('Error', data.message, 'error');
                setLoading(false);
            }
        } catch (e) {
            console.error(e);
            setLoading(false);
        }
    };

    const pollResults = (id) => {
        let attempts = 0;
        const maxAttempts = 20; // 40 seconds
        const interval = setInterval(async () => {
            attempts++;
            try {
                const res = await fetch(`/api/lab/results/${id}`);
                const json = await res.json();
                if (json.status === 'success' && json.data && json.data.length > 0) {
                    setResults(json.data);
                    // Continue polling? If we think it's done? 
                    // Usually we don't know if it's "Done". 
                    // But if we get data, we show it.
                    // For now, let's keep polling until results stabilize or stop after some time?
                    // Or just assumes if we get > 10 rows it's started populating.
                    if (json.data.length > 200 || attempts > 15) {
                        clearInterval(interval);
                        setLoading(false);
                    }
                }
            } catch (e) {
                console.error(e);
            }
            if (attempts >= maxAttempts) {
                clearInterval(interval);
                setLoading(false);
            }
        }, 2000);
    };

    return (
        <div style={{ padding: '20px', minHeight: '100vh', background: '#0f172a', color: '#fff' }}>
            <h2 style={{ borderBottom: '1px solid #334155', paddingBottom: '10px', color: '#38bdf8' }}>🧪 청안 액션플랜 실험실 (Lab)</h2>

            <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', marginTop: '20px', display: 'flex', gap: '20px', alignItems: 'center' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Ticker</label>
                    <select value={ticker} onChange={e => setTicker(e.target.value)} style={{ padding: '8px', borderRadius: '6px', background: '#0f172a', color: '#fff', border: '1px solid #475569' }}>
                        <option value="SOXL">SOXL</option>
                        <option value="SOXS">SOXS</option>
                        <option value="UPRO">UPRO</option>
                        <option value="TQQQ">TQQQ</option>
                    </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Target Date (KST)</label>
                    <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{ padding: '8px', borderRadius: '6px', background: '#0f172a', color: '#fff', border: '1px solid #475569' }} />
                </div>

                <button onClick={runSimulation} disabled={loading} style={{
                    padding: '10px 20px', background: loading ? '#475569' : '#3b82f6', color: '#fff',
                    border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: loading ? 'default' : 'pointer', marginTop: '15px'
                }}>
                    {loading ? 'Simulating...' : 'Run Simulation'}
                </button>
            </div>

            {results.length > 0 && (
                <div style={{ marginTop: '30px' }}>
                    <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', height: '400px' }}>
                        <h4 style={{ margin: '0 0 20px 0', color: '#fbbf24' }}>Simulated Score Analysis</h4>
                        <ResponsiveContainer width="100%" height="90%">
                            <ComposedChart data={results}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                <XAxis dataKey="candle_time" tickFormatter={(t) => t.substring(11, 16)} stroke="#94a3b8" />
                                <YAxis yAxisId="left" domain={[-100, 100]} stroke="#cbd5e1" label={{ value: 'Score', angle: -90, position: 'insideLeft' }} />
                                <YAxis yAxisId="right" orientation="right" stroke="#f472b6" domain={['auto', 'auto']} />
                                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                                <Legend />
                                <Area yAxisId="left" type="monotone" dataKey="total_score" fill="#3b82f6" stroke="#3b82f6" fillOpacity={0.3} name="Total Score" />
                                <Line yAxisId="right" type="monotone" dataKey="price" stroke="#f472b6" nonScalingStroke strokeWidth={2} dot={false} name="Price" />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>

                    <div style={{ marginTop: '20px', overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead>
                                <tr style={{ background: '#334155', color: '#fff' }}>
                                    <th style={thStyle}>Time</th>
                                    <th style={thStyle}>Price</th>
                                    <th style={thStyle}>Score</th>
                                    <th style={thStyle}>RSI(Scr)</th>
                                    <th style={thStyle}>MACD(Scr)</th>
                                    <th style={thStyle}>Total</th>
                                    <th style={thStyle}>Signal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {results.map((row, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid #334155', background: idx % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                                        <td style={tdStyle}>{row.candle_time.substring(5, 16)}</td>
                                        <td style={tdStyle}>${row.price}</td>
                                        <td style={{ ...tdStyle, color: row.total_score >= 60 ? '#4ade80' : row.total_score <= 30 ? '#f87171' : '#fff' }}>
                                            {row.total_score}
                                        </td>
                                        <td style={tdStyle}>{row.rsi}</td>
                                        <td style={tdStyle}>{row.macd}</td>
                                        <td style={tdStyle}>{row.total_score}</td>
                                        <td style={{ ...tdStyle, color: '#fbbf24' }}>{row.signal_step}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

const thStyle = { padding: '12px', textAlign: 'left' };
const tdStyle = { padding: '10px' };

export default LabPage;
