import React, { useMemo } from 'react';

const FinalSignal = ({ stocks }) => {
    const topPicks = useMemo(() => {
        if (!stocks || stocks.length === 0) return [];
        // Sort by score DESC
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
                {/* 1st Priority Card */}
                <PortfolioCard stock={bestStock} rank={1} />

                {/* 2nd Priority Card */}
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

    // Style adjustments
    if (isBuy) {
        borderColor = 'var(--accent-red)';
        shadowColor = 'rgba(248, 113, 113, 0.3)';
        signalColor = 'var(--accent-red)';
    } else if (isSell) {
        borderColor = 'var(--accent-blue)';
        shadowColor = 'rgba(59, 130, 246, 0.3)';
        signalColor = 'var(--accent-blue)';
    }

    return (
        <div className="glass-panel" style={{
            flex: isRank1 ? '1.5' : '1',
            minWidth: '300px',
            padding: '2rem',
            textAlign: 'center',
            background: isBuy
                ? 'linear-gradient(135deg, rgba(40, 20, 20, 0.8), rgba(15, 10, 10, 0.9))'
                : isSell
                    ? 'linear-gradient(135deg, rgba(20, 30, 50, 0.8), rgba(10, 15, 30, 0.9))'
                    : 'linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9))',
            border: `2px solid ${borderColor}`,
            boxShadow: isRank1 ? `0 0 30px ${shadowColor}` : `0 0 15px ${shadowColor}`,
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* Rank Badge */}
            <div style={{
                position: 'absolute', top: 0, left: 0,
                background: isRank1 ? 'var(--accent-gold)' : 'var(--text-secondary)',
                color: 'black', fontWeight: 'bold', padding: '0.4rem 1rem',
                borderBottomRightRadius: '12px', fontSize: '0.9rem'
            }}>
                {isRank1 ? '👑 1st Pick' : '🥈 2nd Pick'}
            </div>

            {/* Score Badge */}
            <div style={{
                position: 'absolute', top: '1rem', right: '1rem',
                background: 'rgba(255,255,255,0.1)',
                padding: '0.4rem 0.8rem', borderRadius: '20px',
                fontSize: '0.8rem', border: '1px solid rgba(255,255,255,0.2)'
            }}>
                Score: {stock.score}
            </div>

            <div style={{ fontSize: isRank1 ? '3.5rem' : '2.5rem', fontWeight: 800, margin: '1rem 0 0.5rem 0' }} className="text-gradient">
                {stock.ticker}
            </div>

            <div style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>
                현재가: <span style={{ fontWeight: 'bold' }}>${stock.current_price?.toFixed(2)}</span>
            </div>

            <div style={{ fontSize: '1.4rem', fontWeight: 600, marginBottom: '1.5rem', color: signalColor }}>
                {stock.position}
            </div>

            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '8px', textAlign: 'left' }}>
                <h3 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Analysis Summary</h3>
                <p style={{ margin: 0, lineHeight: 1.5, fontSize: '0.9rem', color: '#e2e8f0' }}>
                    기술적 점수 <strong>{stock.score}점</strong>.
                    RSI({stock.rsi?.toFixed(1)}) 및 MACD 추세가
                    {stock.prob_up >= 60 ? ' 강력한 상승' : stock.prob_up <= 40 ? ' 하락/조정' : ' 중립적'} 흐름을 지지합니다.
                    {stock.is_box && ` 박스권($${stock.box_low}~$${stock.box_high}) 움직임이 특징적입니다.`}
                </p>
            </div>
        </div>
    );
};

export default FinalSignal;
