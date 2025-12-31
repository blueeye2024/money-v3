import React, { useEffect, useState } from 'react';

const ManagedStocksPage = () => {
    const [stocks, setStocks] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const res = await fetch('/api/managed-stocks');
            const data = await res.json();
            if (Array.isArray(data)) {
                setStocks(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    // Grouping
    const groups = stocks.reduce((acc, stock) => {
        const g = stock.group_name || 'Uncategorized';
        if (!acc[g]) acc[g] = [];
        acc[g].push(stock);
        return acc;
    }, {});

    const sortedGroupNames = Object.keys(groups).sort();

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading Managed Stocks...</div>;

    return (
        <div className="container">
            <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>📦 핵심 거래 종목 관리 (Portfolio)</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                Cheongan 2.0 공식에 따라 관리되는 핵심 포트폴리오 및 전략 리스트입니다.
            </p>

            {sortedGroupNames.map(groupName => (
                <div key={groupName} style={{ marginBottom: '3rem' }}>
                    <h2 style={{
                        fontSize: '1.4rem',
                        color: 'var(--accent-blue)',
                        borderBottom: '1px solid rgba(255,255,255,0.1)',
                        paddingBottom: '0.5rem',
                        marginBottom: '1rem'
                    }}>
                        {groupName}
                    </h2>

                    <div className="table-container">
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead>
                                <tr style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Ticker</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>전략 (Strategy)</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>비중</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>목표 수익</th>
                                    <th style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {groups[groupName].map(stock => (
                                    <tr key={stock.ticker} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '12px', fontWeight: 'bold', fontSize: '1.2rem' }}>
                                            {stock.ticker}
                                        </td>
                                        <td style={{ padding: '12px' }}>
                                            <div style={{ marginBottom: '6px' }}>
                                                <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>[BUY]</span> {stock.buy_strategy}
                                            </div>
                                            <div>
                                                <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>[SELL]</span> {stock.sell_strategy}
                                            </div>
                                            {stock.memo && (
                                                <div style={{ marginTop: '4px', fontSize: '0.8rem', color: '#888', fontStyle: 'italic' }}>
                                                    Memo: {stock.memo}
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ padding: '12px', textAlign: 'center', color: 'var(--accent-gold)', fontWeight: 'bold' }}>
                                            {stock.target_ratio}%
                                        </td>
                                        <td style={{ padding: '12px', textAlign: 'center' }}>
                                            {stock.scenario_yield > 0 ? `+${stock.scenario_yield}%` : '-'}
                                        </td>
                                        <td style={{ padding: '12px', textAlign: 'right' }}>
                                            <button style={{
                                                padding: '4px 8px',
                                                fontSize: '0.8rem',
                                                background: 'transparent',
                                                border: '1px solid var(--text-secondary)',
                                                color: 'var(--text-secondary)',
                                                borderRadius: '4px',
                                                cursor: 'not-allowed',
                                                opacity: 0.5
                                            }} title="편집 기능 준비중">
                                                Edit
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ))}

            <div style={{ marginTop: '2rem', textAlign: 'center', color: '#666', fontSize: '0.8rem' }}>
                * 추가/수정/삭제 기능은 v2.1 업데이트 예정입니다.<br />
                * 공식 버전: 2.0.0 (Safety Switch: -10%)
            </div>
        </div>
    );
};

export default ManagedStocksPage;
