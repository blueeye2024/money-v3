
import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area, ComposedChart
} from 'recharts';
import './LabPage.css'; // Reuse Lab Styles

const SimulatorPage = () => {
    const [loading, setLoading] = useState(false);
    const [chartData, setChartData] = useState([]);
    const [trades, setTrades] = useState([]);
    const [ticker, setTicker] = useState('SOXL');
    const [stats, setStats] = useState(null);

    // Initial Load
    useEffect(() => {
        fetchData();
        fetchBacktest();
    }, [ticker]);

    const runSimulation = async () => {
        setLoading(true);
        Swal.fire({
            title: 'Simulation Running...',
            text: 'Downloading 10 days of data and calculating scores. This may take a few seconds.',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        try {
            const res = await fetch('/api/simulator/initialize', { method: 'POST' });
            const json = await res.json();

            if (json.status === 'success') {
                await fetchData();
                await fetchBacktest();
                Swal.fire('Success', `Processed ${json.processed_scores} candles.`, 'success');
            } else {
                Swal.fire('Error', 'Simulation failed.', 'error');
            }
        } catch (e) {
            Swal.fire('Error', str(e), 'error');
        } finally {
            setLoading(false);
        }
    };

    const fetchData = async () => {
        try {
            const res = await fetch(`/api/simulator/data?ticker=${ticker}`);
            const json = await res.json();
            if (json.status === 'success') {
                // Transform for Chart
                const formatted = json.data.map(d => ({
                    ...d,
                    timeStr: new Date(d.candle_time).toLocaleString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
                    close: parseFloat(d.close),
                    ma10: parseFloat(d.ma10),
                    ma30: parseFloat(d.ma30),
                    total_score: parseInt(d.total_score)
                }));
                setChartData(formatted);
            }
        } catch (e) { console.error(e); }
    };

    const fetchBacktest = async () => {
        try {
            const res = await fetch(`/api/simulator/backtest/${ticker}`);
            const json = await res.json();
            if (json.status === 'success') {
                setTrades(json.trades || []);
                calculateStats(json.trades || []);
            }
        } catch (e) { console.error(e); }
    };

    const calculateStats = (tradeList) => {
        let win = 0, loss = 0, sum = 0;
        tradeList.forEach(t => {
            if (!t.isOpen) {
                if (t.yield > 0) win++; else loss++;
                sum += parseFloat(t.yield);
            }
        });
        setStats({ win, loss, totalYield: sum.toFixed(2), count: win + loss });
    };

    return (
        <div style={{ padding: '20px', background: '#0f172a', minHeight: '100vh', color: '#fff' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                    <h2 style={{ margin: 0, color: '#38bdf8' }}>🕹️ Strategy Simulator</h2>
                    <p style={{ margin: '5px 0 0 0', color: '#94a3b8', fontSize: '0.9rem' }}>
                        Test strategies on last 10 days of Yahoo Finance data. (Independent from Live Data)
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <select
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value)}
                        style={{ padding: '10px', borderRadius: '8px', background: '#1e293b', color: '#fff', border: '1px solid #475569' }}
                    >
                        <option value="SOXL">SOXL</option>
                        <option value="SOXS">SOXS</option>
                    </select>
                    <button
                        onClick={runSimulation}
                        disabled={loading}
                        style={{
                            padding: '10px 20px', borderRadius: '8px', border: 'none',
                            background: loading ? '#475569' : '#3b82f6', color: '#fff', fontWeight: 'bold', cursor: 'pointer'
                        }}
                    >
                        {loading ? 'Running...' : '🔄 New Simulation (10 Days)'}
                    </button>
                </div>
            </div>

            {/* Content Grid */}
            <div className="lab-grid" style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px' }}>

                {/* Chart Area */}
                <div style={{ background: '#1e293b', borderRadius: '16px', padding: '20px', height: '600px', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ margin: '0 0 10px 0', color: '#e2e8f0' }}>📈 {ticker} Price & Score Flow</h3>
                    {chartData.length === 0 ? (
                        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#64748b' }}>
                            No Simulation Data. Click "New Simulation" to start.
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={chartData}>
                                <defs>
                                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis dataKey="timeStr" stroke="#94a3b8" fontSize={12} tickCount={10} minTickGap={30} />
                                <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="#94a3b8" fontSize={12} />
                                <YAxis yAxisId="right" orientation="right" domain={[0, 100]} stroke="#f472b6" fontSize={12} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f1f5f9' }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Legend />
                                <Area yAxisId="left" type="monotone" dataKey="close" stroke="#38bdf8" fillOpacity={1} fill="url(#colorPrice)" name="Price" />
                                <Line yAxisId="right" type="monotone" dataKey="total_score" stroke="#f472b6" strokeWidth={2} dot={false} name="Score" />
                                <ReferenceLine yAxisId="right" y={70} stroke="#4ade80" strokeDasharray="3 3" label="Buy (70)" />
                                <ReferenceLine yAxisId="right" y={50} stroke="#f87171" strokeDasharray="3 3" label="Sell (50)" />
                            </ComposedChart>
                        </ResponsiveContainer>
                    )}
                </div>

                {/* Backtest List Area */}
                <div style={{ background: '#1e293b', borderRadius: '16px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ margin: '0 0 10px 0', color: '#e2e8f0' }}>📊 Signal Returns</h3>

                    {stats && (
                        <div style={{ marginBottom: '15px', padding: '10px', background: '#0f172a', borderRadius: '8px', fontSize: '0.9rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                <span>Trades:</span> <span style={{ fontWeight: 'bold' }}>{stats.count}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                <span>Win/Loss:</span>
                                <span><span style={{ color: '#4ade80' }}>{stats.win}</span> / <span style={{ color: '#f87171' }}>{stats.loss}</span></span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #334155', paddingTop: '5px' }}>
                                <span>Total Yield:</span>
                                <span style={{ fontWeight: 'bold', color: stats.totalYield > 0 ? '#4ade80' : '#f87171' }}>{stats.totalYield}%</span>
                            </div>
                        </div>
                    )}

                    <div style={{ flex: 1, overflowY: 'auto', paddingRight: '5px' }}>
                        {trades.length === 0 ? (
                            <div style={{ textAlign: 'center', color: '#64748b', marginTop: '20px' }}>No trades generated.</div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                                        <th style={{ textAlign: 'left', padding: '8px' }}>Entry</th>
                                        <th style={{ textAlign: 'left', padding: '8px' }}>Exit</th>
                                        <th style={{ textAlign: 'right', padding: '8px' }}>Yield</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {trades.map((t, idx) => (
                                        <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                                            <td style={{ padding: '8px' }}>
                                                <div style={{ color: '#ef4444', fontSize: '0.75rem' }}>{new Date(t.entryTime).toLocaleDateString()}</div>
                                                <div style={{ fontWeight: 'bold' }}>${t.entryPrice}</div>
                                                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Sc: {t.entryScore}</div>
                                            </td>
                                            <td style={{ padding: '8px' }}>
                                                {t.isOpen ? (
                                                    <span style={{ color: '#fbbf24', fontWeight: 'bold' }}>HOLD</span>
                                                ) : (
                                                    <>
                                                        <div style={{ color: '#3b82f6', fontSize: '0.75rem' }}>{t.exitTime ? new Date(t.exitTime).toLocaleDateString() : '-'}</div>
                                                        <div style={{ fontWeight: 'bold' }}>${t.exitPrice}</div>
                                                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Sc: {t.exitScore}</div>
                                                    </>
                                                )}
                                            </td>
                                            <td style={{ padding: '8px', textAlign: 'right', fontWeight: 'bold', color: parseFloat(t.yield) > 0 ? '#4ade80' : '#f87171' }}>
                                                {t.yield}%
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default SimulatorPage;
