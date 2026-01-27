import React, { useEffect, useState } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

function CryptoPage() {
    const [status, setStatus] = useState([]);
    const [selectedCoin, setSelectedCoin] = useState('XRP'); // Default XRP
    const [chartPeriod, setChartPeriod] = useState('30m'); // Default 30m
    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(true);

    // [New] Holdings & Limits from DB
    const [holdings, setHoldings] = useState({});
    const [priceLimits, setPriceLimits] = useState({});

    // Fetch Settings
    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/crypto/settings');
            const json = await res.json();
            if (json.status === 'success') {
                const data = json.data || {};
                setHoldings(data.holdings || {});
                setPriceLimits(data.limits || {});
            }
        } catch (e) {
            console.error("Settings Fetch Error:", e);
        }
    };

    const saveSettings = async (newHoldings, newLimits) => {
        try {
            await fetch('/api/crypto/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    holdings: newHoldings,
                    limits: newLimits
                })
            });
        } catch (e) {
            console.error("Settings Save Error:", e);
        }
    };

    const handleHoldingChange = (symbol, value) => {
        const val = parseFloat(value) || 0;
        const newHoldings = { ...holdings, [symbol]: val };
        setHoldings(newHoldings);
        // Auto-save on change (or use onBlur for validation if preferred)
        // For numbers, immediate save is okay-ish if not too frequent, but onBlur is safer for UX (prevents jumpiness).
        // Let's keep local state update here, but save in a separate 'save' call or useEffect debounce.
        // For simplicity: Save immediately here (Volume is low).
        saveSettings(newHoldings, priceLimits);
    };

    const handleLimitChange = (symbol, type, value) => {
        const current = priceLimits[symbol] || { upper: '', lower: '' };
        const newLimits = {
            ...priceLimits,
            [symbol]: { ...current, [type]: value }
        };
        setPriceLimits(newLimits);
        saveSettings(holdings, newLimits);
    };

    // Fetch Status
    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/crypto/status');
            const json = await res.json();
            setStatus(json.data || []);
        } catch (e) {
            console.error("Status Fetch Error:", e);
        }
    };

    // Fetch Chart
    const fetchChart = async () => {
        if (!selectedCoin) return;
        setLoading(true);
        try {
            const res = await fetch(`/api/crypto/history/${selectedCoin}?period=${chartPeriod}`);
            const json = await res.json();
            setChartData(json.data || []);
        } catch (e) {
            console.error("Chart Fetch Error:", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSettings(); // [Ver 7.6] Load from DB
        fetchStatus();
        const interval = setInterval(fetchStatus, 300000); // 5 min
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        fetchChart();
    }, [selectedCoin, chartPeriod]);

    const getCoinName = (symbol) => symbol === 'BTC' ? '비트코인 (BTC)' : '리플 (XRP)';
    const getCoinColor = (change) => change >= 0 ? '#ef4444' : '#3b82f6';

    // [New] Total Value Calc
    const getCoinPrice = (symbol) => {
        const coin = status.find(c => c.symbol === symbol);
        return coin ? coin.price : 0;
    };

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{ background: 'rgba(15, 23, 42, 0.9)', padding: '10px', border: '1px solid #334155', borderRadius: '4px', fontSize: '0.8rem' }}>
                    <p style={{ color: '#94a3b8', marginBottom: '5px' }}>{label}</p>
                    <p style={{ color: '#fff', fontWeight: 'bold' }}>
                        Price: ${payload[0].value.toLocaleString()}
                    </p>
                </div>
            );
        }
        return null;
    };

    // Get current limits for selected coin
    const currentLimit = priceLimits[selectedCoin] || { upper: '', lower: '' };

    return (
        <div className="crypto-container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', color: '#e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderLeft: '4px solid #f59e0b', paddingLeft: '10px' }}>
                <h1 className="crypto-title">
                    가상자산 시세 조회
                </h1>
                <span className="crypto-update-info">
                    갱신 주기: 5분 (Source: Yahoo Finance)
                </span>
            </div>

            {/* Status Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '30px' }}>
                {status.map((coin) => {
                    const qty = holdings[coin.symbol] || 0;
                    const totalVal = qty * coin.price;

                    return (
                        <div
                            key={coin.symbol}
                            onClick={() => setSelectedCoin(coin.symbol)}
                            style={{
                                background: selectedCoin === coin.symbol ? 'rgba(59, 130, 246, 0.2)' : 'rgba(30, 41, 59, 0.6)',
                                border: selectedCoin === coin.symbol ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '12px',
                                padding: '20px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                backdropFilter: 'blur(10px)',
                                position: 'relative',
                                overflow: 'hidden'
                            }}
                        >
                            {/* Time Badge */}
                            <div style={{
                                position: 'absolute', top: '10px', right: '10px',
                                fontSize: '0.7rem', color: '#64748b',
                                background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px'
                            }}>
                                {coin.time || 'Loading...'}
                            </div>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                                <div>
                                    <h3 style={{ fontSize: '1.4rem', fontWeight: 'bold', color: '#fff' }}>{coin.symbol}</h3>
                                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{coin.name}</span>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: getCoinColor(coin.change), display: 'block' }}>
                                        ${coin.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </span>
                                    <span style={{
                                        fontSize: '0.9rem',
                                        color: getCoinColor(coin.change),
                                        background: coin.change >= 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                                        padding: '2px 8px',
                                        borderRadius: '4px'
                                    }}>
                                        {coin.change > 0 ? '+' : ''}{coin.change.toFixed(2)}%
                                    </span>
                                </div>
                            </div>

                            {/* Holdings Input Section */}
                            <div style={{ marginTop: '15px', paddingTop: '15px', borderTop: '1px solid rgba(255,255,255,0.1)' }} onClick={e => e.stopPropagation()}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                                    <label style={{ fontSize: '0.8rem', color: '#94a3b8' }}>보유 수량:</label>
                                    <input
                                        type="number"
                                        value={qty || ''}
                                        onChange={(e) => handleHoldingChange(coin.symbol, e.target.value)}
                                        placeholder="0"
                                        style={{
                                            background: 'rgba(0,0,0,0.3)', border: '1px solid #475569', borderRadius: '4px',
                                            color: '#fff', padding: '4px 8px', width: '80px', fontSize: '0.9rem'
                                        }}
                                    />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>평가 금액</span>
                                    <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#cbd5e1' }}>
                                        ${totalVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Chart Section */}
            <div style={{ background: 'rgba(30, 41, 59, 0.6)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                {/* Header & Controls */}
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '15px' }}>
                    <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px', minWidth: '200px' }}>
                        {getCoinName(selectedCoin)} <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 'normal' }}>| {chartPeriod === '30m' ? '30분봉' : '일봉'} 차트</span>
                    </h2>

                    {/* Limit Inputs */}
                    <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>상한선:</span>
                            <input
                                type="number"
                                placeholder="Alert High"
                                value={currentLimit.upper}
                                onChange={(e) => handleLimitChange(selectedCoin, 'upper', e.target.value)}
                                style={{
                                    background: 'rgba(0,0,0,0.3)', border: '1px solid #475569', borderRadius: '4px',
                                    color: '#fff', padding: '4px 8px', width: '90px'
                                }}
                            />
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: '#3b82f6', fontSize: '0.9rem' }}>하한선:</span>
                            <input
                                type="number"
                                placeholder="Alert Low"
                                value={currentLimit.lower}
                                onChange={(e) => handleLimitChange(selectedCoin, 'lower', e.target.value)}
                                style={{
                                    background: 'rgba(0,0,0,0.3)', border: '1px solid #475569', borderRadius: '4px',
                                    color: '#fff', padding: '4px 8px', width: '90px'
                                }}
                            />
                        </div>
                    </div>

                    {/* Chart Toggles */}
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                            onClick={() => setChartPeriod('30m')}
                            style={{
                                padding: '6px 16px',
                                background: chartPeriod === '30m' ? '#3b82f6' : 'transparent',
                                border: '1px solid #3b82f6',
                                borderRadius: '6px',
                                color: '#fff',
                                cursor: 'pointer',
                                fontWeight: chartPeriod === '30m' ? 'bold' : 'normal'
                            }}
                        >
                            30분봉 (30m)
                        </button>
                        <button
                            onClick={() => setChartPeriod('daily')}
                            style={{
                                padding: '6px 16px',
                                background: chartPeriod === 'daily' ? '#3b82f6' : 'transparent',
                                border: '1px solid #3b82f6',
                                borderRadius: '6px',
                                color: '#fff',
                                cursor: 'pointer',
                                fontWeight: chartPeriod === 'daily' ? 'bold' : 'normal'
                            }}
                        >
                            일봉 (Daily)
                        </button>
                    </div>
                </div>

                <div style={{ height: '500px', width: '100%' }}>
                    {loading ? (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                            <div className="spinner" style={{ border: '4px solid rgba(255,255,255,0.1)', width: '36px', height: '36px', borderRadius: '50%', borderLeftColor: '#3b82f6', animation: 'spin 1s linear infinite' }}></div>
                        </div>
                    ) : (chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                <XAxis
                                    dataKey="time"
                                    stroke="#94a3b8"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    tickMargin={10}
                                    tickFormatter={(str) => {
                                        // 30m formatting: 'dd일 HH:mm'
                                        // Incoming str might be 'DD일 HH:mm' already from backend or Date string?
                                        // Backend sends: daily='MM/DD', 30m='DD일 HH:mm'
                                        // So we just display as is, or refine it. 
                                        return str;
                                    }}
                                />
                                <YAxis
                                    domain={['auto', 'auto']}
                                    stroke="#94a3b8"
                                    tick={{ fill: '#94a3b8', fontSize: 12 }}
                                    tickFormatter={(val) => `$${val.toLocaleString()}`}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Line
                                    type="monotone"
                                    dataKey="close"
                                    stroke={selectedCoin === 'BTC' ? '#f59e0b' : '#3b82f6'}
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 6, fill: '#fff' }}
                                />

                                {/* Reference Lines for Limits */}
                                {currentLimit.upper && (
                                    <ReferenceLine
                                        y={parseFloat(currentLimit.upper)}
                                        label={{ value: 'Upper', fill: '#ef4444', fontSize: 12, position: 'right' }}
                                        stroke="#ef4444"
                                        strokeDasharray="5 5"
                                    />
                                )}
                                {currentLimit.lower && (
                                    <ReferenceLine
                                        y={parseFloat(currentLimit.lower)}
                                        label={{ value: 'Lower', fill: '#3b82f6', fontSize: 12, position: 'right' }}
                                        stroke="#3b82f6"
                                        strokeDasharray="5 5"
                                    />
                                )}
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                            No Data Available
                        </div>
                    ))}
                </div>
                <div style={{ marginTop: '10px', textAlign: 'right', fontSize: '0.8rem', color: '#64748b' }}>
                    * 실시간 데이터 조회 주기: 5분
                </div>
            </div>

            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .crypto-title {
                    font-size: 1.5rem;
                    font-weight: bold;
                }
                .crypto-update-info {
                    font-size: 0.8rem; 
                    color: #64748b;
                    display: block;
                }
                @media (max-width: 768px) {
                    .crypto-title {
                        font-size: 1.2rem;
                    }
                    .crypto-update-info {
                        display: none;
                    }
                    .crypto-container {
                        padding: 10px !important;
                    }
                }
            `}</style>
        </div>
    );
}

export default CryptoPage;
