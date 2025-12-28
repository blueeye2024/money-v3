import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const JournalPage = () => {
    // State
    const [stocks, setStocks] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [stats, setStats] = useState([]);
    const [view, setView] = useState('journal'); // journal or stocks

    // Form State
    const [formData, setFormData] = useState({
        id: null,
        ticker: '',
        trade_type: 'BUY',
        qty: '',
        price: '',
        trade_date: new Date().toISOString().slice(0, 16),
        memo: ''
    });

    const [stockForm, setStockForm] = useState({ code: '', name: '' });

    useEffect(() => {
        fetchStocks();
        fetchTransactions();
        fetchStats();
    }, []);

    // --- API Calls ---
    const fetchStocks = async () => {
        try {
            const res = await fetch('/api/stocks');
            if (res.ok) setStocks(await res.json());
        } catch (e) { console.error(e); }
    };

    const fetchTransactions = async () => {
        try {
            const res = await fetch('/api/transactions');
            if (res.ok) setTransactions(await res.json());
        } catch (e) { console.error(e); }
    };

    const fetchStats = async () => {
        try {
            const res = await fetch('/api/transactions/stats');
            if (res.ok) setStats(await res.json());
        } catch (e) { console.error(e); }
    };

    // --- Stock Management ---
    const handleStockSubmit = async (e) => {
        e.preventDefault();
        const res = await fetch('/api/stocks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(stockForm)
        });
        if (res.ok) {
            alert("종목이 등록되었습니다.");
            setStockForm({ code: '', name: '' });
            fetchStocks();
        } else {
            alert("등록 실패");
        }
    };

    const deleteStock = async (code) => {
        if (!confirm("정말 삭제하시겠습니까? 관련 매매 기록도 삭제될 수 있습니다.")) return;
        const res = await fetch(`/api/stocks/${code}`, { method: 'DELETE' });
        if (res.ok) fetchStocks();
    };

    // --- Transaction Management ---
    const handleTxSubmit = async (e) => {
        e.preventDefault();
        const url = formData.id ? `/api/transactions/${formData.id}` : '/api/transactions';
        const method = formData.id ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (res.ok) {
            alert(formData.id ? "수정되었습니다." : "등록되었습니다.");
            setFormData({ id: null, ticker: '', trade_type: 'BUY', qty: '', price: '', trade_date: new Date().toISOString().slice(0, 16), memo: '' });
            fetchTransactions();
            fetchStats();
        } else {
            alert("처리 실패");
        }
    };

    const editTx = (tx) => {
        setFormData({
            id: tx.id,
            ticker: tx.ticker,
            trade_type: tx.trade_type,
            qty: tx.qty,
            price: tx.price,
            trade_date: tx.trade_date, // might need formatting
            memo: tx.memo
        });
    };

    const deleteTx = async (id) => {
        if (!confirm("삭제하시겠습니까?")) return;
        const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
        if (res.ok) {
            fetchTransactions();
            fetchStats();
        }
    };

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '4rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 className="text-gradient" style={{ fontSize: '2rem', margin: 0 }}>매매 일지 & 수익률 분석</h1>
                <div>
                    <button onClick={() => setView('journal')} style={{ marginRight: '1rem', background: view === 'journal' ? 'var(--accent-blue)' : 'transparent', border: '1px solid var(--accent-blue)', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>매매 기록</button>
                    <button onClick={() => setView('stocks')} style={{ background: view === 'stocks' ? 'var(--accent-blue)' : 'transparent', border: '1px solid var(--accent-blue)', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>종목 관리</button>
                </div>
            </div>

            {view === 'stocks' && (
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <h3>종목 관리</h3>
                    <form onSubmit={handleStockSubmit} style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                        <input placeholder="종목코드 (예: SOXL)" value={stockForm.code} onChange={e => setStockForm({ ...stockForm, code: e.target.value.toUpperCase() })} required className="input-field" />
                        <input placeholder="종목명 (예: 반도체 3배 Bull)" value={stockForm.name} onChange={e => setStockForm({ ...stockForm, name: e.target.value })} required className="input-field" style={{ flex: 2 }} />
                        <button type="submit" style={{ background: 'var(--accent-green)', border: 'none', color: 'white', padding: '0 2rem', borderRadius: '4px', cursor: 'pointer' }}>등록</button>
                    </form>
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {stocks.map(s => (
                            <li key={s.code} style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                <span><strong>{s.code}</strong> - {s.name}</span>
                                <button onClick={() => deleteStock(s.code)} style={{ color: 'var(--accent-red)', background: 'none', border: 'none', cursor: 'pointer' }}>삭제</button>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {view === 'journal' && (
                <>
                    {/* Input Form */}
                    <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
                        <h3 style={{ marginBottom: '1rem' }}>{formData.id ? '매매 기록 수정' : '새 매매 기록 추가'}</h3>
                        <form onSubmit={handleTxSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>

                            {/* Stock Select */}
                            <select
                                value={formData.ticker}
                                onChange={e => setFormData({ ...formData, ticker: e.target.value })}
                                required
                                className="input-field"
                                style={{ background: '#1e293b' }}
                            >
                                <option value="">종목 선택</option>
                                {stocks.map(s => <option key={s.code} value={s.code}>{s.name} ({s.code})</option>)}
                            </select>

                            {/* Buy/Sell Radio */}
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '0 1rem', borderRadius: '6px', border: '1px solid var(--glass-border)' }}>
                                <label style={{ cursor: 'pointer', color: formData.trade_type === 'BUY' ? 'var(--accent-red)' : 'white', marginRight: '1rem' }}>
                                    <input type="radio" name="type" checked={formData.trade_type === 'BUY'} onChange={() => setFormData({ ...formData, trade_type: 'BUY' })} /> 매수 (Buy)
                                </label>
                                <label style={{ cursor: 'pointer', color: formData.trade_type === 'SELL' ? 'var(--accent-blue)' : 'white' }}>
                                    <input type="radio" name="type" checked={formData.trade_type === 'SELL'} onChange={() => setFormData({ ...formData, trade_type: 'SELL' })} /> 매도 (Sell)
                                </label>
                            </div>

                            <input type="datetime-local" value={formData.trade_date} onChange={e => setFormData({ ...formData, trade_date: e.target.value })} required className="input-field" />
                            <input type="number" placeholder="가격($)" step="0.01" value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })} required className="input-field" />
                            <input type="number" placeholder="수량" value={formData.qty} onChange={e => setFormData({ ...formData, qty: e.target.value })} required className="input-field" />

                            <input placeholder="메모" value={formData.memo} onChange={e => setFormData({ ...formData, memo: e.target.value })} className="input-field" style={{ gridColumn: '1 / -1' }} />

                            <button type="submit" style={{ gridColumn: '1 / -1', padding: '1rem', background: 'var(--accent-purple)', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
                                {formData.id ? '수정 내용 저장' : '기록 저장'}
                            </button>
                            {formData.id && (
                                <button type="button" onClick={() => setFormData({ id: null, ticker: '', trade_type: 'BUY', qty: '', price: '', trade_date: '', memo: '' })} style={{ gridColumn: '1 / -1', padding: '0.5rem', background: 'gray', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>취소</button>
                            )}
                        </form>
                    </div>

                    {/* Chart */}
                    <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', height: '400px' }}>
                        <h3 style={{ marginBottom: '1rem' }}>실현 손익 분석 (FIFO 기준)</h3>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="date" stroke="var(--text-secondary)" tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                                <YAxis stroke="var(--text-secondary)" />
                                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid var(--glass-border)' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                                <Legend />
                                <Bar dataKey="profit" name="실현손익($)" fill="#8884d8">
                                    {stats.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.profit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)'} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* List Table */}
                    <div className="glass-panel" style={{ padding: '2rem', overflowX: 'auto' }}>
                        <h3 style={{ marginBottom: '1rem' }}>최근 거래 내역</h3>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead>
                                <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--glass-border)' }}>
                                    <th style={{ padding: '1rem', textAlign: 'left' }}>날짜</th>
                                    <th style={{ padding: '1rem', textAlign: 'left' }}>종목</th>
                                    <th style={{ padding: '1rem', textAlign: 'center' }}>구분</th>
                                    <th style={{ padding: '1rem', textAlign: 'right' }}>가격</th>
                                    <th style={{ padding: '1rem', textAlign: 'right' }}>수량</th>
                                    <th style={{ padding: '1rem', textAlign: 'left' }}>메모</th>
                                    <th style={{ padding: '1rem', textAlign: 'right' }}>관리</th>
                                </tr>
                            </thead>
                            <tbody>
                                {transactions.length === 0 ? (
                                    <tr><td colSpan="7" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>거래 기록이 없습니다.</td></tr>
                                ) : (
                                    transactions.map(tx => (
                                        <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                            <td style={{ padding: '1rem' }}>{new Date(tx.trade_date).toLocaleString()}</td>
                                            <td style={{ padding: '1rem' }}>
                                                <strong>{tx.stock_name || tx.ticker}</strong>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{tx.ticker}</div>
                                            </td>
                                            <td style={{ padding: '1rem', textAlign: 'center' }}>
                                                <span style={{
                                                    padding: '4px 12px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 'bold',
                                                    background: tx.trade_type === 'BUY' ? 'rgba(248, 113, 113, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                                                    color: tx.trade_type === 'BUY' ? 'var(--accent-red)' : 'var(--accent-blue)'
                                                }}>
                                                    {tx.trade_type === 'BUY' ? '매수' : '매도'}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1rem', textAlign: 'right' }}>${tx.price.toFixed(2)}</td>
                                            <td style={{ padding: '1rem', textAlign: 'right' }}>{tx.qty}</td>
                                            <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{tx.memo}</td>
                                            <td style={{ padding: '1rem', textAlign: 'right' }}>
                                                <button onClick={() => editTx(tx)} style={{ marginRight: '0.5rem', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}>수정</button>
                                                <button onClick={() => deleteTx(tx.id)} style={{ background: 'none', border: 'none', color: 'var(--accent-red)', cursor: 'pointer' }}>삭제</button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            <style>{`
                .input-field {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid var(--glass-border);
                    color: white;
                    padding: 0.8rem;
                    border-radius: 6px;
                    width: 100%;
                    outline: none;
                }
                .input-field:focus {
                    border-color: var(--accent-blue);
                }
            `}</style>
        </div>
    );
};

export default JournalPage;
