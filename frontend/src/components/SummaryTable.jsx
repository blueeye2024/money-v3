import React from 'react';

const SummaryTable = ({ stocks }) => {
    return (
        <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem', overflowX: 'auto' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>종합 분석 요약표</h2>
            <table>
                <thead>
                    <tr>
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
                    {stocks
                        .sort((a, b) => (b.score || 0) - (a.score || 0))
                        .map(stock => {
                            const isBuy = stock.position.includes('매수') || stock.position.includes('상단');
                            const isSell = stock.position.includes('매도') || stock.position.includes('하단');
                            const details = stock.score_details || { base: 0, trend: 0, reliability: 0, breakout: 0, market: 0 };

                            return (
                                <tr key={stock.ticker} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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
                                            {isBuy ? '매수' : isSell ? '매도' : stock.position.includes('미보유') ? '미보유' : '관망'}
                                        </span>
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        {stock.is_box ? '📦 박스권' :
                                            stock.position.includes('돌파') ? '🚀 돌파' : '-'}
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <div style={{ padding: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', fontSize: '0.9rem', fontWeight: 'bold', color: 'var(--accent-gold)' }}>
                                            {stock.score}
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
    );
};

export default SummaryTable;
