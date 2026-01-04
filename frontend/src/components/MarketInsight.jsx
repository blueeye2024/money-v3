import React from 'react';

const MarketInsight = ({ market, stocks, signalHistory }) => {
    // Safety
    if (!market || !market.market_regime) {
        return <div style={{ padding: '20px', color: '#ccc', textAlign: 'center' }}>데이터를 분석중입니다...</div>;
    }

    const { market_regime } = market;
    const details = market_regime.details || {};
    const prime = details.prime_guide || {};

    const soxlScore = prime.soxl_score?.score || 0;
    const soxsScore = prime.soxs_score?.score || 0;

    return (
        <div style={{
            padding: '24px',
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(12px)',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#f8fafc',
            marginBottom: '32px'
        }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.2rem', color: '#38bdf8' }}>🚀 청안 Prime Guide (안전 모드)</h3>

            {/* Guide Text */}
            <div style={{
                padding: '16px',
                background: 'rgba(0, 0, 0, 0.3)',
                borderRadius: '12px',
                marginBottom: '20px',
                borderLeft: '4px solid #38bdf8'
            }}>
                <div style={{ fontSize: '0.95rem', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                    {prime.main_guide || details.risk_plan || "시장 데이터를 불러오는 중입니다..."}
                </div>
            </div>

            {/* Scores (Simple Bars) */}
            <div style={{ display: 'flex', gap: '20px', marginBottom: '24px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px', padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 'bold', color: '#06b6d4' }}>SOXL 매수 준비</span>
                        <span style={{ fontWeight: 'bold' }}>{soxlScore}%</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: '#333', borderRadius: '4px' }}>
                        <div style={{ width: `${soxlScore}%`, height: '100%', background: '#06b6d4', borderRadius: '4px' }} />
                    </div>
                </div>
                <div style={{ flex: 1, minWidth: '200px', padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 'bold', color: '#a855f7' }}>SOXS 매수 준비</span>
                        <span style={{ fontWeight: 'bold' }}>{soxsScore}%</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', background: '#333', borderRadius: '4px' }}>
                        <div style={{ width: `${soxsScore}%`, height: '100%', background: '#a855f7', borderRadius: '4px' }} />
                    </div>
                </div>
            </div>

            {/* News (Safe List) */}
            <div>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#94a3b8' }}>실시간 뉴스 피드</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {prime.news && Array.isArray(prime.news) && prime.news.length > 0 ? (
                        prime.news.map((n, i) => (
                            <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                                <div style={{
                                    padding: '12px',
                                    background: 'rgba(255,255,255,0.02)',
                                    borderRadius: '8px',
                                    border: '1px solid rgba(255,255,255,0.05)',
                                    color: '#e2e8f0'
                                }}>
                                    <div style={{ fontSize: '0.9rem', marginBottom: '4px' }}>{n.title}</div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                        {n.publisher} • {n.time}
                                    </div>
                                </div>
                            </a>
                        ))
                    ) : (
                        <div style={{ padding: '10px', color: '#666', fontSize: '0.85rem' }}>뉴스 데이터가 없습니다.</div>
                    )}
                </div>
            </div>

            {/* Footer Info */}
            <div style={{ marginTop: '20px', textAlign: 'right', fontSize: '0.75rem', color: '#555' }}>
                Engine V2.1 Safe Mode Active
            </div>
        </div>
    );
};

export default MarketInsight;
