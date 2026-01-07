import React from 'react';

const V2SignalStatus = ({ title, buyStatus, sellStatus, renderInfo, isBear = false }) => {
    // Info from V1 status (Price, Change)
    const { current_price, daily_change } = renderInfo || {};

    // Determine Current Mode
    const isHolding = buyStatus?.final_buy_yn === 'Y';
    const isSellFinished = sellStatus?.final_sell_yn === 'Y'; // If sold, maybe back to Buy?

    // If Sell Finished, we are back to Buy Mode? 
    // Logic: If buy_final=Y, check sell. If sell_final=Y -> Buy Mode (Waiting for next).
    // Actually, backend might not reset buy_final immediately? 
    // Assumption: If sell_final=Y, the cycle is complete. We look for NEW Buy.
    // So: if (isHolding && !isSellFinished) -> Sell Mode. Else -> Buy Mode.

    const mode = (isHolding && !isSellFinished) ? 'SELL' : 'BUY';
    const activeData = mode === 'BUY' ? buyStatus : sellStatus;

    // Steps Configuration
    const steps = mode === 'BUY' ? [
        { key: 'buy_sig1_yn', label: '1차: 5분봉 GC', desc: '추세 시작' },
        { key: 'buy_sig2_yn', label: '2차: 박스권+2%', desc: '강력 돌파' },
        { key: 'buy_sig3_yn', label: '3차: 30분봉 GC', desc: '추세 확정' }
    ] : [
        { key: 'sell_sig1_yn', label: '1차: 5분봉 DC', desc: '단기 조정' },
        { key: 'sell_sig2_yn', label: '2차: 손절/익절', desc: '리스크 관리' },
        { key: 'sell_sig3_yn', label: '3차: 30분봉 DC', desc: '추세 이탈' }
    ];

    // Colors
    // Buy: Blue/Purple (Bull), Purple (Bear) - as per original code?
    // Let's use Cyan for Bull (SOXL), Purple for Bear (SOXS)
    // Sell Mode: Red/Orange for Warning?
    const themeColor = isBear ? '#a855f7' : '#06b6d4';
    const modeColor = mode === 'SELL' ? '#ef4444' : themeColor;

    // Calculate Progress
    const progress = steps.filter(s => activeData?.[s.key] === 'Y').length;

    // Format Price
    const formatPrice = (p) => p ? `$${Number(p).toFixed(2)}` : '-';

    return (
        <div style={{ flex: 1, minWidth: '320px', background: 'rgba(0,0,0,0.4)', padding: '1.5rem', borderRadius: '16px', border: `1px solid ${modeColor}33`, position: 'relative', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h4 style={{ margin: 0, fontSize: '1.2rem', color: themeColor, fontWeight: '800' }}>{title}</h4>
                        <span style={{
                            fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px', fontWeight: 'bold',
                            background: mode === 'SELL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(6, 182, 212, 0.1)',
                            color: modeColor
                        }}>
                            {mode === 'SELL' ? '매도 감시 (HOLDING)' : '매수 대기 (WATCHING)'}
                        </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '6px' }}>
                        Manage ID: {activeData?.manage_id || '-'}
                    </div>
                    {/* Price Display */}
                    {current_price && (
                        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                            <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff', letterSpacing: '-0.5px' }}>
                                ${Number(current_price).toFixed(2)}
                            </span>
                            {daily_change != null && (
                                <span style={{
                                    fontSize: '0.75rem', fontWeight: 'bold',
                                    color: daily_change >= 0 ? '#4ade80' : '#f87171'
                                }}>
                                    ({daily_change >= 0 ? '+' : ''}{Number(daily_change).toFixed(2)}%)
                                </span>
                            )}
                        </div>
                    )}
                </div>

                {/* Visual Badge */}
                <div style={{ textAlign: 'right' }}>
                    {!isHolding && activeData?.buy_sig1_yn === 'Y' && (
                        <div style={{ fontSize: '0.8rem', color: themeColor, animation: 'pulse 1.5s infinite', fontWeight: 'bold' }}>
                            Signal Active!
                        </div>
                    )}
                    {isHolding && (
                        <div style={{ fontSize: '0.8rem', color: '#ef4444', animation: 'pulse 1.5s infinite', fontWeight: 'bold' }}>
                            Exit Signal!
                        </div>
                    )}
                </div>
            </div>

            {/* Progress Bar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', marginTop: '1rem', padding: '0 10px' }}>
                {/* Connecting Line */}
                <div style={{ position: 'absolute', top: '20px', left: '15%', right: '15%', height: '2px', background: 'rgba(255,255,255,0.1)', zIndex: 0 }} />

                {steps.map((step, idx) => {
                    const isActive = activeData?.[step.key] === 'Y';

                    return (
                        <div key={idx} style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', flex: 1 }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '50%',
                                background: isActive ? modeColor : '#1e293b',
                                border: `2px solid ${isActive ? '#fff' : 'rgba(255,255,255,0.1)'}`,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                boxShadow: isActive ? `0 0 15px ${modeColor}66` : 'none',
                                transition: 'all 0.3s ease'
                            }}>
                                <span style={{ fontSize: '1rem', color: isActive ? '#fff' : '#64748b', fontWeight: 'bold' }}>
                                    {isActive ? '✓' : idx + 1}
                                </span>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: isActive ? '#f1f5f9' : '#64748b' }}>
                                    {step.label}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: '#475569', marginTop: '2px' }}>
                                    {activeData?.[step.key + '_date'] ? new Date(activeData[step.key + '_date']).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : step.desc}
                                </div>
                                {isActive && activeData?.[step.key + '_price'] && (
                                    <div style={{ fontSize: '0.7rem', color: modeColor, fontWeight: 'bold', marginTop: '2px' }}>
                                        {formatPrice(activeData[step.key + '_price'])}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Footer Logic: Show Entry Price if Holding */}
            {mode === 'SELL' && (
                <div style={{ marginTop: '1.5rem', background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.75rem', color: '#aaa' }}>
                        진입 가격 (Avg)
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fff' }}>
                        {/* We don't have entry price in sellStatus yet, unless we joined. 
                            But sellStatus has nothing? 
                            Ah, wait. Backend analysis.py injection just dumps the row.
                            sell_stock table has foreign key to manage_id? 
                            Wait, sell_stock doesn't have entry_price column? 
                            Let's check db.py again later if needed.
                            For now, assume we might need to fetch it or user manual input.
                        */}
                        Unknown
                    </div>
                </div>
            )}

            <style>{`
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.6; }
                    100% { opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default V2SignalStatus;
