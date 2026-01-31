
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

    const fetchBacktest = async () => {
        setLoading(true);
        // User Req: Clear previous data first
        setTrades([]);
        try {
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

    // Auto-fetch only on mount or ticker/period change. 
    // Do NOT auto-fetch on buyScore/sellScore change anymore (User Req).
    useEffect(() => {
        fetchBacktest();
        // eslint-disable-next-line
    }, [ticker, period]);

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

            {/* Trades List Header with Reset Button */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4 style={{ margin: 0, color: '#94a3b8', fontSize: '0.8rem' }}>
                    📜 Signal Returns ({loading ? '...' : trades.length})
                </h4>
                <button
                    onClick={fetchBacktest}
                    disabled={loading}
                    style={{ background: '#334155', border: '1px solid #475569', color: '#fff', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', padding: '2px 8px' }}
                >
                    {loading ? 'Running...' : '🔄 Reset'}
                </button>
            </div>

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
                        {trades.map((trade, idx) => {
                            const isOpen = trade.isOpen === true;
                            const rowStyle = {
                                borderBottom: '1px solid #334155',
                                background: isOpen ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                                borderLeft: isOpen ? '3px solid #3b82f6' : 'none'
                            };

                            return (
                                <tr key={idx} style={rowStyle}>
                                    <td style={subTdStyle}>
                                        <div style={{ color: '#ef4444' }}>{new Date(trade.entryTime).toLocaleTimeString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                                        <div>${trade.entryPrice} ({trade.entryScore})</div>
                                    </td>
                                    <td style={subTdStyle}>
                                        {isOpen ? (
                                            <div style={{ color: '#fbbf24', fontWeight: 'bold' }}>HOLDING...</div>
                                        ) : (
                                            <>
                                                <div style={{ color: '#3b82f6' }}>{trade.exitTime ? new Date(trade.exitTime).toLocaleTimeString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}</div>
                                                <div>{trade.exitPrice ? `$${trade.exitPrice} (${trade.exitScore})` : '-'}</div>
                                            </>
                                        )}
                                    </td>
                                    <td style={{ ...subTdStyle, fontWeight: 'bold', color: parseFloat(trade.yield) > 0 ? '#4ade80' : '#f87171' }}>
                                        {trade.yield}%
                                    </td>
                                </tr>
                            );
                        })}
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

    // KR Date Helper with Time (User Req: DateTime Picker)
    const getKRDateTime = (offsetDays = 0, isStart = false) => {
        const d = new Date(); // KST
        d.setDate(d.getDate() + offsetDays);
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hh = isStart ? '00' : String(d.getHours()).padStart(2, '0');
        const mm = isStart ? '00' : String(d.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${day}T${hh}:${mm}`;
    };

    // [New] Real-time Auto Mode for Chart (User Req: No freezing, 1h window)
    const [isAutoMode, setIsAutoMode] = useState(true);

    // [v9.5.5] Clock Trigger (Update every second to keep minute sync)
    const [clockTrigger, setClockTrigger] = useState(0);
    useEffect(() => {
        const timer = setInterval(() => setClockTrigger(prev => prev + 1), 1000);
        return () => clearInterval(timer);
    }, []);

    // Filter
    // Filter
    const [dateFrom, setDateFrom] = useState(getKRDateTime(-1, true)); // Yesterday 00:00
    const [dateTo, setDateTo] = useState(getKRDateTime(0, false));   // Today Current

    // Auto-disable AutoMode when user manually changes filters
    const handleDateChange = (type, val) => {
        setIsAutoMode(false);
        if (type === 'from') setDateFrom(val);
        else setDateTo(val);
    };

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

    // Effect: Chart Auto-Polling (10s) - Faster refresh with no animation for smooth flow
    useEffect(() => {
        if (!isAutoMode || activeTab !== 'chart') return;
        const interval = setInterval(() => {
            fetchChartData(false);
        }, 10000); // 10s polling
        return () => clearInterval(interval);
    }, [isAutoMode, activeTab, period]);

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

    const fetchChartData = async (isManualSearch = false) => {
        if (activeTab !== 'chart') return;

        // ONLY show loading for manual search or true first load when not in auto mode
        const isFirstLoad = !chartData.SOXL.length && !chartData.SOXS.length;
        if (isManualSearch || (isFirstLoad && !isAutoMode)) {
            setChartLoading(true);
        }
        try {
            const fetchOne = async (t) => {
                let url = `/api/lab/data/${period}?page=1&limit=5000&ticker=${t}`;

                // Version: Ver 9.4.3
                // We rely on 'limit' instead of 'date_from' to avoid client-server time sync issues.
                if (isAutoMode && !isManualSearch) {
                    url = `/api/lab/data/${period}?page=1&limit=50&ticker=${t}`;
                } else {
                    if (dateFrom) url += `&date_from=${dateFrom.replace('T', ' ')}`;
                    if (dateTo) url += `&date_to=${dateTo.replace('T', ' ')}`;
                }

                const res = await fetch(url);
                const json = await res.json();

                if (json.status !== 'success') return [];

                // [Ver 9.4.9] Fix 0 price data (fill with prev value)
                let data = json.data.reverse();
                for (let i = 0; i < data.length; i++) {
                    if (Number(data[i].close) === 0) {
                        // Find previous valid close
                        let prevClose = 0;
                        for (let j = i - 1; j >= 0; j--) {
                            if (Number(data[j].close) > 0) {
                                prevClose = data[j].close;
                                break;
                            }
                        }
                        // If no previous valid (e.g. first processing), try next? 
                        // Or just keep 0 if absolutely no data. 
                        // Usually previous data exists.
                        if (prevClose > 0) {
                            data[i].close = prevClose;
                        }
                    }
                }
                return data;
            };

            const [soxl, soxs, uproRaw] = await Promise.all([fetchOne('SOXL'), fetchOne('SOXS'), fetchOne('UPRO')]);

            // --- UPRO Post-Processing ---
            // 1. Filter outliers (±10% from previous point)
            // 2. Limit to latest 3 hours (But if auto mode 1h, it will be 1h subset)
            let upro = uproRaw;
            if (upro.length > 0) {
                const filtered = [];
                upro.forEach((d, i) => {
                    if (i === 0) { filtered.push(d); return; }
                    const prev = filtered[filtered.length - 1].close;
                    const diff = Math.abs(d.close - prev) / prev;
                    if (diff <= 0.1) { // 10% limit
                        filtered.push(d);
                    }
                });

                // Limit to 3 hours logic removed (limit=50 is enough)
                upro = filtered;
            }

            setChartData({ SOXL: soxl, SOXS: soxs, UPRO: upro });

        } catch (e) {
            console.error(e);
        } finally {
            // Only toggle loading off if it was actually turned on
            if (isManualSearch || !chartData.SOXL.length) {
                setChartLoading(false);
            }
        }
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

                <div style={{ height: '200px' }}>
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
                                    isAnimationActive={false}
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
                                isAnimationActive={false}
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

                    {/* [v9.5.5] Real-time Clock UI */}
                    <div style={{ marginLeft: '20px', display: 'flex', flexDirection: 'column', fontSize: '0.75rem', color: '#94a3b8', gap: '2px', paddingLeft: '15px', borderLeft: '1px solid #334155' }}>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.8rem' }}>🇰🇷</span>
                            <span style={{ fontWeight: 'bold', color: '#e2e8f0', fontFamily: 'monospace', paddingTop: '1px' }}>
                                {(() => {
                                    const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
                                    const y = d.getFullYear();
                                    const m = String(d.getMonth() + 1).padStart(2, '0');
                                    const day = String(d.getDate()).padStart(2, '0');
                                    const h = String(d.getHours()).padStart(2, '0');
                                    const min = String(d.getMinutes()).padStart(2, '0');
                                    return `${y}.${m}.${day} ${h}:${min}`;
                                })()}
                            </span>
                        </div>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span style={{ fontSize: '0.8rem' }}>🇺🇸</span>
                            <span style={{ fontWeight: 'bold', color: '#94a3b8', fontFamily: 'monospace', paddingTop: '1px' }}>
                                {(() => {
                                    const d = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
                                    const y = d.getFullYear();
                                    const m = String(d.getMonth() + 1).padStart(2, '0');
                                    const day = String(d.getDate()).padStart(2, '0');
                                    const h = String(d.getHours()).padStart(2, '0');
                                    const min = String(d.getMinutes()).padStart(2, '0');
                                    return `${y}.${m}.${day} ${h}:${min}`;
                                })()}
                            </span>
                        </div>
                    </div>

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
                    <input type="datetime-local" value={dateFrom} onChange={e => handleDateChange('from', e.target.value)} className="lab-input-date" />
                    <span style={{ color: '#64748b' }}>~</span>
                    <input type="datetime-local" value={dateTo} onChange={e => handleDateChange('to', e.target.value)} className="lab-input-date" />
                    <button onClick={() => { setIsAutoMode(false); activeTab === 'list' ? fetchData() : fetchChartData(true); }} className="lab-btn">🔍 Search</button>
                    {activeTab === 'chart' && !isAutoMode && (
                        <button onClick={() => setIsAutoMode(true)} style={{ ...btnStyle, background: '#10b981', marginLeft: '5px' }}>⚡ Auto Live</button>
                    )}
                    {activeTab === 'chart' && isAutoMode && (
                        <span style={{ marginLeft: '10px', color: '#10b981', fontSize: '0.8rem', fontWeight: 'bold' }}>● LIVE (1h)</span>
                    )}
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

                                {/* UPRO Chart (Moved above panels) */}
                                <div className="lab-chart-row">
                                    {renderChart('UPRO', chartData.UPRO || [], {
                                        dataKey: 'total_score',
                                        color: '#3b82f6',
                                        yDomain: [0, 100],
                                        showThresholds: true,
                                        showPriceOverlay: true,
                                        titleSub: '(Score & Price)'
                                    })}
                                </div>

                                {/* Analysis Panels */}
                                <div className="lab-chart-row">
                                    <AnalysisPanel ticker="SOXL" data={chartData.SOXL} buyScore={buyScore} sellScore={sellScore} period={period} />
                                    <AnalysisPanel ticker="SOXS" data={chartData.SOXS} buyScore={buyScore} sellScore={sellScore} period={period} />
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
