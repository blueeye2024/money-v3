import React from 'react';

const MarketInsight = ({ market }) => {
    // market prop here is actually the whole 'data' object passed from App.jsx? 
    // Let's verify App.jsx usage.
    // App.jsx: <MarketInsight market={data} /> 
    // So `market` prop is `data`.
    // data.insight is now a STRING (Actionable Guidelines).
    // data.market_regime is the regime info.

    const { insight, market_regime, strategy_list } = market;
    const guidelines = insight || "";

    const sections = guidelines.split('\n\n');

    return (
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', position: 'relative', overflow: 'hidden' }}>
            {/* Background Accent */}
            <div style={{
                position: 'absolute', top: -50, right: -50, width: '200px', height: '200px',
                background: market_regime?.regime === 'Bull' ? 'radial-gradient(circle, rgba(239,68,68,0.2) 0%, transparent 70%)' :
                    market_regime?.regime === 'Bear' ? 'radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%)' :
                        'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)',
                zIndex: 0
            }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1.5rem', position: 'relative', zIndex: 1 }}>
                <span style={{ fontSize: '1.5rem' }}>🧭</span>
                <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Cheongan Trade Guidelines (현재 거래 지침)</h2>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '2rem', position: 'relative', zIndex: 1, alignItems: 'start' }}>

                {/* LEFT: Strategic Portfolio List */}
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--accent-gold)' }}>🎯 전략 모델 (Target)</h3>
                        <span style={{ fontSize: '0.8rem', color: '#888' }}>총 자산 연동</span>
                    </div>

                    {strategy_list ? strategy_list.map((item, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: item.ticker === 'CASH' ? '#10b981' : '#60a5fa' }}></div>
                                <span style={{ fontWeight: 'bold', color: '#fff' }}>{item.ticker}</span>
                                <span style={{ fontSize: '0.8rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', color: '#ccc' }}>{item.weight}%</span>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ color: item.ticker === 'CASH' ? '#10b981' : '#fff', fontWeight: 'bold', fontSize: '0.95rem' }}>
                                    {item.ticker === 'CASH' ? `$${item.req_qty?.toLocaleString()}` : `${item.req_qty} 주`}
                                </div>
                                {item.ticker !== 'CASH' && (
                                    <div style={{ fontSize: '0.75rem', color: '#666' }}>@ ${item.price?.toFixed(2)}</div>
                                )}
                            </div>
                        </div>
                    )) : (
                        <div style={{ color: '#888', fontStyle: 'italic' }}>전략 데이터 로딩 중...</div>
                    )}
                </div>

                {/* RIGHT: Action Plan Text */}
                <div className="market-insight-grid">
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        {sections.map((sec, idx) => (
                            <p key={idx} style={{
                                lineHeight: 1.7,
                                color: '#e2e8f0',
                                fontSize: '0.95rem',
                                marginBottom: '1rem',
                                whiteSpace: 'pre-line'
                            }}>
                                {sec.split('**').map((part, i) =>
                                    i % 2 === 1 ? <strong key={i} style={{ color: 'var(--accent-gold)' }}>{part}</strong> : part
                                )}
                            </p>
                        ))}
                    </div>
                </div>
            </div>

            <style>{`
                .market-insight-grid {
                    display: block;
                }
                @media (max-width: 768px) {
                    div[style*="grid-template-columns"] {
                        grid-template-columns: 1fr !important;
                    }
                }
            `}</style>
        </div>
    );
};

export default MarketInsight;
