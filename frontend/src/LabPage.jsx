
import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area, ComposedChart
} from 'recharts';
import './LabPage.css'; // Import Responsive CSS

// Helper: Calculate Statistics
// Helper: Calculate Statistics
const calculateStats = (data, buyScore, sellScore) => {
    if (!data || data.length === 0) return null;

    let maxPrice = -Infinity, minPrice = Infinity, sumPrice = 0;
    let maxScore = -Infinity, minScore = Infinity, sumScore = 0;
    let buyCount = 0, sellCount = 0;
    let hasPosition = false;

    data.forEach(d => {
        const p = d.close;
        const s = d.total_score;

        if (p > maxPrice) maxPrice = p;
        if (p < minPrice) minPrice = p;
        sumPrice += p;

        if (s > maxScore) maxScore = s;
        if (s < minScore) minScore = s;
        sumScore += s;

        // Trade Cycle Count Logic
        if (!hasPosition) {
            // Check Buy
            if (s >= buyScore) {
                buyCount++;
                hasPosition = true;
            }
        } else {
            // Check Sell
            if (s <= sellScore) {
                sellCount++;
                hasPosition = false;
            }
        }
    });

    return {
        maxPrice, minPrice, avgPrice: (sumPrice / data.length).toFixed(2),
        maxScore, minScore, avgScore: (sumScore / data.length).toFixed(1),
        buyCount, sellCount
    };
};

