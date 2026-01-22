import React from 'react';
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


const ManualTestPanel = ({ onRefresh, marketData, v2Status }) => {
    const [inputs, setInputs] = React.useState({
        SOXL: { price: '', change: '', rsi: '', vr: '', atr: '', pr1: '' },
        SOXS: { price: '', change: '', rsi: '', vr: '', atr: '', pr1: '' }
    });

    // 현재 값 가져오기 Helper
    const getCurrent = (ticker, type) => {
        if (type === 'price' || type === 'change') {
            if (!marketData || !Array.isArray(marketData)) return '';
            const item = marketData.find(m => m.ticker === ticker);
            if (!item) return '';
            return type === 'price' ? item.current_price : item.change_pct;
        } else {
            // Indicators
            const metrics = v2Status?.[ticker]?.metrics;
            if (!metrics) return '';
            const map = { rsi: 'rsi_14', vr: 'vol_ratio', atr: 'atr', pr1: 'pivot_r1' };
            return metrics[map[type]] || '';
        }
    };

    const handleChange = (ticker, field, value) => {
        setInputs({
            ...inputs,
            [ticker]: { ...inputs[ticker], [field]: value }
        });
    };

    const handleSubmit = async (ticker) => {
        const inp = inputs[ticker];
        const price = inp.price || getCurrent(ticker, 'price');
        const change = inp.change || getCurrent(ticker, 'change');

        if (!price || parseFloat(price) <= 0) return;

        try {
            const payload = {
                ticker,
                price: parseFloat(price),
                change_pct: parseFloat(change) || 0,
                indicators: {
                    rsi: inp.rsi ? parseFloat(inp.rsi) : null,
                    vr: inp.vr ? parseFloat(inp.vr) : null,
                    atr: inp.atr ? parseFloat(inp.atr) : null,
                    pr1: inp.pr1 ? parseFloat(inp.pr1) : null
                }
            };

            const res = await fetch('/api/market-indices/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'success') {
                // Clear inputs
                setInputs({ ...inputs, [ticker]: { price: '', change: '', rsi: '', vr: '', atr: '', pr1: '' } });
                if (onRefresh) onRefresh();
            }
        } catch (e) {
            console.error('Manual update error:', e);
        }
    };

    const inputStyle = {
        background: '#0f172a', border: '1px solid #334155', color: '#fff',
        borderRadius: '6px', fontSize: '0.8rem', padding: '0.4rem', flex: 1, minWidth: '60px'
    };

    return (
        <div style={{
            background: 'rgba(56, 189, 248, 0.05)', padding: '1.2rem',
            borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.2)', marginBottom: '1rem'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1rem' }}>
                <div style={{ fontSize: '1.2rem' }}>🧪</div>
                <h3 style={{ margin: 0, color: '#38bdf8', fontSize: '1rem', fontWeight: '700' }}>수동 테스트 (가격 & 보조지표)</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {['SOXL', 'SOXS'].map(ticker => (
                    <div key={ticker} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '8px' }}>
                        <label style={{ width: '40px', fontSize: '0.9rem', color: '#38bdf8', fontWeight: '700' }}>{ticker}</label>

                        <input type="number" step="0.01" placeholder={`$${getCurrent(ticker, 'price')}`} value={inputs[ticker].price} onChange={e => handleChange(ticker, 'price', e.target.value)} style={{ ...inputStyle, minWidth: '70px' }} title="Current Price" />
                        <input type="number" step="0.1" placeholder={`${getCurrent(ticker, 'change')}%`} value={inputs[ticker].change} onChange={e => handleChange(ticker, 'change', e.target.value)} style={{ ...inputStyle, width: '60px' }} title="Change %" />

                        <div style={{ width: '1px', height: '20px', background: '#334155', margin: '0 4px' }}></div>

                        <input type="number" placeholder={`RSI ${getCurrent(ticker, 'rsi')}`} value={inputs[ticker].rsi} onChange={e => handleChange(ticker, 'rsi', e.target.value)} style={inputStyle} title="RSI" />
                        <input type="number" placeholder={`VR ${getCurrent(ticker, 'vr')}`} value={inputs[ticker].vr} onChange={e => handleChange(ticker, 'vr', e.target.value)} style={inputStyle} title="Volume Ratio" />
                        <input type="number" placeholder={`ATR ${getCurrent(ticker, 'atr')}`} value={inputs[ticker].atr} onChange={e => handleChange(ticker, 'atr', e.target.value)} style={inputStyle} title="ATR" />
                        <input type="number" placeholder={`PR1 ${getCurrent(ticker, 'pr1')}`} value={inputs[ticker].pr1} onChange={e => handleChange(ticker, 'pr1', e.target.value)} style={inputStyle} title="Pivot R1" />

                        <button onClick={() => handleSubmit(ticker)} style={{
                            padding: '0.4rem 0.8rem', background: '#38bdf8', color: '#0f172a',
                            border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.8rem', marginLeft: 'auto'
                        }}>적용</button>
                    </div>
                ))}
            </div>
        </div>
    );
};

