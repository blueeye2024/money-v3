import React from 'react';
import { Newspaper, TrendingUp, AlertTriangle, Zap, Activity, Radio, Info } from 'lucide-react';

// --- Sub Components ---

const ScoreGauge = ({ ticker, data, isBull }) => {
    const score = data?.score || 0;
    const isRisk = data?.is_risk;

    // Color Palette
    // Bull(Cyan), Bear(Purple), Risk(Red)
    const baseColor = isRisk ? '#ef4444' : (isBull ? '#06b6d4' : '#a855f7');

    // Gradient styles
    const bgGradient = isRisk
        ? 'linear-gradient(90deg, #b91c1c, #ef4444)'
        : (isBull ? 'linear-gradient(90deg, #0e7490, #22d3ee)' : 'linear-gradient(90deg, #7e22ce, #c084fc)');

    return (
        <div style={{
            flex: 1,
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '16px',
            padding: '1.25rem',
            border: `1px solid ${baseColor}33`,
            position: 'relative',
            overflow: 'hidden',
            minWidth: '280px'
        }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.4rem', fontWeight: '900', color: baseColor, letterSpacing: '1px' }}>{ticker}</span>
                    <span style={{
                        fontSize: '0.7rem', padding: '3px 8px', borderRadius: '12px',
                        background: `${baseColor}22`, color: baseColor, fontWeight: 'bold',
                        border: `1px solid ${baseColor}44`
                    }}>
                        {isRisk ? 'RISK ALERT' : 'READY STATUS'}
                    </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                    <span style={{ fontSize: '1.8rem', fontWeight: '900', color: '#fff', textShadow: `0 0 15px ${baseColor}66` }}>
                        {score}
                    </span>
                    <span style={{ fontSize: '0.9rem', color: baseColor, fontWeight: '600' }}>%</span>
                </div>
            </div>

            {/* Progress Bar Container */}
            <div style={{ width: '100%', height: '14px', background: 'rgba(0,0,0,0.3)', borderRadius: '7px', overflow: 'hidden', marginBottom: '1.2rem', padding: '2px' }}>
                <div style={{
                    width: `${score}%`,
                    height: '100%',
                    background: bgGradient,
                    borderRadius: '5px',
                    transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: `0 0 20px ${baseColor}55`
                }} />
            </div>

            {/* Logic Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {data?.details?.length > 0 ? (
                    data.details.map((det, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#d1d5db' }}>
                            <Zap size={14} color={baseColor} fill={baseColor} />
                            <span>{det}</span>
                        </div>
                    ))
                ) : (
                    <div style={{ fontSize: '0.85rem', color: '#555', paddingLeft: '4px' }}>신호 대기 중...</div>
                )}
            </div>

            {/* Background Decor */}
            <div style={{ position: 'absolute', top: '-20%', right: '-10%', width: '120px', height: '120px', background: baseColor, filter: 'blur(80px)', opacity: 0.15, pointerEvents: 'none' }} />
        </div>
    );
};

const NewsItem = ({ news }) => (
    <a href={news.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', display: 'block' }}>
        <div style={{
            padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px',
            border: '1px solid rgba(255,255,255,0.05)', transition: 'all 0.2s',
            display: 'flex', flexDirection: 'column', gap: '4px'
        }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
        >
            <div style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: '500', lineHeight: '1.4' }}>
                {news.title}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b' }}>
                <span>{news.publisher}</span>
                <span>{news.time}</span>
            </div>
        </div>
    </a>
);

// MAIN COMPONENT
const MarketInsight = ({ market, stocks, signalHistory }) => {
    if (!market) return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>데이터 분석 중...</div>;

    const { market_regime } = market;
    const details = market_regime?.details;
    const prime = details?.prime_guide || {};

    return (
        <div className="glass-panel" style={{ padding: '0', marginBottom: '3rem', overflow: 'hidden' }}>
            {/* Header Section */}
            <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '40px', height: '40px', background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 15px rgba(6,182,212,0.3)' }}>
                        <Activity color="white" size={24} />
                    </div>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc', fontWeight: '800' }}>청안 Prime Guide</h3>
                        <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8' }}>Real-time Analysis & Action Plan</p>
                    </div>
                </div>
                {/* Connection Status */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
                    <span style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: '600' }}>LIVE ENGINE V2.1</span>
                </div>
            </div>

            {/* Content Body */}
            <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>

                {/* 1. Score Gauges (Entry/Exit Probability) */}
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                    <ScoreGauge ticker="SOXL" data={prime.soxl_score} isBull={true} />
                    <ScoreGauge ticker="SOXS" data={prime.soxs_score} isBull={false} />
                </div>

                {/* 2. Main Strategy Guide */}
                <div style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    borderRadius: '16px',
                    padding: '1.5rem',
                    border: '1px solid rgba(6, 182, 212, 0.2)',
                    boxShadow: '0 0 30px rgba(0,0,0,0.2)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem', color: '#22d3ee' }}>
                        <Info size={18} />
                        <span style={{ fontWeight: 'bold', fontSize: '0.95rem', letterSpacing: '0.5px' }}>CURRENT ACTION PLAN</span>
                    </div>
                    <div style={{
                        fontSize: '0.95rem',
                        lineHeight: '1.7',
                        color: '#e2e8f0',
                        whiteSpace: 'pre-wrap',
                        fontFamily: "'Noto Sans KR', sans-serif"
                    }}>
                        {prime.main_guide ? prime.main_guide : (details?.risk_plan || "시장 데이터를 분석하고 있습니다...")}
                    </div>
                </div>

                {/* 3. News & Volatility Row */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>

                    {/* Recent News */}
                    <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '16px', padding: '1.25rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem', color: '#94a3b8' }}>
                            <Newspaper size={16} />
                            <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>MARKET NEWS (Real-time)</span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {prime.news && prime.news.length > 0 ? (
                                prime.news.map((n, i) => <NewsItem key={i} news={n} />)
                            ) : (
                                <div style={{ fontSize: '0.8rem', color: '#555', padding: '1rem', textAlign: 'center' }}>뉴스 데이터 수신 중...</div>
                            )}
                        </div>
                    </div>

                    {/* Volatility & History */}
                    <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '16px', padding: '1.25rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem', color: '#94a3b8' }}>
                            <AlertTriangle size={16} />
                            <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>AI INSIGHTS</span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                                <div style={{ fontSize: '0.75rem', color: '#aaa', marginBottom: '4px' }}>예상 변동성 (ATR)</div>
                                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#f43f5e' }}>
                                    {prime.atr_volatility || "High (Calculating...)"}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>
                                    변동성이 높은 구간입니다. 짧은 단타(Scalping)가 유리합니다.
                                </div>
                            </div>
                            <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                                <div style={{ fontSize: '0.75rem', color: '#aaa', marginBottom: '4px' }}>Time Regime</div>
                                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#fbbf24' }}>
                                    Intraday Active
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>
                                    가장 거래가 활발한 시간대입니다. 신호 신뢰도가 높습니다.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            {/* Footer Status Bar */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem 2rem', display: 'flex', justifyContent: 'flex-end', fontSize: '0.7rem', color: '#555' }}>
                Last Updated: {market?.timestamp || '-'}
            </div>
        </div>
    );
};

export default MarketInsight;
