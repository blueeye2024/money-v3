import React from 'react';

const getScoreInterpretation = (score, position) => {
    const pos = position || '';
    const isSell = pos.includes('매도') || pos.includes('하단');
    if (score >= 80) return isSell ? "🚨 긴급 매도" : "✨ 강력 매수";
    if (score >= 70) return isSell ? "📉 매도" : "🟢 매수";
    if (score >= 50) return isSell ? "⚠ 경계" : "🟡 관망";
    return isSell ? "📉 조정" : "⚪ 관망";
};

const SummaryTable = ({ stocks, onToggleVisibility }) => {
    return (
        <div className="glass-panel" style={{ marginTop: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', padding: '1.5rem 1.5rem 0' }}>종합 분석 요약표</h2>
            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style={{ textAlign: 'center', padding: '1rem', width: '40px' }}>표시</th>
                            <th style={{ textAlign: 'left', padding: '1rem' }}>종목</th>
                            <th style={{ textAlign: 'left', padding: '1rem' }}>종목명</th>
                            <th style={{ textAlign: 'right', padding: '1rem' }}>현재가</th>
                            <th style={{ textAlign: 'right', padding: '1rem' }}>등락 (%)</th>
                            <th style={{ textAlign: 'center', padding: '1rem' }}>보유 여부</th>
                            <th style={{ textAlign: 'center', padding: '1rem' }}>기술적 신호</th>
                            <th style={{ textAlign: 'center', padding: '1rem' }}>박스권/돌파</th>
                            <th style={{ textAlign: 'center', padding: '1rem' }}>점수</th>
                            <th style={{ textAlign: 'left', padding: '1rem' }}>세부 점수</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stocks.map(stock => {
                            const pos = stock.position || '';
                            const isBuy = pos.includes('매수') || pos.includes('상단');
                            const isSell = pos.includes('매도') || pos.includes('하단');
                            const details = stock.score_details || { base: 0, trend: 0, reliability: 0, breakout: 0, market: 0 };
                            const isVisible = stock.is_visible !== false;

                            return (
                                <tr key={stock.ticker} style={{
                                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                                    opacity: isVisible ? 1 : 0.5,
                                    transition: 'opacity 0.2s'
                                }}>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <input
                                            type="checkbox"
                                            checked={isVisible}
                                            onChange={(e) => onToggleVisibility(stock.ticker, e.target.checked)}
                                            style={{ cursor: 'pointer', width: '18px', height: '18px' }}
                                        />
                                    </td>
                                    <td style={{ fontWeight: 700, padding: '1rem', color: 'var(--accent-blue)' }}>{stock.ticker}</td>
                                    <td style={{ padding: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                        {stock.name.length > 20 ? stock.name.substring(0, 20) + '...' : stock.name}
                                    </td>
                                    <td style={{ textAlign: 'right', padding: '1rem', fontWeight: 600 }}>${stock.current_price ? stock.current_price.toFixed(2) : '-'}</td>
                                    <td style={{ textAlign: 'right', padding: '1rem', fontWeight: 600, color: stock.change_pct >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct ? stock.change_pct.toFixed(2) : '0.00'}%
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        {stock.is_held ? <span style={{ color: 'var(--accent-gold)' }}>✔ 보유</span> : <span style={{ color: '#555', fontSize: '0.8rem' }}>미보유</span>}
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <span style={{
                                            fontWeight: 700,
                                            padding: '4px 12px', borderRadius: '6px',
                                            background: isBuy ? 'rgba(248, 113, 113, 0.1)' : isSell ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                                            color: isBuy ? 'var(--accent-red)' : isSell ? 'var(--accent-blue)' : 'var(--text-secondary)'
                                        }}>
                                            {isBuy ? '매수' : isSell ? '매도' : pos.includes('미보유') ? '미보유' : '관망'}
                                        </span>
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        {stock.is_box ? '📦 박스권' :
                                            stock.position.includes('돌파') ? '🚀 돌파' : '-'}
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <div style={{ padding: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: 'var(--accent-gold)' }}>{stock.score}</div>
                                            <div style={{ fontSize: '0.65rem', color: '#aaa', marginTop: '2px', whiteSpace: 'nowrap' }}>
                                                {getScoreInterpretation(stock.score, stock.position)}
                                            </div>
                                        </div>
                                    </td>
                                    <td style={{ textAlign: 'left', padding: '1rem', fontSize: '0.8rem', color: '#aaa' }}>
                                        (기본:{details.base} 추세:{details.trend} 신뢰:{details.reliability} 돌파:{details.breakout} 시장:{details.market || 0})
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

export default SummaryTable;
