import React from 'react';

const TripleFilterStatus = ({ title, status, isBear = false }) => {
    const conditions = [
        { key: 'step1', label: '타이밍 조건', desc: status?.step_details?.step1 || '5분봉 이평' },
        { key: 'step2', label: '추세 조건', desc: status?.step_details?.step2 || '30분봉 이평' },
        { key: 'step3', label: '강도 조건', desc: status?.step_details?.step3 || '+2% 돌파' }
    ];

    const activeColor = isBear ? '#3b82f6' : '#ef4444';
    const finalColor = isBear ? '#2563eb' : '#dc2626';

    const conditionsMet = [status?.step1, status?.step2, status?.step3].filter(Boolean).length;

    return (
        <div style={{ flex: 1, minWidth: '320px', background: 'rgba(0,0,0,0.4)', padding: '1.5rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                    <h4 style={{ margin: 0, fontSize: '1.1rem', color: status?.final ? (isBear ? '#60a5fa' : '#ef4444') : (isBear ? '#93c5fd' : '#fca5a5'), fontWeight: '800' }}>{title}</h4>
                    <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>
                        {status?.final ? `모든 조건 완성 (${status.signal_time})` : `${conditionsMet} / 3 조건 완료`}
                    </div>
                </div>
                {status?.final ? (
                    <div style={{ textAlign: 'right' }}>
                        <span style={{
                            padding: '0.4rem 1rem', background: finalColor, color: 'white', borderRadius: '30px', fontSize: '0.75rem', fontWeight: 'bold',
                            animation: 'pulse 1.5s infinite', boxShadow: `0 0 20px ${finalColor}66`, display: 'inline-block'
                        }}>
                            진입 조건 완성
                        </span>
                    </div>
                ) : (
                    <div style={{ fontSize: '0.7rem', color: '#888', background: 'rgba(255,255,255,0.05)', padding: '4px 10px', borderRadius: '20px' }}>
                        조건 대기 중...
                    </div>
                )}
            </div>

            {/* Horizontal Condition Bar */}
            <div style={{ position: 'relative', height: '60px', marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 10px' }}>
                <div style={{ position: 'absolute', top: '50%', left: '10%', right: '10%', height: '4px', background: 'rgba(255,255,255,0.1)', transform: 'translateY(-50%)', zIndex: 1, borderRadius: '2px' }} />

                {conditions.map((cond, idx) => {
                    const isMet = status ? status[cond.key] : false;
                    const backendColor = status ? status[`${cond.key}_color`] : null;

                    let dotColor = '#1a1a1a';
                    let shadow = 'none';

                    if (backendColor === 'red') {
                        dotColor = '#ef4444';
                        shadow = '0 0 15px #ef4444';
                    } else if (backendColor === 'orange') {
                        dotColor = '#f97316';
                        shadow = '0 0 15px #f97316';
                    } else if (backendColor === 'yellow') {
                        dotColor = '#eab308';
                        shadow = '0 0 15px #eab308';
                    } else if (isMet) {
                        dotColor = activeColor;
                        shadow = `0 0 15px ${activeColor}`;
                    }

                    return (
                        <div key={cond.key} style={{ zIndex: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', position: 'relative' }}>
                            <div style={{
                                width: '32px', height: '32px', borderRadius: '50%',
                                background: dotColor,
                                border: `3px solid ${isMet || backendColor ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.05)'}`,
                                boxShadow: shadow,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: (isMet || backendColor) ? 'white' : '#444', fontWeight: 'bold', fontSize: '1.2rem',
                                transition: 'all 0.5s ease'
                            }}>
                                {isMet ? '✓' : idx + 1}
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: '700', color: isMet ? '#fff' : '#555' }}>{cond.label}</div>
                                <div style={{ fontSize: '0.65rem', color: isMet ? '#aaa' : '#444' }}>{cond.desc}</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Recent Signal Info */}
            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {status?.warning_5m && (
                    <div style={{
                        background: 'rgba(234, 179, 8, 0.1)', color: '#eab308', padding: '8px 12px', borderRadius: '8px',
                        fontSize: '0.75rem', fontWeight: 'bold', border: '1px solid rgba(234, 179, 8, 0.3)',
                        animation: 'pulse 1s infinite'
                    }}>
                        ⚠️ 주의: 5분봉 데드크로스 발생 (단기 조정 가능성)
                    </div>
                )}

                {/* Detailed Logs for Each Step */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '4px 0' }}>
                    {conditions.map(c => (
                        status?.step_details?.[c.key] && status?.step_details[c.key] !== '대기 중' && (
                            <div key={c.key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#888' }}>
                                <span>• {c.label}</span>
                                <span style={{ color: '#aaa', fontWeight: 'bold' }}>{status.step_details[c.key]}</span>
                            </div>
                        )
                    ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px dashed rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#555' }}>
                        {status?.signal_time ? `신호 완성: ${status.signal_time}` : `체크: ${status?.timestamp ? String(status.timestamp).split(' ')[1] : '-'}`}
                    </div>
                    {status?.target > 0 && (
                        <div style={{ fontSize: '0.7rem', color: '#555' }}>
                            2% 목표: <span style={{ color: status?.step3 ? activeColor : '#555', fontWeight: 'bold' }}>${status.target}</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const MarketInsight = ({ market, stocks, signalHistory }) => {
    if (!market) return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>데이터 로딩 중...</div>;

    const { market_regime } = market;
    const regimeDetails = market_regime?.details;

    const activeStocks = stocks && Array.isArray(stocks)
        ? [...stocks].sort((a, b) => (b.current_ratio || 0) - (a.current_ratio || 0))
        : [];

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
                    <TripleFilterStatus title="SOXL (BULL TOWER)" status={regimeDetails?.soxl} isBear={false} />
                    <TripleFilterStatus title="SOXS (BEAR TOWER)" status={regimeDetails?.soxs} isBear={true} />
                </div>

                {/* Detailed Strategy Guide */}
                <div style={{ background: 'linear-gradient(145deg, rgba(30,41,59,0.5), rgba(15,23,42,0.6))', padding: '1.5rem', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1.5rem' }}>
                        <div style={{ width: '36px', height: '36px', background: 'rgba(96, 165, 250, 0.2)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>📋</div>
                        <h4 style={{ margin: 0, fontSize: '1.2rem', color: '#60a5fa', fontWeight: '800' }}>종합 매매 실천 계획 & 상세 전략 가이드</h4>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.2rem', borderRadius: '16px' }}>
                            <div style={{ color: 'var(--accent-gold)', fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <div style={{ width: '6px', height: '6px', background: 'var(--accent-gold)', borderRadius: '50%' }} /> HISTORY (신호 발생 기록)
                            </div>
                            <div style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.7', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {signalHistory && Array.isArray(signalHistory) && signalHistory.length > 0 ? (
                                    signalHistory.map(sig => (
                                        <div key={sig.id} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '4px' }}>
                                            <span style={{ color: '#bbb' }}>{sig.created_at && sig.created_at.includes(' ') ? sig.created_at.split(' ')[1].substring(0, 5) : (sig.created_at || '-')}</span>
                                            <span style={{ color: (sig.signal_type || '').includes('BUY') ? '#ef4444' : '#3b82f6', fontWeight: 'bold' }}>{sig.ticker || '-'} {(sig.signal_type || '').replace(' (MASTER)', '')}</span>
                                            <span style={{ color: '#aaa' }}>${sig.price}</span>
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ color: '#666' }}>최근 발생한 신호가 없습니다.</div>
                                )}
                            </div>
                        </div>

                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.2rem', borderRadius: '16px' }}>
                            <div style={{ color: '#4ade80', fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <div style={{ width: '6px', height: '6px', background: '#4ade80', borderRadius: '50%' }} /> 리스크 관리 & 운영 전술
                            </div>
                            <div style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: '1.6' }}>
                                {regimeDetails?.risk_plan || "-"}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. Asset Sync Section */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '2.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
                    <div style={{ width: '40px', height: '40px', background: 'rgba(96, 165, 250, 0.1)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem' }}>🧠</div>
                    <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#60a5fa', fontWeight: '800' }}>ASSET SYNC & INDIVIDUAL STRATEGY</h3>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' }}>
                    {activeStocks.filter(stock => stock && typeof stock === 'object').map(stock => {
                        const position = String(stock.position || '');
                        const isSync = position.includes('Master Sync') || position.includes('🔴') || position.includes('🔹');
                        const isBuy = position.includes('매수');
                        const isSell = position.includes('매도');

                        return (
                            <div key={stock.ticker} style={{
                                background: isSync ? 'linear-gradient(135deg, rgba(96, 165, 250, 0.08), rgba(0,0,0,0.3))' : 'rgba(255,255,255,0.03)',
                                padding: '1.5rem',
                                borderRadius: '18px',
                                border: isSync ? `1px solid ${isBuy ? '#ff6b6b44' : isSell ? '#60a5fa44' : '#60a5fa22'}` : '1px solid rgba(255,255,255,0.05)',
                                position: 'relative',
                                transition: 'all 0.3s ease',
                                boxShadow: isSync ? '0 8px 25px rgba(0,0,0,0.2)' : 'none'
                            }}>
                                {isSync && (
                                    <div style={{ position: 'absolute', top: '15px', right: '15px', display: 'flex', gap: '5px' }}>
                                        <div style={{ background: isBuy ? '#ef4444' : isSell ? '#3b82f6' : '#888', width: '8px', height: '8px', borderRadius: '50%', animation: 'flash 1s infinite' }} />
                                    </div>
                                )}
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.2rem', alignItems: 'flex-start' }}>
                                    <div>
                                        <div style={{ fontWeight: '900', fontSize: '1.2rem', color: '#fff' }}>{stock.ticker}</div>
                                        <div style={{
                                            fontSize: '0.95rem', fontWeight: '800',
                                            color: isBuy ? '#ff6b6b' : isSell ? '#4dabf7' : '#888',
                                            marginTop: '8px'
                                        }}>
                                            {stock.position || '-'}
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ color: '#4ade80', fontWeight: '900', fontSize: '1.4rem' }}>
                                            {stock.current_ratio && !isNaN(parseFloat(String(stock.current_ratio))) ? parseFloat(String(stock.current_ratio)).toFixed(1) : '0.0'}%
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>
                                            TARGET: {stock.target_ratio}%
                                        </div>
                                    </div>
                                </div>
                                <div style={{
                                    fontSize: '0.85rem', color: '#9ca3af', lineHeight: '1.6',
                                    background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px',
                                    minHeight: '4.5rem', display: 'flex', alignItems: 'center'
                                }}>
                                    {stock.strategy_text || "Syncing..."}
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
            `}</style>
        </div>
    );
};

export default MarketInsight;
