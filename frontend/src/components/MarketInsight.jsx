import React from 'react';

const MarketInsight = ({ market }) => {
    // market prop here is actually the whole 'data' object passed from App.jsx? 
    // Let's verify App.jsx usage.
    // App.jsx: <MarketInsight market={data} /> 
    // So `market` prop is `data`.
    // data.insight is now a STRING (Actionable Guidelines).
    // data.market_regime is the regime info.

    const { insight, market_regime } = market;
    const guidelines = insight || "";

    // Parse the markdown-like string for display?
    // It has \n\n separators.
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

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1.2rem', position: 'relative', zIndex: 1 }}>
                <span style={{ fontSize: '1.5rem' }}>🧭</span>
                <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Cheongan Trade Guidelines (현재 거래 지침)</h2>
            </div>

            <div className="market-insight-grid" style={{ position: 'relative', zIndex: 1, display: 'block' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    {sections.map((sec, idx) => (
                        <p key={idx} style={{
                            lineHeight: 1.8,
                            color: '#e2e8f0',
                            fontSize: '1rem',
                            marginBottom: '1rem',
                            whiteSpace: 'pre-line'
                        }}>
                            {/* Simple Bold parsing */}
                            {sec.split('**').map((part, i) =>
                                i % 2 === 1 ? <strong key={i} style={{ color: 'var(--accent-gold)' }}>{part}</strong> : part
                            )}
                        </p>
                    ))}
                </div>
            </div>
            <style>{`
                .market-insight-grid {
                    display: block;
                }
            `}</style>
        </div>
    );
};

export default MarketInsight;
