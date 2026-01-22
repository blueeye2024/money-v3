import React, { useState, useEffect, useMemo } from 'react';
import { ComposedChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from 'recharts';

const PriceAlertChart = ({ ticker, currentPrice, changePct = 0, relationIndex = null }) => {
    const [chartData5m, setChartData5m] = useState([]);
    const [alertLevels, setAlertLevels] = useState([]);

    // Derived
    const cleanTicker = ticker;
    const themeColor = ticker === 'SOXS' ? '#a855f7' : '#06b6d4'; // Default to Blue for others

    // Fetch Data
    useEffect(() => {
        const fetchChart = async () => {
            try {
                const res = await fetch(`/api/v2/chart/${cleanTicker}?limit=40`);
                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    setChartData5m(json.data.candles_5m || []);
                }
            } catch (e) { console.error(e); }
        };

        const fetchAlerts = async () => {
            try {
                const res = await fetch(`/api/v2/alerts/${cleanTicker}`);
                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    setAlertLevels(json.data.filter(a => a.is_active === 'Y' && a.price > 0));
                }
            } catch (e) { console.error(e); }
        };

        fetchChart();
        fetchAlerts();
        const chInt = setInterval(fetchChart, 60000);
        const alInt = setInterval(fetchAlerts, 10000);
        return () => { clearInterval(chInt); clearInterval(alInt); };
    }, [cleanTicker]);

    // Prepare Data (Recent 1h = Last 12 of 5m candles)
    const recentData = useMemo(() => {
        let currentTime;
        try {
            const now = new Date();
            currentTime = new Intl.DateTimeFormat('en-US', {
                timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false
            }).format(now);
        } catch (e) {
            const now = new Date();
            currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
        }

        let data = [];
        if (chartData5m.length > 0) {
            // [Fix] Zero Price Handling (Apply to FULL dataset before slicing)
            let validData = [...chartData5m];

            // 1. Forward Fill
            for (let i = 1; i < validData.length; i++) {
                if (validData[i].price === 0 && validData[i - 1].price > 0) {
                    validData[i] = { ...validData[i], price: validData[i - 1].price };
                }
            }
            // 2. Backward Fill
            for (let i = validData.length - 2; i >= 0; i--) {
                if (validData[i].price === 0 && validData[i + 1].price > 0) {
                    validData[i] = { ...validData[i], price: validData[i + 1].price };
                }
            }

            data = validData.slice(-12); // Last 12 candles = 60 mins
            const lastTime = data[data.length - 1].time;

            // Gap Check
            const getMinutesDiff = (t1, t2) => {
                try {
                    const [h1, m1] = t1.split(':').map(Number);
                    const [h2, m2] = t2.split(':').map(Number);
                    let diff = (h2 * 60 + m2) - (h1 * 60 + m1);
                    if (diff < -720) diff += 1440;
                    return diff;
                } catch { return 999; }
            };

            const diff = getMinutesDiff(lastTime, currentTime);
            if (diff <= 60 && diff >= 0 && currentPrice > 0) {
                data = [...data, { time: currentTime, price: currentPrice }];
            }
        } else if (currentPrice > 0) {
            // Fallback for empty history
            data = [{ time: currentTime, price: currentPrice }];
        }
        return data;
    }, [chartData5m, currentPrice]);

    if (recentData.length === 0) return null;

    // YAxis Domain
    const prices = recentData.map(d => d.price).filter(p => p > 0); // Filter out any remaining 0s
    if (prices.length === 0) return null; // Safety check

    const alertPrices = alertLevels.map(a => parseFloat(a.price));

    // Simplified Domain
    const allValues = [...prices, ...alertPrices];
    const minVal = Math.min(...allValues);
    const maxVal = Math.max(...allValues);
    const range = maxVal - minVal;
    const minY = minVal - (range * 0.1);
    const maxY = maxVal + (range * 0.1);

    return (
        <div style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '12px', padding: '12px', border: `1px solid ${themeColor}22` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h4 style={{ margin: 0, fontSize: '0.85rem', color: themeColor, fontWeight: '700' }}>
                    📢 {ticker} Price Alerts (Recent 1h)
                </h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fff' }}>
                        ${currentPrice > 0 ? currentPrice.toFixed(2) : '-.--'}
                    </span>
                    <span style={{
                        fontSize: '0.8rem',
                        fontWeight: '500',
                        color: changePct > 0 ? '#f87171' : changePct < 0 ? '#60a5fa' : '#94a3b8',
                        background: 'rgba(255,255,255,0.05)',
                        padding: '2px 6px',
                        borderRadius: '4px'
                    }}>
                        {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
                    </span>
                    {relationIndex !== null && relationIndex !== undefined && (
                        <span style={{
                            fontSize: '0.7rem',
                            color: '#fbbf24',
                            marginLeft: '4px',
                            background: 'rgba(251, 191, 36, 0.1)',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontWeight: 'bold'
                        }}>
                            연관지수: {relationIndex.toFixed(0)}%
                        </span>
                    )}
                </div>
            </div>

            <ResponsiveContainer width="100%" height={180}>
                <ComposedChart data={recentData} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                    <defs>
                        <linearGradient id={`gradAlert-${cleanTicker}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={themeColor} stopOpacity={0.4} />
                            <stop offset="95%" stopColor={themeColor} stopOpacity={0.05} />
                        </linearGradient>
                    </defs>
                    <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                    <YAxis
                        domain={[minY, maxY]}
                        tick={{ fill: '#94a3b8', fontSize: 9 }}
                        axisLine={{ stroke: '#334155' }}
                        tickLine={false}
                        tickFormatter={(val) => `$${val.toFixed(2)}`}
                        width={45}
                    />
                    <Tooltip
                        contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid #334155', borderRadius: '6px', fontSize: '0.75rem' }}
                        labelStyle={{ color: '#94a3b8' }}
                        formatter={(val) => [`$${val?.toFixed(2)}`, 'Price']}
                    />
                    <Area type="monotone" dataKey="price" stroke={themeColor} strokeWidth={2.5} fill={`url(#gradAlert-${cleanTicker})`} />

                    {/* Alerts */}
                    {alertLevels.map((alert, i) => (
                        <ReferenceLine
                            key={`alert-${i}`}
                            y={alert.price}
                            stroke={alert.level_type === 'BUY' ? 'rgba(248, 113, 113, 0.5)' : 'rgba(192, 132, 252, 0.5)'}
                            strokeDasharray="4 2"
                        />
                    ))}

                    {/* Current Price Dot */}
                    {currentPrice > 0 && (
                        <ReferenceDot
                            x={recentData[recentData.length - 1]?.time}
                            y={currentPrice}
                            r={4}
                            fill={themeColor}
                            stroke="#fff"
                            strokeWidth={2}
                        />
                    )}
                </ComposedChart>
            </ResponsiveContainer>
        </div >
    );
};

export default PriceAlertChart;
