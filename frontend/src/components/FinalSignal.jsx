import React, { useMemo } from 'react';

const FinalSignal = ({ stocks }) => {
    const topPicks = useMemo(() => {
        if (!stocks || stocks.length === 0) return [];
        const sorted = [...stocks].sort((a, b) => (b.score || 0) - (a.score || 0));
        return sorted.slice(0, 2);
    }, [stocks]);

    if (!topPicks || topPicks.length === 0) return null;

    const [bestStock, secondStock] = topPicks;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '3rem' }}>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', letterSpacing: '2px', textAlign: 'center' }}>
                PORTFOLIO LEVEL FINAL DECISION
            </h2>

            <div style={{ display: 'flex', gap: '1.5rem', flexDirection: 'row', flexWrap: 'wrap' }}>
                <PortfolioCard stock={bestStock} rank={1} />
                {secondStock && <PortfolioCard stock={secondStock} rank={2} />}
            </div>
        </div>
    );
};

const PortfolioCard = ({ stock, rank }) => {
    const isBuy = stock.position.includes('매수') || stock.position.includes('상단');
    const isSell = stock.position.includes('매도') || stock.position.includes('하단');
    const isRank1 = rank === 1;

    let borderColor = 'var(--accent-blue)';
    let shadowColor = 'rgba(56, 189, 248, 0.2)';
    let signalColor = 'var(--text-primary)';

    if (isBuy) {
        borderColor = 'var(--accent-red)';
        shadowColor = 'rgba(248, 113, 113, 0.3)';
        signalColor = 'var(--accent-red)';
    } else if (isSell) {
        borderColor = 'var(--accent-blue)';
        shadowColor = 'rgba(59, 130, 246, 0.3)';
        signalColor = 'var(--accent-blue)';
    }

    const details = stock.score_details || {};

    return (
        <div className="glass-panel" style={{
            flex: 1, // Fix: Equal Width
            minWidth: '300px',
            padding: '2rem',
            textAlign: 'center',
            background: isBuy
                ? 'linear-gradient(135deg, rgba(40, 20, 20, 0.9), rgba(15, 10, 10, 0.95))'
                : isSell
                    ? 'linear-gradient(135deg, rgba(20, 30, 50, 0.9), rgba(10, 15, 30, 0.95))'
                    : 'linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95))',
            border: `2px solid ${borderColor}`,
            boxShadow: isRank1 ? `0 0 40px ${shadowColor}` : `0 0 20px ${shadowColor}`,
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* Rank Badge */}
            <div style={{
                position: 'absolute', top: 0, left: 0,
                background: 'rgba(0,0,0,0.6)',
                color: isRank1 ? 'var(--accent-gold)' : '#E2E8F0',
                fontWeight: 'bold', padding: '0.4rem 1rem',
                borderBottomRightRadius: '12px', fontSize: '1.1rem',
                boxShadow: '2px 2px 10px rgba(0,0,0,0.5)',
                borderRight: isRank1 ? '1px solid var(--accent-gold)' : '1px solid #E2E8F0',
                borderBottom: isRank1 ? '1px solid var(--accent-gold)' : '1px solid #E2E8F0'
            }}>
                {isRank1 ? '👑 1st Pick' : '🥈 2nd Pick'}
            </div>

            {/* Score Badge */}
            <div style={{
                position: 'absolute', top: '1rem', right: '1rem',
                background: 'rgba(0,0,0,0.4)',
                padding: '0.4rem 0.8rem', borderRadius: '20px',
                fontSize: '0.9rem', border: '1px solid rgba(255,255,255,0.3)',
                color: 'var(--accent-gold)', fontWeight: 'bold'
            }}>
                Score: {stock.score}
            </div>

            {/* Ticker - Ensure Yellow for Rank 1 */}
            <div style={{
                fontSize: isRank1 ? '4rem' : '3rem',
                fontWeight: 800,
                margin: '2rem 0 0.5rem 0',
                color: isRank1 ? 'var(--accent-gold)' : 'white'
            }}>
                {stock.ticker}
            </div>

            <div style={{ fontSize: '1.0rem', color: '#ccc', marginBottom: '0.5rem' }}>{stock.name}</div>

            <div style={{ fontSize: '1.2rem', marginBottom: '1.5rem', fontWeight: 600 }}>
                현재가: <span style={{ color: 'white' }}>${stock.current_price ? stock.current_price.toFixed(2) : '-'}</span>
            </div>

            <div style={{
                fontSize: '1.6rem', fontWeight: 700, marginBottom: '2rem',
                color: signalColor,
                textShadow: `0 0 10px ${shadowColor}`
            }}>
                {stock.position}
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.2rem', borderRadius: '12px', textAlign: 'left', border: '1px solid rgba(255,255,255,0.1)' }}>
                <h3 style={{ fontSize: '0.9rem', marginBottom: '0.8rem', color: 'var(--accent-gold)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
                    📊 점수 기준 (Score Criteria)
                </h3>
                <div style={{ fontSize: '0.9rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>• 기본 점수 (Base):</span>
                        <strong>{details.base || 0}점</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>• 추세 (Trend):</span>
                        <strong>{details.trend || 0}점</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>• 신뢰도 (Reliability):</span>
                        <strong>{details.reliability || 0}점</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>• 돌파 (Breakout):</span>
                        <strong>{details.breakout || 0}점</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>• 시장변동성 (Market):</span>
                        <strong>{details.market || 0}점</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.4rem', color: 'var(--accent-gold)' }}>
                        <strong>총점 (Total):</strong>
                        <strong>{stock.score}점</strong>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FinalSignal;
