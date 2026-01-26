import React, { useState, useEffect } from 'react';
import V2SignalStatus from './V2SignalStatus';
import PriceLevelAlerts from './PriceLevelAlerts';
import PriceAlertChart from './PriceAlertChart';
import TodayEventsWidget from './TodayEventsWidget';



const SystemPerformanceReport = ({ trades = [] }) => {
    // Calculate Stats on the fly
    const stats = React.useMemo(() => {
        if (!trades || trades.length === 0) return null;

        const closedTrades = trades.filter(t => t.status === 'CLOSED');
        const wins = closedTrades.filter(t => t.profit_pct > 0).length;
        const totalClosed = closedTrades.length;
        const win_rate = totalClosed > 0 ? (wins / totalClosed) * 100 : 0;

        const total_return = closedTrades.reduce((acc, t) => acc + Number(t.profit_pct), 0);
        const avg_return = totalClosed > 0 ? total_return / totalClosed : 0;

        return {
            win_rate,
            wins,
            total_trades: totalClosed,
            avg_return,
            total_return
        };
    }, [trades]);

    if (!trades || trades.length === 0) return null;



    return (
        <div>
            {/* Top Stats */}
            <div className="responsive-grid-3" style={{ marginBottom: '15px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#888' }}>Win Rate</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fff' }}>{stats?.win_rate?.toFixed(1) || 0}%</div>
                    <div style={{ fontSize: '0.65rem', color: '#555' }}>({stats?.wins}/{stats?.total_trades} trades)</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#888' }}>Avg Return</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: (stats?.avg_return > 0 ? '#4ade80' : stats?.avg_return < 0 ? '#f87171' : '#ccc') }}>
                        {stats?.avg_return > 0 ? '+' : ''}{stats?.avg_return?.toFixed(2) || 0}%
                    </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: '#888' }}>Total Profit</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: (stats?.total_return > 0 ? '#4ade80' : stats?.total_return < 0 ? '#f87171' : '#ccc') }}>
                        {stats?.total_return > 0 ? '+' : ''}{stats?.total_return?.toFixed(2) || 0}%
                    </div>
                </div>
            </div>

            {/* Trade List Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', color: '#ccc' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', color: '#888' }}>
                            <th style={{ padding: '6px', textAlign: 'left' }}>Time (KR)</th>
                            <th style={{ padding: '6px', textAlign: 'center' }}>Ticker</th>
                            <th style={{ padding: '6px', textAlign: 'center' }}>Type</th>
                            <th style={{ padding: '6px', textAlign: 'right' }}>Price</th>
                            <th style={{ padding: '6px', textAlign: 'right' }}>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades.slice(0, 5).map((t, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <td style={{ padding: '6px' }}>{new Date(t.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</td>
                                <td style={{ padding: '6px', textAlign: 'center', fontWeight: 'bold' }}>{t.ticker}</td>
                                <td style={{ padding: '6px', textAlign: 'center' }}>
                                    <span style={{
                                        padding: '2px 6px', borderRadius: '4px',
                                        background: t.trade_type === 'BUY' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                                        color: t.trade_type === 'BUY' ? '#f87171' : '#60a5fa',
                                        fontWeight: 'bold', fontSize: '0.65rem'
                                    }}>
                                        {t.trade_type}
                                    </span>
                                </td>
                                <td style={{ padding: '6px', textAlign: 'right' }}>
                                    ${Number(t.price).toFixed(2)}
                                    {t.profit_pct != null && (
                                        <span style={{ marginLeft: '4px', color: t.profit_pct > 0 ? '#4ade80' : '#f87171', fontWeight: 'bold' }}>
                                            ({t.profit_pct > 0 ? '+' : ''}{Number(t.profit_pct).toFixed(2)}%)
                                        </span>
                                    )}
                                </td>
                                <td style={{ padding: '6px', textAlign: 'right', color: '#666' }}>{new Date(t.trade_time).toLocaleDateString()}</td>
                            </tr>
                        ))}
                        {trades.length === 0 && (
                            <tr><td colSpan="5" style={{ padding: '10px', textAlign: 'center', color: '#555' }}>아직 거래 기록이 없습니다.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};




const MarketInsight = ({ market, stocks, signalHistory, onRefresh, pollingMode, setPollingMode, marketStatus, lastUpdateTime, isMuted, toggleMute }) => {
    // [New] Local state for persistent DB signals
    const [dbSignals, setDbSignals] = useState({ SOXL: [], SOXS: [] });

    // Fetch DB signals on mount and polling
    useEffect(() => {
        const fetchDbSignals = async () => {
            try {
                const [soxlRes, soxsRes] = await Promise.all([
                    fetch('/api/signals?ticker=SOXL&limit=10'),
                    fetch('/api/signals?ticker=SOXS&limit=10')
                ]);

                const soxlData = soxlRes.ok ? await soxlRes.json() : [];
                const soxsData = soxsRes.ok ? await soxsRes.json() : [];

                setDbSignals({ SOXL: soxlData, SOXS: soxsData });
            } catch (e) {
                console.error("Failed to fetch DB signals:", e);
            }
        };

        fetchDbSignals();
        // Poll every 10 seconds to keep fresh (User Request)
        const interval = setInterval(fetchDbSignals, 10000);
        return () => clearInterval(interval);
    }, []);
    if (!market) return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>데이터 로딩 중...</div>;

    const { market_regime } = market;
    const regimeDetails = market_regime?.details;

    const [v2Status, setV2Status] = React.useState({ SOXL: null, SOXS: null });
    const [todayStrategy, setTodayStrategy] = React.useState('');
    const [showJournal, setShowJournal] = React.useState(false);
    const [todayEvents, setTodayEvents] = React.useState([]);

    // 오늘의 장전 전략 가져오기
    React.useEffect(() => {
        const fetchTodayStrategy = async () => {
            try {
                const today = new Date().toISOString().slice(0, 10);
                const res = await fetch(`/api/daily-reports/${today}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.pre_market_strategy) {
                        setTodayStrategy(data.pre_market_strategy);
                    }
                }
            } catch (e) {
                console.error('Strategy fetch error:', e);
            }
        };
        fetchTodayStrategy();

        // Fetch today events
        const fetchTodayEvents = async () => {
            try {
                const res = await fetch('/api/market-events/today');
                if (res.ok) setTodayEvents(await res.json());
            } catch (e) { console.error('Events fetch error:', e); }
        };
        fetchTodayEvents();
    }, []);



    // [Ver 7.2.6] Enhanced Refresh Handler (Combines Parent + Local Refresh)
    const handleRefresh = () => {
        if (onRefresh) onRefresh(); // Parent Refresh (Global Data)

        // Local Refresh (V2 Signals) - defined inside effect, so we need to extract it or trigger it
        // Re-defining fetchV2Status outside effect or using a trigger state is better.
        // Let's use a trigger state for simplicity and safety.
        setManualRefreshTrigger(prev => prev + 1);
    };

    // [Ver 7.2.6] State to trigger local refresh
    const [manualRefreshTrigger, setManualRefreshTrigger] = useState(0);

    // [Ver 7.2.6] Separate Effect for V2 Status Fetching (Both Interval & Manual Trigger)
    React.useEffect(() => {
        const fetchV2Status = async () => {
            try {
                const [soxlRes, soxsRes, uproRes] = await Promise.all([
                    fetch('/api/v2/status/SOXL'),
                    fetch('/api/v2/status/SOXS'),
                    fetch('/api/v2/status/UPRO')
                ]);
                const soxlData = await soxlRes.json();
                const soxsData = await soxsRes.json();
                const uproData = await uproRes.json();

                if (soxlData.status === 'success' && soxsData.status === 'success') {
                    setV2Status({
                        SOXL: soxlData,
                        SOXS: soxsData,
                        UPRO: uproData.status === 'success' ? uproData : null
                    });
                }
            } catch (e) {
                console.error('V2 Status fetch error:', e);
            }
        };

        fetchV2Status();

        // Polling Logic
        let delay = 10000; // Default 10s
        if (pollingMode === 'off') {
            delay = null;
        } else if (pollingMode === 'auto' && marketStatus === 'closed') {
            delay = 60000; // Slow down to 60s when closed
        }

        if (!delay) return;

        const interval = setInterval(fetchV2Status, delay);
        return () => clearInterval(interval);
    }, [pollingMode, marketStatus, lastUpdateTime, manualRefreshTrigger]); // Add trigger dependency

    const activeStocks = stocks && Array.isArray(stocks)
        ? [...stocks].sort((a, b) => (b.current_ratio || 0) - (a.current_ratio || 0))
        : [];

    // Helper function for dual time formatting
    const formatDualTime = (timeStr) => {
        if (!timeStr) return '-';

        // Handle pre-formatted backend string (e.g. "2026-01-01 12:00 (US) / ...")
        if (typeof timeStr === 'string' && timeStr.includes(' / ') && timeStr.includes('(KR)')) {
            try {
                const parts = timeStr.split(' / ');
                if (parts.length === 2) {
                    return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                            <div>🇺🇸 {parts[0].replace('(US)', '').trim()} (NY)</div>
                            <div>🇰🇷 {parts[1].replace('(KR)', '').trim()} (KR)</div>
                        </div>
                    );
                }
            } catch (e) { return timeStr; }
        }

        try {
            const date = new Date(timeStr);
            if (isNaN(date.getTime())) return timeStr;

            const format = (d, tz) => {
                const parts = new Intl.DateTimeFormat('en-CA', {
                    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: false
                }).formatToParts(d);

                const get = (type) => parts.find(p => p.type === type).value;
                return `${get('year')}.${get('month')}.${get('day')} ${get('hour')}:${get('minute')}`;
            };

            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                    <div>🇺🇸 {format(date, 'America/New_York')} (NY)</div>
                    <div>🇰🇷 {format(date, 'Asia/Seoul')} (KR)</div>
                </div>
            );
        } catch (e) {
            return timeStr;
        }
    };

    return (
        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>

            {/* 1. Status Bar with Events */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', fontSize: '0.85rem', flexWrap: 'wrap', gap: '8px' }}>
                    {/* Left: Today Events */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', flex: '1 1 auto' }}>
                        {todayEvents.length > 0 && (
                            <>
                                <span style={{ color: '#f87171', fontWeight: 'bold', fontSize: '0.75rem' }}>📅</span>
                                {todayEvents.slice(0, 2).map((evt, i) => (
                                    <span key={i} style={{
                                        background: evt.importance === 'HIGH' ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.1)',
                                        color: evt.importance === 'HIGH' ? '#fca5a5' : '#93c5fd',
                                        padding: '2px 6px', borderRadius: '10px', fontSize: '0.7rem', fontWeight: '500'
                                    }}>
                                        {evt.event_time?.slice(0, 5)} {evt.title.length > 10 ? evt.title.slice(0, 10) + '..' : evt.title}
                                    </span>
                                ))}
                                {todayEvents.length > 2 && <span style={{ color: '#64748b', fontSize: '0.7rem' }}>+{todayEvents.length - 2}</span>}
                            </>
                        )}
                    </div>
                    {/* Right: Status */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{
                            color: market_regime?.regime?.includes('Bull') ? '#16a34a' : market_regime?.regime?.includes('Bear') ? '#dc2626' : '#9ca3af',
                            fontWeight: 'bold'
                        }}>
                            {market_regime?.regime?.includes('Bull') ? '상승장' : market_regime?.regime?.includes('Bear') ? '하락장' : '보합장'}
                        </span>
                        <span style={{
                            color: marketStatus === 'open' ? '#4ade80' :
                                (marketStatus === 'pre' || marketStatus === 'post' || marketStatus === 'pre-after') ? '#facc15' :
                                    (marketStatus === 'daytime' || marketStatus === 'day-market') ? '#38bdf8' : '#f87171',
                            fontWeight: '500'
                        }}>
                            {marketStatus === 'open' ? '정규장' :
                                (marketStatus === 'pre' || marketStatus === 'pre-after') ? '프리마켓' :
                                    marketStatus === 'post' ? '애프터마켓' :
                                        (marketStatus === 'daytime' || marketStatus === 'day-market') ? '주간거래' : '휴장'}
                        </span>
                        <span
                            onClick={() => {
                                const modes = ['auto', 'on', 'off'];
                                const nextIndex = (modes.indexOf(pollingMode) + 1) % modes.length;
                                setPollingMode(modes[nextIndex]);
                            }}
                            style={{
                                color: pollingMode === 'on' ? '#f97316' : pollingMode === 'off' ? '#3b82f6' : '#4ade80',
                                cursor: 'pointer', fontWeight: '500'
                            }}
                            title="클릭하여 폴링 모드 변경"
                        >
                            {pollingMode === 'auto' ? '자동' : pollingMode === 'on' ? '수동ON' : '수동OFF'}
                        </span>
                        <span
                            onClick={() => setShowJournal(!showJournal)}
                            style={{
                                color: showJournal ? '#fbbf24' : '#64748b',
                                cursor: 'pointer', fontWeight: '500'
                            }}
                        >
                            매매일지
                        </span>
                        <span style={{ width: '1px', height: '12px', background: '#334155', margin: '0 8px' }}></span>
                        <span
                            onClick={toggleMute}
                            style={{
                                color: isMuted ? '#f87171' : '#4ade80',
                                cursor: 'pointer', fontWeight: '500', fontSize: '1.1rem',
                                opacity: isMuted ? 0.7 : 1
                            }}
                            title={isMuted ? "음소거 해제" : "음소거"}
                        >
                            {isMuted ? '🔇' : '🔊'}
                        </span>
                    </div>
                </div>

                {/* Today's Key Alerts - Toggle Controlled */}
                {showJournal && <TodayEventsWidget />}


                {/* 2. Prime Guide : Action Plan (V3.5 Comprehensive Score) */}
                <div style={{ background: 'rgba(15, 23, 42, 0.9)', padding: '1.5rem', borderRadius: '20px', border: '1px solid rgba(56, 189, 248, 0.5)', boxShadow: '0 0 30px rgba(56, 189, 248, 0.1)', marginBottom: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem', flexWrap: 'wrap', gap: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ width: '12px', height: '12px', background: '#38bdf8', borderRadius: '50%', boxShadow: '0 0 15px #38bdf8', flexShrink: 0 }} />
                            <h3 style={{ margin: 0, fontSize: '1.4rem', color: '#38bdf8', fontWeight: '900', letterSpacing: '-0.5px', whiteSpace: 'nowrap' }}>청안 Prime Guide : Action Plan</h3>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', background: '#0f172a', padding: '4px 10px', borderRadius: '20px' }}>Ver 5.7 Market Intelligence</div>
                    </div>

                    {/* Dual Guide Layout */}
                    <div className="responsive-grid-2">
                        {['SOXL', 'SOXS'].map(ticker => {
                            const guideData = regimeDetails?.prime_guide || {};
                            const scoreObj = guideData.scores?.[ticker] || { score: 0, breakdown: {} };
                            const guideText = guideData.guides?.[ticker] || "분석 대기 중...";
                            const isSoxl = ticker === 'SOXL';
                            const color = isSoxl ? '#06b6d4' : '#a855f7';

                            // Get price and change data (동일 소스: BULL TOWER와 일치)
                            const renderInfo = v2Status[ticker]?.market_info || (isSoxl ? regimeDetails?.soxl : regimeDetails?.soxs);
                            const currentPrice = renderInfo?.current_price || 0;
                            const dailyChange = renderInfo?.change_pct ?? renderInfo?.daily_change ?? 0;

                            // Calculate Energy Score [Jian 1.1 - moved outside IIFE for total]
                            const soxlChange = regimeDetails?.soxl?.daily_change || 0;
                            const uproChange = regimeDetails?.upro?.daily_change || 0;
                            let relationIndex = 0;
                            if (Math.abs(uproChange) > 0.05) {
                                relationIndex = (soxlChange / uproChange) * 100;
                            }
                            let rawEnergy = (relationIndex - 100) / 20;
                            if (uproChange < 0) rawEnergy = -rawEnergy;
                            rawEnergy = Math.max(-10, Math.min(10, rawEnergy));
                            const energyScore = isSoxl ? Math.trunc(rawEnergy) : Math.trunc(-rawEnergy);

                            // Calculate frontend total score [Jian 1.1]
                            const d = scoreObj.cheongan_details || {};
                            const pureSum = (d.sig1 || 0) + (d.sig2 || 0) + (d.sig3 || 0);
                            const cheonganWithEnergy = pureSum + energyScore;

                            const indicatorTotal = (scoreObj.breakdown?.rsi || 0) + (scoreObj.breakdown?.macd || 0) +
                                (scoreObj.breakdown?.vol || 0) + (scoreObj.breakdown?.atr || 0);
                            const sellPenalty = scoreObj.breakdown?.sell_penalty || 0;
                            const realTotalScore = cheonganWithEnergy + indicatorTotal + sellPenalty;

                            return (
                                <div key={ticker} style={{ width: '100%', background: `rgba(${isSoxl ? '6,182,212' : '168,85,247'}, 0.05)`, padding: '1.5rem', borderRadius: '16px', border: `1px solid ${color}33` }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                        <h4 style={{ margin: 0, color: color, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {isSoxl ? '🐂' : '🐻'} {ticker} 전략
                                        </h4>
                                        <div style={{ textAlign: 'right' }}>
                                            <span style={{ fontSize: '0.8rem', color: isSoxl ? '#cffafe' : '#f3e8ff', display: 'block' }}>보유 매력도 (Holding Score)</span>
                                            <span style={{ fontSize: '1.5rem', fontWeight: '900', color: color }}>
                                                {realTotalScore}점
                                            </span>
                                            <div style={{ fontSize: '0.85rem', color: dailyChange >= 0 ? '#4ade80' : '#f87171', marginTop: '4px' }}>
                                                ${currentPrice.toFixed(2)} <span style={{ fontWeight: 'bold' }}>({dailyChange >= 0 ? '+' : ''}{dailyChange.toFixed(2)}%)</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Score Breakdown 2-Column Layout (V6.4.9) */}
                                    {(() => {
                                        // Calculate Energy Score from UPRO relationIndex
                                        const soxlChange = regimeDetails?.soxl?.daily_change || 0;
                                        const uproChange = regimeDetails?.upro?.daily_change || 0;
                                        let relationIndex = 0;
                                        if (Math.abs(uproChange) > 0.05) {
                                            relationIndex = (soxlChange / uproChange) * 100;
                                        }
                                        // Energy Score Logic [Jian 1.1]
                                        // S = (RI - 100) / 20 (상승 시), S = -(RI - 100) / 20 (하락 시)
                                        // 제한: ±10점
                                        let rawEnergy = (relationIndex - 100) / 20;
                                        if (uproChange < 0) rawEnergy = -rawEnergy;  // 시장 하락 시 부호 반전
                                        rawEnergy = Math.max(-10, Math.min(10, rawEnergy));  // ±10 제한
                                        const energyScore = isSoxl
                                            ? Math.trunc(rawEnergy)
                                            : Math.trunc(-rawEnergy);

                                        // Recalculate cheongan total with energy
                                        // [Ver 7.2.7 Fix] Force Subtotal to match displayed rows (Pure Algo Sum)
                                        const d = scoreObj.cheongan_details || {};
                                        const pureSum = (d.sig1 || 0) + (d.sig2 || 0) + (d.sig3 || 0);
                                        const cheonganWithEnergy = pureSum + energyScore;

                                        return (
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '15px', fontSize: '0.75rem' }}>
                                                {/* 좌측: 청안 지수 */}
                                                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '10px', borderRadius: '8px' }}>
                                                    <div style={{ fontWeight: 'bold', color: color, marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>
                                                        🔥 청안지수 <span style={{ fontWeight: 'normal', color: '#94a3b8' }}>(최대 60점)</span>
                                                    </div>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>1차 (5분 GC)</span>
                                                            <span style={{ color: (scoreObj.cheongan_details?.sig1 || 0) > 0 ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {(scoreObj.cheongan_details?.sig1 || 0) > 0 ? `+${scoreObj.cheongan_details?.sig1}` : '0'}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>2차 (+1%)</span>
                                                            <span style={{ color: (scoreObj.cheongan_details?.sig2 || 0) > 0 ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {(scoreObj.cheongan_details?.sig2 || 0) > 0 ? `+${scoreObj.cheongan_details?.sig2}` : '0'}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>3차 (30분 GC)</span>
                                                            <span style={{ color: (scoreObj.cheongan_details?.sig3 || 0) > 0 ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {(scoreObj.cheongan_details?.sig3 || 0) > 0 ? `+${scoreObj.cheongan_details?.sig3}` : '0'}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#fbbf24' }}>⚡ 에너지 <span style={{ fontSize: '0.65rem', color: '#64748b' }}>({Math.abs(relationIndex).toFixed(0)}%)</span></span>
                                                            <span style={{ color: energyScore > 0 ? '#4ade80' : energyScore < 0 ? '#f87171' : '#64748b', fontWeight: 'bold' }}>
                                                                {energyScore > 0 ? '+' : ''}{energyScore}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: '4px' }}>
                                                            <span style={{ fontWeight: 'bold', color: '#fff' }}>소계</span>
                                                            <span style={{ fontWeight: '900', color: color }}>{cheonganWithEnergy}</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* 우측: 보조지표 */}
                                                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '10px', borderRadius: '8px' }}>
                                                    <div style={{ fontWeight: 'bold', color: '#94a3b8', marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>
                                                        📊 보조지표 <span style={{ fontWeight: 'normal', color: '#64748b' }}>(±40점)</span>
                                                    </div>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>RSI</span>
                                                            <span style={{ color: (scoreObj.breakdown?.rsi || 0) > 0 ? '#4ade80' : (scoreObj.breakdown?.rsi || 0) < 0 ? '#f87171' : '#ccc', fontWeight: 'bold' }}>
                                                                {scoreObj.breakdown?.rsi > 0 ? '+' : ''}{scoreObj.breakdown?.rsi || 0}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>MACD</span>
                                                            <span style={{ color: (scoreObj.breakdown?.macd || 0) > 0 ? '#4ade80' : (scoreObj.breakdown?.macd || 0) < 0 ? '#f87171' : '#ccc', fontWeight: 'bold' }}>
                                                                {scoreObj.breakdown?.macd > 0 ? '+' : ''}{scoreObj.breakdown?.macd || 0}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>Volume</span>
                                                            <span style={{ color: (scoreObj.breakdown?.vol || 0) > 0 ? '#4ade80' : (scoreObj.breakdown?.vol || 0) < 0 ? '#f87171' : '#ccc', fontWeight: 'bold' }}>
                                                                {scoreObj.breakdown?.vol > 0 ? '+' : ''}{scoreObj.breakdown?.vol || 0}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>ATR</span>
                                                            <span style={{ color: (scoreObj.breakdown?.atr || 0) > 0 ? '#4ade80' : (scoreObj.breakdown?.atr || 0) < 0 ? '#f87171' : '#ccc', fontWeight: 'bold' }}>
                                                                {scoreObj.breakdown?.atr > 0 ? '+' : ''}{scoreObj.breakdown?.atr || 0}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: '4px' }}>
                                                            <span style={{ fontWeight: 'bold', color: '#fff' }}>소계</span>
                                                            <span style={{ fontWeight: '900', color: '#94a3b8' }}>
                                                                {(scoreObj.breakdown?.rsi || 0) + (scoreObj.breakdown?.macd || 0) + (scoreObj.breakdown?.vol || 0) + (scoreObj.breakdown?.atr || 0)}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })()}

                                    {/* 총점 + 매도경고 */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '10px 12px', borderRadius: '8px', marginBottom: '15px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                            <span style={{ fontWeight: 'bold', color: '#fff', fontSize: '0.85rem' }}>📌 총점</span>
                                            {sellPenalty !== 0 && (
                                                <span style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', padding: '2px 8px', borderRadius: '10px', fontSize: '0.7rem', fontWeight: 'bold' }}>
                                                    ⚠️ 매도경고 {sellPenalty}
                                                </span>
                                            )}
                                        </div>
                                        <span style={{ fontWeight: '900', fontSize: '1.2rem', color: color }}>{realTotalScore}점</span>
                                    </div>


                                </div>
                            )
                        })}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
                    <V2SignalStatus
                        title="SOXL (BULL TOWER)"
                        buyStatus={v2Status.SOXL?.buy || regimeDetails?.soxl?.v2_buy}
                        sellStatus={v2Status.SOXL?.sell || regimeDetails?.soxl?.v2_sell}
                        renderInfo={v2Status.SOXL?.market_info || regimeDetails?.soxl}
                        metrics={v2Status.SOXL?.metrics}
                        bbi={v2Status.SOXL?.bbi}
                        isBear={false}
                        onRefresh={handleRefresh}
                    />
                    <V2SignalStatus
                        title="SOXS (BEAR TOWER)"
                        buyStatus={v2Status.SOXS?.buy || regimeDetails?.soxs?.v2_buy}
                        sellStatus={v2Status.SOXS?.sell || regimeDetails?.soxs?.v2_sell}
                        renderInfo={v2Status.SOXS?.market_info || regimeDetails?.soxs}
                        metrics={v2Status.SOXS?.metrics}
                        bbi={v2Status.SOXS?.bbi}
                        isBear={true}
                        onRefresh={handleRefresh}
                    />
                </div>

                {/* [Ver 6.6.6] BBI (Box Breakout Index) Display - SOXL/SOXS 나란히 */}
                <div className="responsive-grid-2" style={{ marginBottom: '1.5rem' }}>
                    {['SOXL', 'SOXS'].map(ticker => {
                        const bbi = v2Status[ticker]?.bbi;
                        const isSoxl = ticker === 'SOXL';
                        const color = isSoxl ? '#06b6d4' : '#a855f7';

                        if (!bbi) return null;

                        return (
                            <div key={ticker} style={{ padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: `1px solid ${color}22` }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span style={{ fontSize: '0.8rem', color: color, fontWeight: 'bold' }}>📦 {ticker} BBI</span>
                                        <span style={{ fontSize: '0.65rem', color: '#64748b', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                                            -10 ~ +10
                                        </span>
                                    </div>
                                    <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#60a5fa' }}>
                                        {bbi.bbi > 0 ? '+' : ''}{bbi.bbi}
                                    </span>
                                </div>

                                {/* Gauge Bar */}
                                <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', position: 'relative', overflow: 'hidden', marginBottom: '8px', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.3)' }}>
                                    <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', background: '#475569', zIndex: 10 }}></div>
                                    <div style={{
                                        position: 'absolute', top: 0, bottom: 0,
                                        left: bbi.bbi >= 0 ? '50%' : `${Math.max(0, 50 + (bbi.bbi * 5))}%`,
                                        width: `${Math.min(50, Math.abs(bbi.bbi) * 5)}%`,
                                        background: bbi.bbi < 0 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #10b981, #34d399)',
                                        borderRadius: '4px', transition: 'all 0.5s ease-out'
                                    }}></div>
                                </div>

                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', alignItems: 'center' }}>
                                    <span style={{ color: bbi.bbi < 0 ? '#fbbf24' : '#34d399', fontWeight: 'bold' }}>
                                        {bbi.bbi < 0 ? '💤 박스권' : '🚀 추세'}
                                    </span>
                                    <span style={{ color: '#94a3b8', fontWeight: '500' }}>{bbi.status}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* [Ver 5.4] Independent Price Level Alert Panel */}
                {(() => {
                    // SOXL, SOXS: v2Status에서 가져오기 (안정적)
                    const soxlPrice = v2Status.SOXL?.market_info?.current_price || 0;
                    const soxsPrice = v2Status.SOXS?.market_info?.current_price || 0;

                    // UPRO: v2Status에서 우선, 없으면 market.indices에서 폴백
                    const uproV2 = v2Status.UPRO?.market_info;
                    const indices = Array.isArray(market?.indices) ? market.indices : [];
                    const uproFallback = indices.find(m => m.ticker === 'UPRO');

                    const uproPrice = uproV2?.current_price || (uproFallback ? Number(uproFallback.current_price || uproFallback.price) : 0);
                    const uproChange = uproV2?.change_pct ?? (uproFallback ? Number(uproFallback.change_pct || uproFallback.change_rate || 0) : 0);
                    const soxlChange = v2Status.SOXL?.market_info?.change_pct || 0;

                    let relationIndex = 0;
                    if (uproChange !== 0) {
                        relationIndex = (soxlChange / uproChange) * 100;
                    }

                    return (
                        <div style={{ marginBottom: '1.5rem' }}>
                            {/* UPRO Chart (Requested) */}
                            <div style={{ marginBottom: '1rem' }}>
                                <PriceAlertChart ticker="UPRO" currentPrice={uproPrice} changePct={uproChange} relationIndex={relationIndex} />
                            </div>

                            <div className="responsive-grid-2">
                                <PriceLevelAlerts ticker="SOXL" currentPrice={soxlPrice} />
                                <PriceLevelAlerts ticker="SOXS" currentPrice={soxsPrice} />
                            </div>
                        </div>
                    );
                })()}

                {/* 3. Bottom Grid: Intelligence & History */}


                {/* Col 2: Recent Cross History (SOXL / SOXS) */}
                <div className="responsive-grid-2">

                    {['SOXL', 'SOXS'].map(ticker => {
                        // Use Persistent DB History instead of Simulation
                        const history = dbSignals[ticker] || [];
                        const mainColor = ticker === 'SOXL' ? '#06b6d4' : '#a855f7';
                        const title = ticker === 'SOXL' ? 'SOXL (BULL)' : 'SOXS (BEAR)';

                        return (
                            <div key={ticker} style={{
                                background: 'rgba(0,0,0,0.25)', padding: '1.2rem', borderRadius: '16px', border: `1px solid ${mainColor}33`
                            }}>
                                <h4 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: mainColor, display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px' }}>
                                    <span style={{ fontSize: '1.2rem' }}>{ticker === 'SOXL' ? '🚀' : '🛡️'}</span> {title} Signal History
                                </h4>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>

                                    {/* DB Signal History List */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {
                                            (() => {
                                                const signals = history;

                                                if (signals.length === 0) {
                                                    return (
                                                        <div style={{ padding: '20px', textAlign: 'center', color: '#666', fontSize: '0.8rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                                                            Waiting for signals...
                                                        </div>
                                                    );
                                                }

                                                return signals.map((sig, idx) => {
                                                    // Determine Type (BUY/SELL)
                                                    const isBuy = (sig.signal_type && sig.signal_type.includes('BUY')) ||
                                                        (sig.position && sig.position.includes('매수')) ||
                                                        (sig.position && sig.position.includes('진입'));

                                                    // Context/Reason
                                                    const reason = sig.signal_reason || sig.position || sig.interpretation || '-';

                                                    // Time Formatting
                                                    let displayTime = '-';
                                                    if (sig.signal_time) {
                                                        const d = new Date(sig.signal_time);
                                                        const mo = String(d.getMonth() + 1).padStart(2, '0');
                                                        const dy = String(d.getDate()).padStart(2, '0');
                                                        const hr = String(d.getHours()).padStart(2, '0');
                                                        const mi = String(d.getMinutes()).padStart(2, '0');
                                                        displayTime = `${mo}-${dy} ${hr}:${mi}`;
                                                    } else if (sig.created_at) {
                                                        const d = new Date(sig.created_at);
                                                        const mo = String(d.getMonth() + 1).padStart(2, '0');
                                                        const dy = String(d.getDate()).padStart(2, '0');
                                                        const hr = String(d.getHours()).padStart(2, '0');
                                                        const mi = String(d.getMinutes()).padStart(2, '0');
                                                        displayTime = `${mo}-${dy} ${hr}:${mi}`;
                                                    }

                                                    // Single Line Format: MM-DD HH:mm  [Type] [Reason]  $Price
                                                    return (
                                                        <div key={idx} style={{
                                                            background: 'rgba(255,255,255,0.03)',
                                                            padding: '6px 10px',
                                                            borderRadius: '6px',
                                                            borderLeft: isBuy ? `3px solid ${mainColor}` : '3px solid #777',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            fontSize: '0.85rem',
                                                            color: '#ddd',
                                                            gap: '8px'
                                                        }}>
                                                            {/* Time */}
                                                            <span style={{ color: '#888', fontSize: '0.8rem', minWidth: '85px' }}>{displayTime}</span>

                                                            {/* Type */}
                                                            <span style={{
                                                                color: isBuy ? '#4ade80' : '#f87171',
                                                                fontWeight: 'bold',
                                                                minWidth: '30px'
                                                            }}>
                                                                {isBuy ? '매수' : '매도'}
                                                            </span>

                                                            {/* Reason */}
                                                            <span style={{
                                                                color: '#ccc',
                                                                flex: 1,
                                                                whiteSpace: 'nowrap',
                                                                overflow: 'hidden',
                                                                textOverflow: 'ellipsis'
                                                            }}>
                                                                {reason}
                                                            </span>

                                                            {/* Price */}
                                                            <span style={{ fontWeight: 'bold', color: '#fff' }}>
                                                                ${Number(sig.price).toFixed(2)}
                                                            </span>
                                                        </div>
                                                    );
                                                });
                                            })()
                                        }
                                    </div>


                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* 4. System Trading Panel (Auto-Trading Log) */}
                <SystemTradingPanel />

                <style>{`
                        @keyframes pulse {
                            0 % { transform: scale(1); opacity: 1; }
                            50 % { transform: scale(1.05); opacity: 0.9; }
                            100 % { transform: scale(1); opacity: 1; }
                        }
                        @keyframes flash {
                            0 % { opacity: 1; }
                            50 % { opacity: 0.3; }
                            100 % { opacity: 1; }
                        }
                .glass-panel {
                        /* Existing styles inherited */
                        backdrop-filter: blur(12px);
                }
            `}</style>
            </div>
        </div >
    );
};

// [Ver 7.2] System Trading Panel (Split SOXL/SOXS Tables)
const SystemTradingPanel = () => {
    const [trades, setTrades] = useState({ soxl: [], soxs: [] });

    const fetchData = async () => {
        try {
            // Fetch both Open and Closed trades
            // limit=50 to show recent history
            const [statusRes, historyRes] = await Promise.all([
                fetch('/api/trading/status'),
                fetch('/api/trading/history?limit=50')
            ]);

            let openTrades = [];
            let closedTrades = [];

            if (statusRes.ok) openTrades = await statusRes.json();
            if (historyRes.ok) closedTrades = await historyRes.json();

            // Combine and Sort
            const allTrades = [...openTrades, ...closedTrades];

            // Split by Ticker
            const soxl = allTrades.filter(t => t.ticker === 'SOXL').sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));
            const soxs = allTrades.filter(t => t.ticker === 'SOXS').sort((a, b) => new Date(b.entry_time) - new Date(a.entry_time));

            setTrades({ soxl, soxs });

        } catch (e) {
            console.error("Trading Data Error:", e);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    const formatDate = (isoString) => {
        if (!isoString) return '-';
        const d = new Date(isoString);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    };

    const formatTime = (isoString) => {
        if (!isoString) return '-';
        const d = new Date(isoString);
        return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    };

    const formatFullDateTime = (isoString) => {
        if (!isoString) return '-';
        const d = new Date(isoString);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}-${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    }

    const renderTable = (ticker, data) => (
        <div className="glass-panel" style={{ padding: '15px', marginBottom: '20px', overflowX: 'auto' }}>
            <h4 style={{
                color: ticker === 'SOXL' ? '#06b6d4' : '#a855f7',
                margin: '0 0 10px 0',
                fontSize: '1.1rem',
                borderBottom: `2px solid ${ticker === 'SOXL' ? 'rgba(6,182,212,0.3)' : 'rgba(168,85,247,0.3)'}`,
                paddingBottom: '5px'
            }}>
                {ticker} Auto-Trading Log
            </h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', color: '#ddd' }}>
                <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#888' }}>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Date</th>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Time</th>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Entry Action</th>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Exit Time</th>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Exit Action</th>
                        <th style={{ padding: '8px', textAlign: 'right' }}>Profit</th>
                    </tr>
                </thead>
                <tbody>
                    {data.length === 0 ? (
                        <tr><td colSpan="6" style={{ padding: '15px', textAlign: 'center', color: '#666' }}>No records found</td></tr>
                    ) : (
                        data.map((trade, idx) => {
                            const isWin = trade.profit_pct > 0;
                            const profitColor = isWin ? '#ef4444' : trade.profit_pct < 0 ? '#3b82f6' : '#ddd'; // Red win, Blue loss
                            return (
                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '8px' }}>{formatDate(trade.entry_time)}</td>
                                    <td style={{ padding: '8px' }}>{formatTime(trade.entry_time)}</td>
                                    <td style={{ padding: '8px', color: '#ddd' }}>70점 매수</td>
                                    <td style={{ padding: '8px' }}>{trade.status === 'CLOSED' ? formatFullDateTime(trade.exit_time) : '-'}</td>
                                    <td style={{ padding: '8px' }}>{trade.status === 'CLOSED' ? '50점 매도' : '-'}</td>
                                    <td style={{ padding: '8px', textAlign: 'right', color: trade.status === 'CLOSED' ? profitColor : '#aaa', fontWeight: 'bold' }}>
                                        {trade.status === 'CLOSED' ? `${trade.profit_pct}%` : 'Running'}
                                    </td>
                                </tr>
                            );
                        })
                    )}
                </tbody>
            </table>
        </div>
    );

    return (
        <div style={{ marginTop: '2rem' }}>
            <h3 style={{
                color: '#fff', fontSize: '1.2rem', margin: '0 0 1rem 0',
                display: 'flex', alignItems: 'center', gap: '8px',
                borderLeft: '4px solid #f59e0b', paddingLeft: '12px'
            }}>
                🤖 System Trading Log <span style={{ fontSize: '0.8rem', color: '#888', fontWeight: 'normal' }}>(Score Strategy)</span>
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {renderTable('SOXL', trades.soxl)}
                {renderTable('SOXS', trades.soxs)}
            </div>
        </div>
    );
};

export default MarketInsight;
