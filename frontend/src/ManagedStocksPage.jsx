import React, { useEffect, useState } from 'react';

const ManagedStocksPage = () => {
    const [stocks, setStocks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingStock, setEditingStock] = useState(null);
    const [formData, setFormData] = useState({
        ticker: '',
        name: '',
        group_name: '',
        buy_strategy: '',
        sell_strategy: '',
        target_ratio: 0,
        scenario_yield: 0,
        memo: ''
    });

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

    const handleOpenModal = (stock = null) => {
        if (stock) {
            setEditingStock(stock);
            setFormData({
                ticker: stock.ticker,
                name: stock.name || '',
                group_name: stock.group_name || '',
                buy_strategy: stock.buy_strategy || '',
                sell_strategy: stock.sell_strategy || '',
                target_ratio: stock.target_ratio || 0,
                scenario_yield: stock.scenario_yield || 0,
                memo: stock.memo || ''
            });
        } else {
            setEditingStock(null);
            setFormData({
                ticker: '',
                name: '',
                group_name: '',
                buy_strategy: '',
                sell_strategy: '',
                target_ratio: 0,
                scenario_yield: 0,
                memo: ''
            });
        }
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsModalOpen(false);
        setEditingStock(null);
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: (name === 'target_ratio' || name === 'scenario_yield') ? parseFloat(value) : value
        }));
    };

    const handleSave = async (e) => {
        e.preventDefault();
        const url = editingStock ? `/api/managed-stocks/${editingStock.id}` : '/api/managed-stocks';
        const method = editingStock ? 'PUT' : 'POST';

        try {
            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (res.ok) {
                handleCloseModal();
                fetchData();
            }
        } catch (e) {
            console.error("Save failed", e);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("정말 이 종목을 연동 해제하시겠습니까?")) return;
        try {
            const res = await fetch(`/api/managed-stocks/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchData();
            }
        } catch (e) {
            console.error("Delete failed", e);
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h1 style={{ fontSize: '2rem', margin: 0 }}>📦 핵심 거래 종목 관리 (Portfolio)</h1>
                <button
                    onClick={() => handleOpenModal()}
                    style={{
                        padding: '0.6rem 1.2rem',
                        background: 'var(--accent-blue)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                    }}
                >
                    + 종목 추가
                </button>
            </div>
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
                                    <th style={{ padding: '12px', textAlign: 'left' }}>Ticker / Name</th>
                                    <th style={{ padding: '12px', textAlign: 'left' }}>전략 (Strategy)</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>비중</th>
                                    <th style={{ padding: '12px', textAlign: 'center' }}>목표 수익</th>
                                    <th style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {groups[groupName].map(stock => (
                                    <tr key={stock.ticker} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '12px' }}>
                                            <div style={{ fontWeight: 'bold', fontSize: '1.2rem', color: 'white' }}>{stock.ticker}</div>
                                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{stock.name || '-'}</div>
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
                                            <div style={{ display: 'flex', gap: '5px', justifyContent: 'flex-end' }}>
                                                <button
                                                    onClick={() => handleOpenModal(stock)}
                                                    style={{
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        background: 'rgba(255,255,255,0.05)',
                                                        border: '1px solid rgba(255,255,255,0.2)',
                                                        color: '#fff',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(stock.id)}
                                                    style={{
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        background: 'rgba(239, 68, 68, 0.1)',
                                                        border: '1px solid rgba(239, 68, 68, 0.3)',
                                                        color: '#f87171',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ))}

            {isModalOpen && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', padding: '2rem', zIndex: 1000,
                    alignItems: 'center'
                }}>
                    <div className="glass-panel" style={{ width: '500px', padding: '2rem', maxHeight: '90vh', overflowY: 'auto' }}>
                        <h2 style={{ marginBottom: '1.5rem' }}>{editingStock ? '종목 전략 수정' : '새 전략 종목 추가'}</h2>
                        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>Ticker</label>
                                    <input
                                        name="ticker" value={formData.ticker} onChange={handleInputChange} required
                                        placeholder="EX) TSLA" style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                    />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>Name (한글명)</label>
                                    <input
                                        name="name" value={formData.name} onChange={handleInputChange} required
                                        placeholder="EX) 테슬라" style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                    />
                                </div>
                            </div>

                            <div style={{ flex: 1 }}>
                                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>Group (분류)</label>
                                <input
                                    name="group_name" value={formData.group_name} onChange={handleInputChange} required
                                    placeholder="EX) 레버리지" style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                />
                            </div>

                            <div>
                                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>매수 전략 (Buy Strategy)</label>
                                <textarea
                                    name="buy_strategy" value={formData.buy_strategy} onChange={handleInputChange} required
                                    rows="2" style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                />
                            </div>

                            <div>
                                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>매도 전략 (Sell Strategy)</label>
                                <textarea
                                    name="sell_strategy" value={formData.sell_strategy} onChange={handleInputChange} required
                                    rows="2" style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                />
                            </div>

                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>목표 비중 (%)</label>
                                    <input
                                        type="number" name="target_ratio" value={formData.target_ratio} onChange={handleInputChange} required
                                        style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                    />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>목표 수익 (%)</label>
                                    <input
                                        type="number" step="0.1" name="scenario_yield" value={formData.scenario_yield} onChange={handleInputChange}
                                        style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                    />
                                </div>
                            </div>

                            <div>
                                <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>메모 (Memo)</label>
                                <input
                                    name="memo" value={formData.memo} onChange={handleInputChange}
                                    style={{ width: '100%', padding: '0.6rem', background: 'rgba(0,0,0,0.2)', border: '1px solid #444', color: 'white' }}
                                />
                            </div>

                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={handleCloseModal} style={{ flex: 1, padding: '0.8rem', background: '#333', color: 'white', border: 'none', cursor: 'pointer' }}>취소</button>
                                <button type="submit" style={{ flex: 1, padding: '0.8rem', background: 'var(--accent-blue)', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}>저장하기</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ManagedStocksPage;