const AnalysisPanel = ({ ticker, data, buyScore, sellScore, period = '5m' }) => {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchBacktest = async () => {
            setLoading(true);
            try {
                // Use buyScore/sellScore from props for real-time preview
                const res = await fetch(`/api/lab/backtest/${ticker}?period=${period}&buy_score=${buyScore}&sell_score=${sellScore}`);
                if (res.ok) {
                    const result = await res.json();
                    setTrades(result.trades || []);
                }
            } catch (e) {
                console.error("Backtest Fetch Error:", e);
            } finally {
                setLoading(false);
            }
        };
        fetchBacktest();
    }, [ticker, buyScore, sellScore, period]);

    if (!data || data.length === 0) return null;
    const stats = calculateStats(data, buyScore, sellScore);

    return (
        <div style={{ flex: 1, minWidth: '0', background: '#1e293b', padding: '15px', borderRadius: '12px', fontSize: '0.85rem' }}>
            <h4 style={{ marginTop: 0, marginBottom: '10px', color: '#94a3b8', borderBottom: '1px solid #334155', paddingBottom: '5px' }}>
                📊 {ticker} Statistics & Backtest
            </h4>

            {/* Stats Table */}
            <table style={{ width: '100%', marginBottom: '15px', borderCollapse: 'collapse' }}>
                <tbody>
                    <tr>
                        <td style={subTdStyle}>Price (H/L)</td>
                        <td style={subTdValStyle}>${stats ? stats.maxPrice : '-'} / ${stats ? stats.minPrice : '-'}</td>
                        <td style={subTdStyle}>Score (H/L)</td>
                        <td style={subTdValStyle}>{stats ? stats.maxScore : '-'} / {stats ? stats.minScore : '-'}</td>
                    </tr>
                    <tr>
                        <td style={subTdStyle}>Avg Price</td>
                        <td style={subTdValStyle}>${stats ? stats.avgPrice : '-'}</td>
                        <td style={subTdStyle}>Avg Score</td>
                        <td style={subTdValStyle}>{stats ? stats.avgScore : '-'}</td>
                    </tr>
                    <tr>
                        <td style={subTdStyle}>Buy Count</td>
                        <td style={{ ...subTdValStyle, color: '#ef4444' }}>{stats ? stats.buyCount : '-'}</td>
                        <td style={subTdStyle}>Sell Count</td>
                        <td style={{ ...subTdValStyle, color: '#3b82f6' }}>{stats ? stats.sellCount : '-'}</td>
                    </tr>
                </tbody>
            </table>

            {/* Trades List */}
            <h4 style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '0.8rem' }}>
                📜 Signal Returns ({loading ? '...' : trades.length})
            </h4>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                        <tr style={{ background: '#0f172a', color: '#94a3b8', position: 'sticky', top: 0 }}>
                            <th style={subThStyle}>Entry</th>
                            <th style={subThStyle}>Exit</th>
                            <th style={subThStyle}>Yield</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades.map((trade, idx) => (
                            <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                                <td style={subTdStyle}>
                                    <div style={{ color: '#ef4444' }}>{new Date(trade.entryTime).toLocaleTimeString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                    <div>${trade.entryPrice} ({trade.entryScore})</div>
                                </td>
                                <td style={subTdStyle}>
                                    <div style={{ color: '#3b82f6' }}>{trade.exitTime ? new Date(trade.exitTime).toLocaleTimeString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}</div>
                                    <div>{trade.exitPrice ? `$${trade.exitPrice} (${trade.exitScore})` : '-'}</div>
                                </td>
                                <td style={{ ...subTdStyle, fontWeight: 'bold', color: parseFloat(trade.yield) > 0 ? '#4ade80' : '#f87171' }}>
                                    {trade.yield}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const subThStyle = { padding: '5px', textAlign: 'left', fontWeight: 'normal' };
const subTdStyle = { padding: '4px', color: '#cbd5e1' };
const subTdValStyle = { padding: '4px', textAlign: 'right', fontWeight: 'bold', color: '#fff' };

const LabPage = () => {
    // UI State
    const [period, setPeriod] = useState('5m');
    const [activeTab, setActiveTab] = useState('chart'); // 'list' or 'chart'

    // Config State
    const [buyScore, setBuyScore] = useState(70);
    const [sellScore, setSellScore] = useState(50);
    const [configLoading, setConfigLoading] = useState(false);

    // List View State
    const [ticker, setTicker] = useState('SOXL');
    const [page, setPage] = useState(1);
    const [data, setData] = useState([]);
    const [pagination, setPagination] = useState({});
    const [loading, setLoading] = useState(false);
    const [selectedIds, setSelectedIds] = useState([]);

    // Chart View State
    const [chartData, setChartData] = useState({ SOXL: [], SOXS: [], UPRO: [] });
    const [realtimePrices, setRealtimePrices] = useState({ SOXL: null, SOXS: null, UPRO: null });
    const [chartLoading, setChartLoading] = useState(false);

    // KR Date Helper (User Request: Default Yesterday ~ Today)
    const getKRDate = (offsetDays = 0) => {
        const d = new Date();
        d.setDate(d.getDate() + offsetDays);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    };

    // Filter
    const [dateFrom, setDateFrom] = useState(getKRDate(-1));
    const [dateTo, setDateTo] = useState(getKRDate(0));

    // Initial Load
    useEffect(() => {
        fetchConfig();
        fetchData(); // Load List Initial
    }, []);

    // Effect: Tab Switch or Filter Change
    useEffect(() => {
        if (activeTab === 'list') {
            fetchData();
        } else {
            fetchChartData();
        }
    }, [activeTab, period, page, ticker, dateFrom, dateTo]); // page/ticker only affects list, but simple trigger is fine

    // Effect: Realtime Price Polling (Every 10s)
    useEffect(() => {
        const fetchRealtime = async () => {
            try {
                const tickers = ['SOXL', 'SOXS', 'UPRO'];
                const promises = tickers.map(t => fetch(`/api/v2/status/${t}`).then(res => res.json()));
                const results = await Promise.all(promises);

                const newPrices = {};
                results.forEach((res, idx) => {
                    if (res.status === 'success' && res.market_info) {
                        newPrices[tickers[idx]] = res.market_info;
                    }
                });

                setRealtimePrices(prev => ({ ...prev, ...newPrices }));
            } catch (e) {
                console.error("Realtime Fetch Error", e);
            }
        };

        fetchRealtime(); // Initial fetch
        const interval = setInterval(fetchRealtime, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    // --- API: Config ---
    const fetchConfig = async () => {
        try {
            const res = await fetch('/api/lab/config');
            const json = await res.json();
            if (json) {
                setBuyScore(json.lab_buy_score);
                setSellScore(json.lab_sell_score);
            }
        } catch (e) {
            console.error("Config Fetch Error", e);
        }
    };

    const saveConfig = async () => {
        setConfigLoading(true);
        try {
            const res = await fetch('/api/lab/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lab_buy_score: buyScore, lab_sell_score: sellScore })
            });
            const json = await res.json();
            if (json.status === 'success') {
                Swal.fire('Saved', 'Thresholds saved successfully.', 'success');
            } else {
                Swal.fire('Error', json.detail || 'Failed to save', 'error');
            }
        } catch (e) {
            Swal.fire('Error', 'Network Error', 'error');
        }
        setConfigLoading(false);
    };

    // --- API: Data ---
    const fetchData = async () => {
        if (activeTab !== 'list') return;
        setLoading(true);
        try {
            let url = `/api/lab/data/${period}?page=${page}&limit=10&ticker=${ticker}`;
            if (dateFrom) url += `&date_from=${dateFrom}`;
            if (dateTo) url += `&date_to=${dateTo}`;

            const res = await fetch(url);
            const json = await res.json();
            if (json.status === 'success') {
                setData(json.data);
                setPagination(json.pagination);
                setSelectedIds([]);
            }
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    const fetchChartData = async () => {
        if (activeTab !== 'chart') return;
        setChartLoading(true);
        try {
            // Fetch both SOXL and SOXS for the range
            // Limit 10000 to get full range chart
            const fetchOne = async (t) => {
                let url = `/api/lab/data/${period}?page=1&limit=5000&ticker=${t}`;
                if (dateFrom) url += `&date_from=${dateFrom}`;
                if (dateTo) url += `&date_to=${dateTo}`;
                const res = await fetch(url);
                const json = await res.json();
                return json.status === 'success' ? json.data.reverse() : []; // Reverse for Chart (Old -> New)
            };

            const [soxl, soxs, upro] = await Promise.all([fetchOne('SOXL'), fetchOne('SOXS'), fetchOne('UPRO')]);
            setChartData({ SOXL: soxl, SOXS: soxs, UPRO: upro });

        } catch (e) {
            console.error(e);
        }
        setChartLoading(false);
    }

    // --- Handlers ---
    const handleDelete = async () => {
        if (selectedIds.length === 0) return;
        const result = await Swal.fire({
            title: 'Delete',
            text: `Delete ${selectedIds.length} items?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#ef4444',
            confirmButtonText: 'Delete'
        });

        if (result.isConfirmed) {
            try {
                const ids = selectedIds.join(',');
                const res = await fetch(`/api/lab/data/${period}?ids=${ids}`, { method: 'DELETE' });
                const json = await res.json();
                if (json.status === 'success') {
                    Swal.fire('Deleted', json.message, 'success');
                    fetchData();
                } else {
                    Swal.fire('Error', json.message, 'error');
                }
            } catch (e) {
                Swal.fire('Error', 'Network error', 'error');
            }
        }
    };

    const toggleSelect = (id) => {
        if (selectedIds.includes(id)) setSelectedIds(selectedIds.filter(x => x !== id));
        else setSelectedIds([...selectedIds, id]);
    };

    const toggleSelectAll = () => {
        if (selectedIds.length === data.length) setSelectedIds([]);
        else setSelectedIds(data.map(d => d.id));
    };

    // --- Chart Components ---
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const d = payload[0].payload;
            return (
                <div style={{ background: 'rgba(30, 41, 59, 0.9)', border: '1px solid #475569', padding: '10px', borderRadius: '4px', fontSize: '0.8rem' }}>
                    <p style={{ color: '#94a3b8', marginBottom: '5px' }}>{new Date(d.candle_time).toLocaleString()}</p>
                    <p style={{ color: '#fbbf24', fontWeight: 'bold' }}>Score: {d.total_score}</p>
                    <p style={{ color: '#fff' }}>Price: ${d.close}</p>
                </div>
            );
        }
        return null;
    };

    const renderChart = (tickerName, dataPoints, config = {}) => {
        const {
            dataKey = 'total_score',
            color = tickerName === 'SOXL' ? '#4ade80' : '#f87171',
            yDomain = [0, 100],
            showThresholds = true,
            titleSub = '(Total Score)',
            showPriceOverlay = false
        } = config;

        // Get Latest Info
        const lastData = dataPoints && dataPoints.length > 0 ? dataPoints[dataPoints.length - 1] : null;

        // Prefer Realtime Data for Header
        const realtime = realtimePrices[tickerName];
        const currentPrice = realtime ? realtime.current_price : (lastData ? lastData.close : 0);
        const changePct = realtime ? realtime.change_pct : (lastData ? (lastData.change_pct || 0) : 0);

        const changeColor = changePct > 0 ? '#4ade80' : changePct < 0 ? '#f87171' : '#94a3b8';

        return (
            <div style={{ flex: 1, minWidth: '0', background: '#1e293b', padding: '15px', borderRadius: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
                    <h3 style={{ margin: 0, color: color }}>
                        {tickerName} <span style={{ fontSize: '0.8em', color: '#94a3b8' }}>{titleSub}</span>
                    </h3>
                    {(lastData || realtime) && (
                        <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fbbf24', marginRight: '15px' }}>
                                Score: {realtime && realtime.current_score !== undefined ? realtime.current_score : (lastData ? lastData.total_score : 0)}
                            </span>
                            <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fff', marginRight: '10px' }}>
                                ${currentPrice}
                            </span>
                            <span style={{ color: changeColor, fontWeight: 'bold' }}>
                                {changePct > 0 ? '▲' : changePct < 0 ? '▼' : ''} {changePct}%
                            </span>
                        </div>
                    )}
                </div>

                <div style={{ height: '400px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={dataPoints}>
                            <defs>
                                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis
                                dataKey="candle_time"
                                tickFormatter={(t) => {
                                    const dt = new Date(t);
                                    const hh = dt.getHours().toString().padStart(2, '0');
                                    const mm = dt.getMinutes().toString().padStart(2, '0');
                                    return `${hh}:${mm}`;
                                }}
                                stroke="#94a3b8"
                                fontSize={12}
                            />
                            {/* Primary Axis (Score or Price depending on config) */}
                            <YAxis
                                yAxisId="primary"
                                domain={yDomain}
                                stroke={showPriceOverlay ? color : "#94a3b8"}
                                fontSize={12}
                            />

                            {/* Secondary Axis (Price Overlay) */}
                            {showPriceOverlay && (
                                <YAxis
                                    yAxisId="secondary"
                                    orientation="right"
                                    domain={['auto', 'auto']}
                                    stroke="#64748b"
                                    fontSize={12}
                                    tickFormatter={(val) => `$${val}`}
                                />
                            )}

                            <Tooltip content={<CustomTooltip />} />
                            <Legend />

                            {showThresholds && (
                                <>
                                    <ReferenceLine yAxisId="primary" y={buyScore} label="Buy" stroke="#ef4444" strokeDasharray="3 3" />
                                    <ReferenceLine yAxisId="primary" y={sellScore} label="Sell" stroke="#3b82f6" strokeDasharray="3 3" />
                                </>
                            )}

                            {/* Price Overlay Area */}
                            {showPriceOverlay && (
                                <Area
                                    yAxisId="secondary"
                                    type="monotone"
                                    dataKey="close"
                                    stroke="#94a3b8"
                                    fillOpacity={1}
                                    fill="url(#colorPrice)"
                                    name="Price"
                                />
                            )}

                            {/* Main Line (Score or Price) */}
                            <Line
                                yAxisId="primary"
                                type="monotone"
                                dataKey={dataKey}
                                stroke={color}
                                strokeWidth={2}
                                dot={false}
                                activeDot={{ r: 6 }}
                                connectNulls={true}
                                name={titleSub.replace(/[()]/g, '')}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </div>
        );
    };

    return (
        <div className="lab-container">
            {/* Header Toolbar */}
            <div className="lab-header-toolbar">
                <div className="lab-title-group">
                    <h2 style={{ margin: 0, color: '#38bdf8' }}>🧪 Lab 2.0</h2>

                    {/* Tab Switcher */}
                    <div style={{ display: 'flex', background: '#1e293b', borderRadius: '6px', padding: '4px' }}>
                        <button
                            onClick={() => setActiveTab('list')}
                            style={{ ...tabStyle, background: activeTab === 'list' ? '#334155' : 'transparent' }}
                        >
                            📋 List
                        </button>
                        <button
                            onClick={() => setActiveTab('chart')}
                            style={{ ...tabStyle, background: activeTab === 'chart' ? '#334155' : 'transparent' }}
                        >
                            📈 Chart
                        </button>
                    </div>
                </div>

                {/* Right Actions: Config & Refresh */}
                <div className="lab-actions-group">
                    {/* Config Inputs */}
                    <div className="lab-config-group">
                        <span style={{ color: '#ef4444' }}>Buy Line:</span>
                        <input
                            type="number"
                            value={buyScore}
                            onChange={(e) => setBuyScore(Number(e.target.value))}
                            style={miniInputStyle}
                        />
                        <span style={{ color: '#3b82f6', marginLeft: '5px' }}>Sell Line:</span>
                        <input
                            type="number"
                            value={sellScore}
                            onChange={(e) => setSellScore(Number(e.target.value))}
                            style={miniInputStyle}
                        />
                        <button onClick={saveConfig} disabled={configLoading} style={{ ...btnStyle, fontSize: '0.8rem', padding: '4px 8px', marginLeft: '5px' }}>
                            {configLoading ? 'Saving...' : '💾 Save'}
                        </button>
                    </div>

                </div>
            </div>

            {/* Filter Bar */}
            <div className="lab-filter-bar">
                <div className="lab-filter-inputs">
                    <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="lab-input-date" />
                    <span style={{ color: '#64748b' }}>~</span>
                    <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="lab-input-date" />
                    <button onClick={() => activeTab === 'list' ? fetchData() : fetchChartData()} className="lab-btn">🔍 Search</button>
                </div>

                {/* List Specific Controls */}
                {activeTab === 'list' && (
                    <div className="lab-filter-controls">
                        {/* Ticker Radio */}
                        <div style={{ display: 'flex', gap: '5px', background: '#1e293b', padding: '4px', borderRadius: '6px', border: '1px solid #475569' }}>
                            {['SOXL', 'SOXS'].map(t => (
                                <label key={t} style={{
                                    cursor: 'pointer', padding: '4px 10px', borderRadius: '4px',
                                    background: ticker === t ? '#3b82f6' : 'transparent',
                                    color: ticker === t ? '#fff' : '#94a3b8',
                                    fontWeight: ticker === t ? 'bold' : 'normal',
                                    fontSize: '0.9rem'
                                }}>
                                    <input type="radio" name="ticker" value={t} checked={ticker === t} onChange={() => setTicker(t)} style={{ display: 'none' }} />
                                    {t}
                                </label>
                            ))}
                        </div>

                        {selectedIds.length > 0 && (
                            <button onClick={handleDelete} style={{ ...btnStyle, background: '#ef4444' }}>
                                🗑️ Delete ({selectedIds.length})
                            </button>
                        )}
                        <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                            Pg {pagination.page} / {pagination.total_pages} (T:{pagination.total})
                        </span>
                        <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={pageBtnStyle}>◀</button>
                        <button disabled={page >= pagination.total_pages} onClick={() => setPage(page + 1)} style={pageBtnStyle}>▶</button>
                    </div>
                )}
            </div>

            {/* Content Area */}
            {
                activeTab === 'list' ? (
                    // --- LIST VIEW ---
                    <div style={{ background: '#1e293b', borderRadius: '12px', overflow: 'hidden' }}>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                <thead>
                                    <tr style={{ background: '#0f172a', color: '#94a3b8' }}>
                                        <th style={{ ...thStyle, width: '40px', textAlign: 'center' }}>
                                            <input type="checkbox" onChange={toggleSelectAll} checked={data.length > 0 && selectedIds.length === data.length} />
                                        </th>
                                        <th style={thStyle}>Time (US)</th>
                                        <th style={thStyle}>가격</th>
                                        <th style={thStyle}>등락률</th>
                                        <th style={{ ...thStyle, color: '#fbbf24' }}>Total</th>
                                        <th style={thStyle}>C1</th>
                                        <th style={thStyle}>C2</th>
                                        <th style={thStyle}>C3</th>
                                        <th style={thStyle}>Eng</th>
                                        <th style={thStyle}>RSI</th>
                                        <th style={thStyle}>MACD</th>
                                        <th style={thStyle}>Slope</th>
                                        <th style={thStyle}>ATR</th>
                                        <th style={thStyle}>Ver</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.map((row) => {
                                        const isSelected = selectedIds.includes(row.id);
                                        const rowBg = isSelected ? '#334155' : 'transparent';

                                        return (
                                            <tr key={row.id} style={{ borderBottom: '1px solid #334155', background: rowBg }}>
                                                <td style={{ ...tdStyle, textAlign: 'center' }}>
                                                    <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(row.id)} />
                                                </td>
                                                <td style={tdStyle}>{new Date(row.candle_time).toLocaleString()}</td>
                                                <td style={tdStyle}>{row.close}</td>
                                                <td style={{ ...tdStyle, color: row.change_pct > 0 ? '#4ade80' : row.change_pct < 0 ? '#f87171' : '#fff' }}>
                                                    {row.change_pct}%
                                                </td>
                                                <td style={{ ...tdStyle, color: '#fbbf24', fontWeight: 'bold' }}>{row.total_score}</td>
                                                <td style={tdStyle}>{row.score_cheongan_1}</td>
                                                <td style={tdStyle}>{row.score_cheongan_2}</td>
                                                <td style={tdStyle}>{row.score_cheongan_3}</td>
                                                <td style={tdStyle}>{row.score_energy}</td>
                                                <td style={tdStyle}>{row.score_rsi}</td>
                                                <td style={tdStyle}>{row.score_macd}</td>
                                                <td style={tdStyle}>{row.score_slope}</td>
                                                <td style={tdStyle}>{row.score_atr}</td>
                                                <td style={{ ...tdStyle, fontSize: '0.75rem', color: '#94a3b8' }}>{row.algo_version || '-'}</td>
                                            </tr>
                                        );
                                    })}
                                    {data.length === 0 && (
                                        <tr>
                                            <td colSpan="15" style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
                                                No data found.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ) : (
                    // --- CHART VIEW ---
                    <div className="lab-chart-view">
                        {chartLoading ? (
                            <div style={{ width: '100%', textAlign: 'center', padding: '50px', color: '#94a3b8' }}>Loading Charts...</div>
                        ) : (
                            <>
                                <div className="lab-chart-row">
                                    {renderChart('SOXL', chartData.SOXL, { showPriceOverlay: true })}
                                    {renderChart('SOXS', chartData.SOXS, { showPriceOverlay: true })}
                                </div>

                                {/* Analysis Panels */}
                                <div className="lab-chart-row">
                                    <AnalysisPanel ticker="SOXL" data={chartData.SOXL} buyScore={buyScore} sellScore={sellScore} period={period} />
                                    <AnalysisPanel ticker="SOXS" data={chartData.SOXS} buyScore={buyScore} sellScore={sellScore} period={period} />
                                </div>

                                {/* UPRO Chart (Full Width) */}
                                <div className="lab-chart-row">
                                    {renderChart('UPRO', chartData.UPRO || [], {
                                        dataKey: 'close',
                                        color: '#3b82f6',
                                        yDomain: ['auto', 'auto'],
                                        showThresholds: false,
                                        titleSub: '(Price)'
                                    })}
                                </div>
                            </>
                        )}
                    </div>
                )
            }
        </div>
    );
};

// Styles
const tabStyle = { padding: '6px 15px', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem', borderRadius: '4px' };
const btnStyle = { background: '#334155', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' };
const pageBtnStyle = { background: '#1e293b', border: '1px solid #475569', color: '#fff', width: '30px', height: '30px', borderRadius: '4px', cursor: 'pointer' };
const inputStyle = { background: '#1e293b', border: '1px solid #475569', color: '#fff', padding: '5px', borderRadius: '4px' };
const miniInputStyle = { width: '50px', background: '#0f172a', border: '1px solid #475569', color: '#fff', padding: '2px 5px', borderRadius: '3px', marginLeft: '5px' };
const thStyle = { padding: '10px', textAlign: 'left', whiteSpace: 'nowrap' };
const tdStyle = { padding: '8px 10px', borderBottom: '1px solid #334155' };

export default LabPage;
