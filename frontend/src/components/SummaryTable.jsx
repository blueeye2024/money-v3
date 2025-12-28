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
                        <th style={{ textAlign: 'center', padding: '1rem' }}>기술적 신호</th>
                        <th style={{ textAlign: 'center', padding: '1rem' }}>박스권/돌파</th>
                        <th style={{ textAlign: 'center', padding: '1rem' }}>뉴스 확률</th>
                        <th style={{ textAlign: 'center', padding: '1rem' }}>종합 판단</th>
                    </tr>
                </thead>
                <tbody>
                    {stocks
                        .sort((a, b) => {
                            const aPriority = a.position.includes('진입') ? 2 : (a.position.includes('유지') ? 1 : 0);
                            const bPriority = b.position.includes('진입') ? 2 : (b.position.includes('유지') ? 1 : 0);
                            return bPriority - aPriority;
                        })
                        .map(stock => {
                            const isBuy = stock.position.includes('매수') || stock.position.includes('상단');
                            const isSell = stock.position.includes('매도') || stock.position.includes('하단');

                            return (
                                <tr key={stock.ticker} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ fontWeight: 700, padding: '1rem', color: 'var(--accent-blue)' }}>{stock.ticker}</td>
                                    <td style={{ padding: '1rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{stock.name}</td>
                                    <td style={{ textAlign: 'right', padding: '1rem', fontWeight: 600 }}>${stock.current_price?.toFixed(2)}</td>
                                    <td style={{ textAlign: 'right', padding: '1rem', fontWeight: 600, color: stock.change_pct >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <span style={{
                                            padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem',
                                            background: stock.last_cross_type === 'gold' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                            color: stock.last_cross_type === 'gold' ? 'var(--accent-green)' :
                                                stock.last_cross_type === 'dead' ? 'var(--accent-red)' : 'inherit'
                                        }}>
                                            {stock.last_cross_type === 'gold' ? '골든크로스' :
                                                stock.last_cross_type === 'dead' ? '데드크로스' : '-'}
                                        </span>
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        {stock.is_box ? '📦 박스권' :
                                            stock.position.includes('돌파') ? stock.position : '-'}
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <div style={{ padding: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', fontSize: '0.85rem' }}>
                                            {stock.prob_up}%
                                        </div>
                                    </td>
                                    <td style={{ textAlign: 'center', padding: '1rem' }}>
                                        <span style={{
                                            fontWeight: 700,
                                            padding: '4px 12px', borderRadius: '6px',
                                            background: isBuy ? 'rgba(248, 113, 113, 0.1)' : isSell ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                                            color: isBuy ? 'var(--accent-red)' : isSell ? 'var(--accent-blue)' : 'var(--text-secondary)'
                                        }}>
                                            {stock.position}
                                        </span>
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
