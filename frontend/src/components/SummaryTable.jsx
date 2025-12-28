import React from 'react';

const SummaryTable = ({ stocks }) => {
    return (
        <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem', overflowX: 'auto' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>종합 분석 요약표</h2>
            <table>
                <thead>
                    <tr>
                        <th>종목</th>
                        <th>기술적 신호</th>
                        <th>박스권/돌파</th>
                        <th>뉴스 확률</th>
                        <th>종합 판단</th>
                    </tr>
                </thead>
                <tbody>
                    {stocks.map(stock => {
                        const isBuy = stock.position.includes('매수') || stock.position.includes('상단');
                        const isSell = stock.position.includes('매도') || stock.position.includes('하단');

                        return (
                            <tr key={stock.ticker}>
                                <td style={{ fontWeight: 600 }}>{stock.ticker}</td>
                                <td>
                                    <span style={{
                                        color: stock.last_cross_type === 'gold' ? 'var(--accent-green)' :
                                            stock.last_cross_type === 'dead' ? 'var(--accent-red)' : 'inherit'
                                    }}>
                                        {stock.last_cross_type === 'gold' ? '골든크로스' :
                                            stock.last_cross_type === 'dead' ? '데드크로스' : '-'}
                                    </span>
                                </td>
                                <td>
                                    {stock.is_box ? '📦 박스권' :
                                        stock.position.includes('돌파') ? stock.position : '-'}
                                </td>
                                <td>
                                    {stock.prob_up}%
                                </td>
                                <td>
                                    <span style={{
                                        fontWeight: 600,
                                        color: isBuy ? 'var(--accent-green)' : isSell ? 'var(--accent-red)' : 'var(--text-secondary)'
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
