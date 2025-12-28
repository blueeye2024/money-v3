import React from 'react';

const StockCard = ({ data }) => {
    const {
        ticker, current_price, change_pct, position,
        signal_time, is_box, box_high, box_low,
        rsi, macd, macd_sig, prob_up
    } = data;

    const isBuy = position?.includes('매수') || position?.includes('상단');
    const isSell = position?.includes('매도') || position?.includes('하단');
    const isObserving = !isBuy && !isSell;

    if (data.error) {
        return (
            <div className="glass-panel" style={{ padding: '1.5rem', borderLeft: `4px solid var(--accent-red)` }}>
                <h3 style={{ margin: 0 }}>{ticker}</h3>
                <p style={{ color: 'var(--accent-red)' }}>Error: {data.error}</p>
            </div>
        );
    }

    let borderColor = 'var(--glass-border)';
    if (isBuy) borderColor = 'var(--accent-red)';
    if (isSell) borderColor = 'var(--accent-blue)';

    if (position?.includes('진입')) {
        // Stronger border for entry
    }

    return (
        <div className="glass-panel" style={{ padding: '1.5rem', borderLeft: `4px solid ${borderColor}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>{ticker}</h3>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {data.name || ticker}
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>${current_price?.toFixed(2)}</div>
                    <div style={{
                        color: change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                        fontSize: '0.9rem'
                    }}>
                        {change_pct >= 0 ? '+' : ''}{change_pct?.toFixed(2)}%
                    </div>
                </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
                <span style={{
                    padding: '4px 12px',
                    borderRadius: '99px',
                    backgroundColor: isBuy ? 'rgba(248, 113, 113, 0.2)' : isSell ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                    color: isBuy ? 'var(--accent-red)' : isSell ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '0.9rem'
                }}>
                    {position}
                </span>
            </div>

            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <strong>최근 신호:</strong> {signal_time}
            </div>

            {is_box && (
                <div style={{ marginBottom: '0.5rem', fontSize: '0.9rem', background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '8px' }}>
                    <div>📦 <strong>박스권 횡보</strong></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                        <span>H: ${box_high?.toFixed(2)}</span>
                        <span>L: ${box_low?.toFixed(2)}</span>
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem', marginTop: '1rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                <div>
                    <span style={{ color: 'var(--text-secondary)' }}>RSI(14)</span>
                    <br />
                    <span style={{ color: rsi > 70 ? 'var(--accent-red)' : rsi < 30 ? 'var(--accent-green)' : 'inherit' }}>
                        {rsi?.toFixed(1)}
                    </span>
                </div>
                <div>
                    <span style={{ color: 'var(--text-secondary)' }}>MACD</span>
                    <br />
                    <span style={{ color: macd > macd_sig ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {macd?.toFixed(3)}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default StockCard;
