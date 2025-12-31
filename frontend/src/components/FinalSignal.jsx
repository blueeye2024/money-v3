import React, { useMemo } from 'react';

const getScoreInterpretation = (score, position) => {
    const pos = position || '';
    const isSell = pos.includes('매도') || pos.includes('하단');
    if (score >= 80) return isSell ? "🚨 긴급 매도" : "✨ 강력 매수";
    if (score >= 70) return isSell ? "📉 매도" : "🟢 매수";
    if (score >= 50) return isSell ? "⚠ 경계/약세" : "🟡 관망/중립";
    return isSell ? "📉 단기 조정" : "⚪ 관망";
};

const FinalSignal = ({ stocks }) => {
    // Determine Recommended Portfolio
    const portfolio = useMemo(() => {
        if (!stocks || stocks.length === 0) return [];

        // Priority:
        // 1. Buy Signal (Entry / Add)
        // 2. Sell Signal (Exit / Partial)
        // 3. Held (Hold/Wait)
        // 4. Watchlist (Others)

        const categorized = stocks.map(stock => {
            const pos = stock.position || "";
            const isHeld = stock.is_held || false;
            const score = stock.score || 0;
            const target = stock.target_ratio || 0;

            let type = "WATCH"; // DEFAULT
            let action = "관망 (Wait)";
            let priority = 4;

            const isBuy = pos.includes('매수') || pos.includes('상단');
            const isSell = pos.includes('매도') || pos.includes('하단');
            const isHold = pos.includes('유지') || pos.includes('관망'); // Using '유지' keyword from analysis

            if (isBuy) {
                type = "BUY";
                action = isHeld ? `추가 매수 (목표 ${target}%)` : `신규 진입 (목표 ${target}%)`;
                priority = 1;
            } else if (isSell && isHeld) {
                type = "SELL";
                action = "매도 대응 (Profit/Cut)";
                priority = 2;
            } else if (isHeld) {
                type = "HOLD";
                action = "보유 (Hold)";
                priority = 3;
            }

            return { ...stock, type, action, priority };
        });

        // Sort
        categorized.sort((a, b) => a.priority - b.priority || b.score - a.score);

        return categorized;
    }, [stocks]);

    if (!portfolio || portfolio.length === 0) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '3rem' }}>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', letterSpacing: '2px', textAlign: 'center' }}>
                ⭐ Cheongan Recommended Portfolio
            </h2>

            <div className="glass-panel" style={{ padding: '0', overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '1rem', textAlign: 'center' }}>Rank</th>
                            <th style={{ padding: '1rem', textAlign: 'left' }}>Stock</th>
                            <th style={{ padding: '1rem', textAlign: 'center' }}>Position</th>
                            <th style={{ padding: '1rem', textAlign: 'left' }}>Action Plan</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>Score</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>Price</th>
                            <th style={{ padding: '1rem', textAlign: 'center' }}>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {portfolio.map((stock, index) => {
                            const isBuy = stock.type === 'BUY';
                            const isSell = stock.type === 'SELL';
                            const rowBg = index % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent';

                            return (
                                <tr key={stock.ticker} style={{ background: rowBg, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '1rem', textAlign: 'center', fontWeight: 'bold', color: index === 0 ? 'var(--accent-gold)' : '#ccc' }}>
                                        {index + 1}
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: 'bold', fontSize: '1.1rem' }}>
                                        {stock.ticker}
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 'normal' }}>{stock.name}</div>
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'center' }}>
                                        <span style={{
                                            padding: '4px 10px', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.8rem',
                                            background: isBuy ? 'rgba(34, 197, 94, 0.2)' : isSell ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                            color: isBuy ? '#4ade80' : isSell ? '#f87171' : '#ccc'
                                        }}>
                                            {stock.type}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1rem', color: isBuy ? '#4ade80' : isSell ? '#f87171' : '#ddd' }}>
                                        {stock.action}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 'bold' }}>
                                        {stock.score}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                                        ${stock.current_price?.toFixed(2)}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'center', color: '#aaa', fontSize: '0.8rem' }}>
                                        {stock.position}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};




export default FinalSignal;
