import React from 'react';
import V2SignalStatus from './V2SignalStatus';



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

const MarketInsight = ({ market, stocks, signalHistory, onRefresh }) => {
    if (!market) return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>데이터 로딩 중...</div>;

    const { market_regime } = market;
    const regimeDetails = market_regime?.details;

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
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>

            {/* 1. MASTER CONTROL TOWER (V2.3) */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ width: '48px', height: '48px', background: 'rgba(212, 175, 55, 0.1)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem' }}>🛰️</div>
                        <h3 style={{ margin: 0, fontSize: '1.4rem', color: 'var(--accent-gold)', letterSpacing: '1px', fontWeight: '900' }}>MASTER CONTROL TOWER</h3>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{
                            background: market_regime?.regime?.includes('Bull') ? 'rgba(74, 222, 128, 0.1)' : market_regime?.regime?.includes('Bear') ? 'rgba(248, 113, 113, 0.1)' : 'rgba(255,255,255,0.05)',
                            padding: '0.5rem 1rem', borderRadius: '10px', border: `1px solid ${market_regime?.regime?.includes('Bull') ? '#4ade8055' : market_regime?.regime?.includes('Bear') ? '#f8717155' : '#ffffff22'}`,
                        }}>
                            <span style={{ color: market_regime?.regime?.includes('Bull') ? '#4ade80' : market_regime?.regime?.includes('Bear') ? '#f87171' : '#ccc', fontWeight: '900', fontSize: '1.1rem' }}>
                                {regimeDetails?.reason || market_regime?.regime}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Insight Comment Box */}
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1.2rem', borderRadius: '16px', marginBottom: '2rem', borderLeft: '5px solid var(--accent-gold)' }}>
                    <p style={{ margin: 0, color: '#bbb', fontSize: '0.95rem', lineHeight: '1.6', fontWeight: '500' }}>
                        {regimeDetails?.comment || "시장 상황을 실시간 분석 중입니다."}
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
                    <V2SignalStatus
                        title="SOXL (BULL TOWER)"
                        buyStatus={regimeDetails?.soxl?.v2_buy}
                        sellStatus={regimeDetails?.soxl?.v2_sell}
                        renderInfo={regimeDetails?.soxl}
                        isBear={false}
                        onRefresh={onRefresh}
                    />
                    <V2SignalStatus
                        title="SOXS (BEAR TOWER)"
                        buyStatus={regimeDetails?.soxs?.v2_buy}
                        sellStatus={regimeDetails?.soxs?.v2_sell}
                        renderInfo={regimeDetails?.soxs}
                        isBear={true}
                        onRefresh={onRefresh}
                    />
                </div>

                {/* 2. Prime Guide : Action Plan (V3.5 Comprehensive Score) */}
                <div style={{ background: 'rgba(15, 23, 42, 0.9)', padding: '1.5rem', borderRadius: '20px', border: '1px solid rgba(56, 189, 248, 0.5)', boxShadow: '0 0 30px rgba(56, 189, 248, 0.1)', marginBottom: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ width: '12px', height: '12px', background: '#38bdf8', borderRadius: '50%', boxShadow: '0 0 15px #38bdf8' }} />
                            <h3 style={{ margin: 0, fontSize: '1.4rem', color: '#38bdf8', fontWeight: '900', letterSpacing: '-0.5px' }}>청안 Prime Guide : Action Plan</h3>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', background: '#0f172a', padding: '4px 10px', borderRadius: '20px' }}>V3.5 Holding Score</div>
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

                                    {/* Score Breakdown Bar (V3.5) */}
                                    <div style={{ marginBottom: '15px' }}>
                                        <div style={{ width: '100%', height: '8px', background: '#334155', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                                            <div style={{ width: `${(scoreObj.breakdown?.cheongan || 0)}%`, background: color, opacity: 1 }} title="청안 프라임 지수" />
                                            <div style={{ width: `${(scoreObj.breakdown?.tech || 0)}%`, background: color, opacity: 0.6 }} title="기술적 지표" />
                                            {/* Penalty visualization (Red bar at end if exists, conceptually) */}
                                            {(scoreObj.breakdown?.penalty || 0) > 0 && <div style={{ width: `${scoreObj.breakdown.penalty}%`, background: '#ef4444' }} title="감점 요인" />}
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8', marginTop: '4px' }}>
                                            <span>청안지수({scoreObj.breakdown?.cheongan || 0}/60)</span>
                                            <span>Tech({scoreObj.breakdown?.tech || 0}/40)</span>
                                            <span style={{ color: (scoreObj.breakdown?.penalty || 0) > 0 ? '#ef4444' : '#94a3b8' }}>감점(-{scoreObj.breakdown?.penalty || 0})</span>
                                        </div>
                                    </div>

                                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.7', fontSize: '0.92rem', color: isSoxl ? '#cffafe' : '#f3e8ff', fontFamily: "'Noto Sans KR', sans-serif" }}>
                                        {guideText}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* 3. Bottom Grid: Intelligence & History */}
                <div className="responsive-grid-2-1">

                    {/* Col 1: Market Intelligence Center (Detailed) */}
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '16px' }}>
                        <h4 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px' }}>
                            🌐 Market Intelligence Center (심층 분석)
                        </h4>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                            {['UPRO', 'SOXL', 'SOXS'].map(ticker => {
                                const guideData = regimeDetails?.prime_guide || {};
                                const scoreObj = guideData.scores?.[ticker] || { score: 0, breakdown: {} };
                                const tech = guideData.tech_summary?.[ticker] || {};
                                const comment = guideData.tech_comments?.[ticker] || "-";

                                const color = ticker === 'SOXL' ? '#06b6d4' : ticker === 'SOXS' ? '#a855f7' : '#f59e0b';

                                return (
                                    <div key={ticker} style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '12px', border: `1px solid ${color}22` }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                            <span style={{ fontWeight: 'bold', color: color, fontSize: '1rem' }}>{ticker}</span>
                                            <span style={{ fontWeight: 'bold', color: 'white', fontSize: '1.1rem' }}>{scoreObj.score} <span style={{ fontSize: '0.7rem', color: '#888' }}>점</span></span>
                                        </div>

                                        {/* Evaluation Summary */}
                                        <div style={{ fontSize: '0.8rem', color: '#e2e8f0', background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '6px', marginBottom: '12px', textAlign: 'center', fontWeight: 'bold' }}>
                                            {scoreObj.evaluation || "-"}
                                        </div>

                                        {/* Tech Summary (2 decimals) */}
                                        <div style={{ fontSize: '0.8rem', color: '#aaa' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>RSI(14)</span> <span style={{ color: 'white' }}>{Number(tech.rsi || 0).toFixed(2)}</span></div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>MACD</span> <span style={{ color: 'white' }}>{Number(tech.macd || 0).toFixed(2)}</span></div>
                                            <div style={{ marginTop: '6px', fontSize: '0.75rem', color: color, lineHeight: '1.3', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '4px' }}>
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
