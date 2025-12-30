import React from 'react';

const MarketInsight = ({ market }) => {
    const { insight } = market;
    const { prediction, prediction_desc, news } = insight || {};

    let predColor = 'var(--text-primary)';
    if (prediction?.includes('상승')) predColor = 'var(--accent-red)';
    if (prediction?.includes('하락')) predColor = 'var(--accent-blue)';

    return (
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', position: 'relative', overflow: 'hidden' }}>
            {/* Background Accent */}
            <div style={{
                position: 'absolute', top: -50, right: -50, width: '200px', height: '200px',
                background: prediction?.includes('상승') ? 'radial-gradient(circle, rgba(239,68,68,0.2) 0%, transparent 70%)' :
                    prediction?.includes('하락') ? 'radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%)' :
                        'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)',
                zIndex: 0
            }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1.2rem', position: 'relative', zIndex: 1 }}>
                <span style={{ fontSize: '1.5rem' }}>🧠</span>
                <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Cheongan Market Insight</h2>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', position: 'relative', zIndex: 1 }}>

                {/* Left: Market Prediction */}
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <h3 style={{ margin: '0 0 1rem 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>📈 AI Market Prediction (S&P 500)</h3>
                    <div style={{ fontSize: '1.8rem', fontWeight: 800, color: predColor, marginBottom: '0.5rem' }}>
                        {prediction || 'Analyzing...'}
                    </div>
                    <p style={{ lineHeight: 1.6, color: '#e2e8f0', margin: 0, fontSize: '0.95rem' }}>
                        {prediction_desc || '현재 시장 데이터를 분석 중입니다.'}
                    </p>
                </div>

                {/* Right: Key News */}
                <div>
                    <h3 style={{ margin: '0 0 1rem 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>📰 주요 뉴스 요약</h3>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {news && news.length > 0 ? (
                            news.map((item, idx) => (
                                <li key={idx} style={{
                                    paddingLeft: '0.8rem', borderLeft: '2px solid var(--accent-gold)',
                                    display: 'flex', flexDirection: 'column', gap: '0.3rem'
                                }}>
                                    <div style={{ color: 'var(--text-primary)', fontWeight: '600', fontSize: '0.9rem' }}>
                                        {item.title}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                        {item.source} • {item.date}
                                    </div>
                                </li>
                            ))
                        ) : (
                            <li style={{ color: 'var(--text-secondary)' }}>주요 뉴스를 불러오는 중입니다...</li>
                        )}
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default MarketInsight;