const MarketInsight = ({ market, stocks, signalHistory, onRefresh, pollingMode, setPollingMode, marketStatus, lastUpdateTime, isMuted, toggleMute }) => {
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

    React.useEffect(() => {
        const fetchV2Status = async () => {
            try {
                const [soxlRes, soxsRes] = await Promise.all([
                    fetch('/api/v2/status/SOXL'),
                    fetch('/api/v2/status/SOXS')
                ]);
                const soxlData = await soxlRes.json();
                const soxsData = await soxsRes.json();

                if (soxlData.status === 'success' && soxsData.status === 'success') {
                    setV2Status({
                        SOXL: soxlData,
                        SOXS: soxsData
                    });
                }
            } catch (e) {
                console.error('V2 Status fetch error:', e);
            }
        };

        fetchV2Status();
        fetchV2Status();

        // Polling Logic
        let delay = 10000; // Default 10s
        if (pollingMode === 'off') {
            delay = null;
        } else if (pollingMode === 'auto' && marketStatus === 'closed') {
            delay = 60000; // Slow down to 60s when closed
        }
        // 'on' mode or 'auto' + open/pre-after/day-market uses default 10s

        if (!delay) return;

        const interval = setInterval(fetchV2Status, delay);
        return () => clearInterval(interval);
    }, [pollingMode, marketStatus, lastUpdateTime]);

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

                            return (
                                <div key={ticker} style={{ width: '100%', background: `rgba(${isSoxl ? '6,182,212' : '168,85,247'}, 0.05)`, padding: '1.5rem', borderRadius: '16px', border: `1px solid ${color}33` }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                        <h4 style={{ margin: 0, color: color, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {isSoxl ? '🐂' : '🐻'} {ticker} 전략
                                        </h4>
                                        <div style={{ textAlign: 'right' }}>
                                            <span style={{ fontSize: '0.8rem', color: isSoxl ? '#cffafe' : '#f3e8ff', display: 'block' }}>보유 매력도 (Holding Score)</span>
                                            <span style={{ fontSize: '1.5rem', fontWeight: '900', color: color }}>
                                                {scoreObj.score}점
                                            </span>
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
                                        // Energy Score Logic (Ver 6.4.10)
                                        // 연관지수 >= 100%: SOXL=+, SOXS=-
                                        // 연관지수 < 100%: SOXL=-, SOXS=+
                                        const baseEnergy = Math.trunc(relationIndex / 10);
                                        let energyScore;
                                        if (relationIndex >= 100) {
                                            energyScore = isSoxl ? baseEnergy : -baseEnergy;
                                        } else {
                                            energyScore = isSoxl ? -baseEnergy : baseEnergy;
                                        }

                                        // Recalculate cheongan total with energy
                                        const baseCheongan = scoreObj.breakdown?.cheongan || 0;
                                        const cheonganWithEnergy = baseCheongan + energyScore;

                                        return (
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '15px', fontSize: '0.75rem' }}>
                                                {/* 좌측: 청안 지수 */}
                                                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '10px', borderRadius: '8px' }}>
                                                    <div style={{ fontWeight: 'bold', color: color, marginBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '4px' }}>
                                                        🔥 청안지수 <span style={{ fontWeight: 'normal', color: '#94a3b8' }}>(최대 80점)</span>
                                                    </div>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>1차 (5분 GC)</span>
                                                            <span style={{ color: v2Status?.[ticker]?.buy?.buy_sig1_yn === 'Y' ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {v2Status?.[ticker]?.buy?.buy_sig1_yn === 'Y' ? '+20' : '0'}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>2차 (+1%)</span>
                                                            <span style={{ color: v2Status?.[ticker]?.buy?.buy_sig2_yn === 'Y' ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {v2Status?.[ticker]?.buy?.buy_sig2_yn === 'Y' ? '+20' : '0'}
                                                            </span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                                            <span style={{ color: '#ccc' }}>3차 (30분 GC)</span>
                                                            <span style={{ color: v2Status?.[ticker]?.buy?.buy_sig3_yn === 'Y' ? '#4ade80' : '#64748b', fontWeight: 'bold' }}>
                                                                {v2Status?.[ticker]?.buy?.buy_sig3_yn === 'Y' ? '+30' : '0'}
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
                                            {(scoreObj.breakdown?.sell_penalty || 0) !== 0 && (
                                                <span style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', padding: '2px 8px', borderRadius: '10px', fontSize: '0.7rem', fontWeight: 'bold' }}>
                                                    ⚠️ 매도경고 {scoreObj.breakdown?.sell_penalty}
                                                </span>
                                            )}
                                        </div>
                                        <span style={{ fontWeight: '900', fontSize: '1.2rem', color: color }}>{scoreObj.score}점</span>
                                    </div>

                                    {/* Guide Commentary */}
                                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7', fontSize: '0.88rem', color: isSoxl ? '#cffafe' : '#f3e8ff', fontFamily: "'Noto Sans KR', sans-serif", background: 'rgba(0,0,0,0.15)', padding: '12px', borderRadius: '8px', borderLeft: `3px solid ${color}` }}>
                                        {guideText}
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
                        isBear={false}
                        onRefresh={onRefresh}
                    />
                    <V2SignalStatus
                        title="SOXS (BEAR TOWER)"
                        buyStatus={v2Status.SOXS?.buy || regimeDetails?.soxs?.v2_buy}
                        sellStatus={v2Status.SOXS?.sell || regimeDetails?.soxs?.v2_sell}
                        renderInfo={v2Status.SOXS?.market_info || regimeDetails?.soxs}
                        metrics={v2Status.SOXS?.metrics}
                        isBear={true}
                        onRefresh={onRefresh}
                    />
                </div>

                {/* [Ver 5.4] Independent Price Level Alert Panel */}
                {(() => {
                    const indices = Array.isArray(market?.indices) ? market.indices : [];
                    const soxlData = indices.find(m => m.ticker === 'SOXL');
                    const soxsData = indices.find(m => m.ticker === 'SOXS');
                    const uproData = indices.find(m => m.ticker === 'UPRO');

                    const soxlPrice = soxlData ? Number(soxlData.current_price || soxlData.price) : 0;
                    const soxsPrice = soxsData ? Number(soxsData.current_price || soxsData.price) : 0;
                    const uproPrice = uproData ? Number(uproData.current_price || uproData.price) : 0;
                    const soxlChange = soxlData ? Number(soxlData.change_pct || soxlData.change_rate || 0) : 0;
                    const uproChange = uproData ? Number(uproData.change_pct || uproData.change_rate || 0) : 0;

                    let relationIndex = null;
                    if (Math.abs(uproChange) > 0.05) { // Minimum threshold to avoid noise
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

                {/* 수동 테스트 패널 (Params 전달) */}
                <ManualTestPanel onRefresh={onRefresh} marketData={market?.indices} v2Status={v2Status} />


                {/* 3. Bottom Grid: Intelligence & History */}
                <div className="responsive-grid-2-1">

                    {/* Col 1: Market Intelligence Center (Detailed) */}
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '16px' }}>
                        <h4 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px' }}>
                            🌐 Market Intelligence Center (심층 분석)
                        </h4>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                            {['SOXL', 'SOXS'].map(ticker => {
                                // Use v2Status metrics from DB (market_indicators_snapshot)
                                const dbMetrics = v2Status?.[ticker]?.metrics || {};
                                const guideData = regimeDetails?.prime_guide || {};
                                const scoreObj = guideData.scores?.[ticker] || { score: 0, breakdown: {} };
                                const breakdown = scoreObj.breakdown || {};
                                const comment = guideData.tech_comments?.[ticker] || "-";

                                const color = ticker === 'SOXL' ? '#06b6d4' : '#a855f7';

                                // Helper for score color
                                const getScoreColor = (score) => score > 0 ? '#4ade80' : score < 0 ? '#f87171' : '#888';
                                const formatScore = (score) => score > 0 ? `+${score}` : score;

                                return (
                                    <div key={ticker} style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '12px', border: `1px solid ${color}22` }}>
                                        {/* Header */}
                                        <div style={{ fontWeight: 'bold', color: color, marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontSize: '1rem' }}>{ticker} 안티그래비티 스코어</span>
                                            <span style={{
                                                fontSize: '1.3rem', fontWeight: '900',
                                                color: scoreObj.score >= 90 ? '#22c55e' : scoreObj.score >= 70 ? '#4ade80' : scoreObj.score >= 60 ? '#fbbf24' : '#94a3b8'
                                            }}>
                                                {scoreObj.score}점
                                            </span>
                                        </div>

                                        {/* 청안 지수 */}
                                        <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '6px', marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: '#e2e8f0', fontSize: '0.85rem' }}>📊 청안 지수 (V2 신호)</span>
                                            <span style={{ color: breakdown.cheongan >= 60 ? '#4ade80' : breakdown.cheongan >= 30 ? '#fbbf24' : '#94a3b8', fontWeight: 'bold' }}>
                                                {breakdown.cheongan || 0}점
                                            </span>
                                        </div>

                                        {/* 보조지표 그리드 */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.8rem' }}>
                                            {/* RSI */}
                                            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>RSI (14)</span>
                                                    <span style={{ color: getScoreColor(breakdown.rsi), fontWeight: 'bold', fontSize: '0.75rem' }}>
                                                        {formatScore(breakdown.rsi || 0)}
                                                    </span>
                                                </div>
                                                <div style={{ color: '#e2e8f0', fontWeight: 'bold', marginTop: '2px' }}>
                                                    {dbMetrics.rsi_14 ? Number(dbMetrics.rsi_14).toFixed(1) : '-'}
                                                </div>
                                            </div>
                                            {/* MACD */}
                                            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>MACD</span>
                                                    <span style={{ color: getScoreColor(breakdown.macd), fontWeight: 'bold', fontSize: '0.75rem' }}>
                                                        {formatScore(breakdown.macd || 0)}
                                                    </span>
                                                </div>
                                                <div style={{ color: (Number(dbMetrics.macd) > Number(dbMetrics.macd_sig)) ? '#4ade80' : '#f87171', fontWeight: 'bold', marginTop: '2px' }}>
                                                    {dbMetrics.macd ? Number(dbMetrics.macd).toFixed(3) : '-'}
                                                </div>
                                            </div>
                                            {/* Vol Ratio */}
                                            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>Vol Ratio</span>
                                                    <span style={{ color: getScoreColor(breakdown.vol), fontWeight: 'bold', fontSize: '0.75rem' }}>
                                                        {formatScore(breakdown.vol || 0)}
                                                    </span>
                                                </div>
                                                <div style={{ color: '#e2e8f0', fontWeight: 'bold', marginTop: '2px' }}>
                                                    {dbMetrics.vol_ratio ? Number(dbMetrics.vol_ratio).toFixed(1) + 'x' : '-'}
                                                </div>
                                            </div>
                                            {/* ATR */}
                                            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>ATR</span>
                                                    <span style={{ color: getScoreColor(breakdown.atr), fontWeight: 'bold', fontSize: '0.75rem' }}>
                                                        {formatScore(breakdown.atr || 0)}
                                                    </span>
                                                </div>
                                                <div style={{ color: '#e2e8f0', fontWeight: 'bold', marginTop: '2px' }}>
                                                    {dbMetrics.atr ? Number(dbMetrics.atr).toFixed(2) : '-'}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Evaluation & Comment */}
                                        <div style={{ marginTop: '10px', padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', borderLeft: `3px solid ${scoreObj.score >= 60 ? '#4ade80' : '#94a3b8'}` }}>
                                            <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: scoreObj.score >= 90 ? '#22c55e' : scoreObj.score >= 70 ? '#4ade80' : scoreObj.score >= 60 ? '#fbbf24' : '#94a3b8' }}>
                                                {scoreObj.evaluation || '⏳ 관망'}
                                            </div>
                                            <div style={{ marginTop: '4px', fontSize: '0.75rem', color: '#94a3b8', lineHeight: '1.3' }}>
                                                "{comment}"
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>

                        {/* [NEW] System Trading Performance Report (Virtual) */}
                        <div style={{ background: 'rgba(16, 185, 129, 0.05)', padding: '15px', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.2)', marginTop: '20px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', borderBottom: '1px dashed rgba(16, 185, 129, 0.3)', paddingBottom: '8px' }}>
                                <h4 style={{ margin: 0, fontSize: '1rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    🤖 System Auto-Trading Log (Virtual)
                                </h4>
                                <div style={{ fontSize: '0.75rem', color: '#6ee7b7' }}>청안 3중 필터 자동매매 시뮬레이션</div>
                            </div>

                            <SystemPerformanceReport trades={regimeDetails?.prime_guide?.trade_history} />
                        </div>

                    </div>

                    {/* Col 2: Recent Cross History (SOXL / SOXS) */}
                    <div style={{ padding: '0', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

                        {['SOXL', 'SOXS'].map(ticker => {
                            // Extract History from regime details
                            const tickData = ticker === 'SOXL' ? regimeDetails?.soxl : regimeDetails?.soxs;
                            const history = tickData?.cross_history || { gold_30m: [], gold_5m: [] };
                            const mainColor = ticker === 'SOXL' ? '#06b6d4' : '#a855f7';
                            const title = ticker === 'SOXL' ? 'SOXL (BULL)' : 'SOXS (BEAR)';

                            return (
                                <div key={ticker} style={{ background: 'rgba(0,0,0,0.25)', padding: '1.2rem', borderRadius: '16px', border: `1px solid ${mainColor}33` }}>
                                    <h4 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: mainColor, display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '8px' }}>
                                        <span style={{ fontSize: '1.2rem' }}>{ticker === 'SOXL' ? '🚀' : '🛡️'}</span> {title} Signal History
                                    </h4>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>

                                        {/* Auto Trade History List */}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                            {
                                                (() => {
                                                    const signals = [
                                                        ...(history?.gold_30m || []),
                                                        ...(history?.gold_5m || []),
                                                        ...(history?.dead_5m || [])
                                                    ];

                                                    if (signals.length === 0) {
                                                        return (
                                                            <div style={{ padding: '20px', textAlign: 'center', color: '#666', fontSize: '0.8rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                                                                Waiting for signals...
                                                            </div>
                                                        );
                                                    }

                                                    return signals.map((sig, idx) => {
                                                        const isGold = sig.type && sig.type.includes('골든');
                                                        return (
                                                            <div key={idx} style={{
                                                                background: 'rgba(255,255,255,0.03)',
                                                                padding: '10px',
                                                                borderRadius: '8px',
                                                                borderLeft: isGold ? `3px solid ${mainColor}` : '3px solid #777',
                                                                display: 'flex',
                                                                justifyContent: 'space-between',
                                                                alignItems: 'center'
                                                            }}>
                                                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                                                    <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: isGold ? mainColor : '#ccc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                                        {isGold ? '⚡ SIGNAL' : '💤 EXIT'} <span style={{ fontSize: '0.8rem', color: '#888' }}>| {sig.type}</span>
                                                                    </div>
                                                                    <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '3px' }}>
                                                                        {sig.time_ny} (NY) <span style={{ margin: '0 4px' }}>@</span> <b style={{ color: '#fff' }}>${sig.price}</b>
                                                                    </div>
                                                                </div>
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
                </div>

                <style>{`
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.05); opacity: 0.9; }
                    100% { transform: scale(1); opacity: 1; }
                }
                @keyframes flash {
                    0% { opacity: 1; }
                    50% { opacity: 0.3; }
                    100% { opacity: 1; }
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

export default MarketInsight;
