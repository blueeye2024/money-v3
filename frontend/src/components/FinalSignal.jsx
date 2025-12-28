import React, { useMemo } from 'react';

const FinalSignal = ({ stocks }) => {
    const bestStock = useMemo(() => {
        if (!stocks || stocks.length === 0) return null;

        // Logic to score stocks
        // Priority: Breakout > Entry > Maintain

        let candidates = stocks.map(s => {
            let score = 0;
            if (s.position.includes('박스권 돌파')) score += 100;
            if (s.position.includes('매수 진입')) score += 80;
            if (s.position.includes('매도 진입')) score += 80;
            if (s.position.includes('매수 유지')) score += 50;
            if (s.position.includes('매도 유지')) score += 50;

            // Tie breaker: Probability
            score += (s.prob_up / 100);

            return { ...s, score };
        });

        candidates.sort((a, b) => b.score - a.score);
        return candidates[0];
    }, [stocks]);

    if (!bestStock) return null;

    return (
        <div className="glass-panel" style={{
            padding: '2rem',
            marginBottom: '2rem',
            textAlign: 'center',
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9))',
            border: '2px solid var(--accent-blue)',
            boxShadow: '0 0 20px rgba(56, 189, 248, 0.2)'
        }}>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', letterSpacing: '2px' }}>
                PORTFOLIO LEVEL FINAL DECISION
            </h2>
            <div style={{ fontSize: '3rem', fontWeight: 800, margin: '1rem 0' }} className="text-gradient">
                {bestStock.ticker}
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '1rem', color: bestStock.score >= 80 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                FINAL SIGNAL: {bestStock.position}
            </div>

            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '8px', maxWidth: '600px', margin: '0 auto' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>선정 이유</h3>
                <p style={{ margin: 0, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                    {bestStock.ticker} 종목은 현재 <strong>{bestStock.position}</strong> 상태입니다.
                    기술적 지표(RSI {bestStock.rsi.toFixed(1)}, MACD {bestStock.macd.toFixed(3)})와
                    뉴스 기반 상승 확률 {bestStock.prob_up}%를 종합적으로 고려할 때,
                    가장 신뢰도 높은 추세를 보이고 있습니다.
                    {bestStock.is_box && ` 현재 박스권($${bestStock.box_low.toFixed(2)} - $${bestStock.box_high.toFixed(2)}) 내에서 움직임을 주시해야 합니다.`}
                </p>
            </div>
        </div>
    );
};

export default FinalSignal;
