import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const JournalPage = () => {
    // === State ===
    const [stocks, setStocks] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [stats, setStats] = useState([]);
    const [view, setView] = useState('journal'); // 'journal' | 'stocks'
    const [exchangeRate, setExchangeRate] = useState(1350);

    // Form State (Journal)
    const [formData, setFormData] = useState({
        id: null,
        ticker: '',
        trade_type: 'BUY',
        qty: '',
        price: '',
        trade_date: new Date().toISOString().slice(0, 16),
        memo: ''
    });

    // Form State (Stock Manager)
    const [stockForm, setStockForm] = useState({ code: '', name: '' });

    // === Effects ===
    useEffect(() => {
        fetchStocks();
        fetchTransactions();
        fetchStats();
        fetchExchangeRate();
    }, []);

    const fetchExchangeRate = async () => {
        try {
            const res = await fetch('/api/exchange-rate');
            if (res.ok) {
                const data = await res.json();
                setExchangeRate(data.rate);
            }
        } catch (e) { console.error(e); }
    };

    // === API Calls ===
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

    // === Actions: Stock Management ===
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

    // === Actions: Transactions ===
    const handleTxSubmit = async (e) => {
        e.preventDefault();

        // Validation & Type Conversion
        const payload = {
            ...formData,
            qty: parseInt(formData.qty),
            price: parseFloat(formData.price)
        };

        // Remove ID for POST (create) to match Pydantic model if strictly checking, 
        // though usually ignored. Safer to strip.
        if (!formData.id) delete payload.id;

        const url = formData.id ? `/api/transactions/${formData.id}` : '/api/transactions';
        const method = formData.id ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            alert(formData.id ? "수정되었습니다." : "등록되었습니다.");
            setFormData({
                id: null, ticker: formData.ticker, // Keep ticker for convenience
                trade_type: 'BUY', qty: '', price: '',
                trade_date: new Date().toISOString().slice(0, 16), memo: ''
            });
            fetchTransactions();
            fetchStats();
        } else {
            const err = await res.text();
            console.error(err);
            alert("처리 실패: " + err);
        }
    };

    const editTx = (tx) => {
        setFormData({
            id: tx.id,
            ticker: tx.ticker,
            trade_type: tx.trade_type,
            qty: tx.qty,
            price: tx.price,
            trade_date: tx.trade_date,
            memo: tx.memo
        });
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const deleteTx = async (id) => {
        if (!confirm("삭제하시겠습니까?")) return;
        const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
        if (res.ok) {
            fetchTransactions();
            fetchStats();
        }
    };

    // === Helpers ===
    const getTotalProfit = () => {
        return stats.reduce((sum, item) => sum + item.profit, 0);
    };

    const getStockProfit = (ticker) => {
        return stats.filter(s => s.ticker === ticker).reduce((sum, item) => sum + item.profit, 0);
    };

    // Group transactions by ticker
    const groupedTransactions = transactions.reduce((acc, tx) => {
        if (!acc[tx.ticker]) acc[tx.ticker] = [];
        acc[tx.ticker].push(tx);
        return acc;
    }, {});

    // Sort Groups (maybe by name or recent activity) - currently just keys
    const sortedTickers = Object.keys(groupedTransactions).sort();

    const getPeriod = (txList) => {
        if (!txList || txList.length === 0) return '-';
        const dates = txList.map(t => new Date(t.trade_date).getTime());
        const min = new Date(Math.min(...dates));
        const max = new Date(Math.max(...dates));
        return `${min.toLocaleDateString()} ~ ${max.toLocaleDateString()}`;
    };

    // === Render ===
    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '6rem', fontFamily: "'Inter', sans-serif" }}>

            {/* Header Area */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', marginTop: '2rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.2rem', margin: 0, fontWeight: 700 }}>매매 일지 & 수익률 분석</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>나만의 트레이딩 기록과 성과를 관리하세요.</p>
                </div>

                <div style={{ display: 'flex', gap: '1rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '8px' }}>
                    <TabButton active={view === 'journal'} onClick={() => setView('journal')} icon="📝">매매 기록</TabButton>
                    <TabButton active={view === 'stocks'} onClick={() => setView('stocks')} icon="💼">종목 관리</TabButton>
                </div>
            </div>

            {/* Content Switch */}
            {view === 'stocks' && (
                <div className="glass-panel" style={{ padding: '3rem' }}>
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>💼 관심 종목 관리</h2>

                    {/* Add Stock Form */}
                    <form onSubmit={handleStockSubmit} style={{
                        display: 'grid', gridTemplateColumns: 'minmax(150px, 1fr) minmax(300px, 2fr) auto', gap: '20px', alignItems: 'end', marginBottom: '3rem'
                    }}>
                        <div className="form-group">
                            <label>종목 코드 (Symbol)</label>
                            <input
                                placeholder="예: SOXL"
                                value={stockForm.code}
                                onChange={e => setStockForm({ ...stockForm, code: e.target.value.toUpperCase() })}
                                required
                                className="input-field-lg"
                            />
                        </div>
                        <div className="form-group">
                            <label>종목명 (Company Name)</label>
                            <input
                                placeholder="예: 반도체 3배 Bull ETF"
                                value={stockForm.name}
                                onChange={e => setStockForm({ ...stockForm, name: e.target.value })}
                                required
                                className="input-field-lg"
                            />
                        </div>
                        <button type="submit" className="btn-primary-lg">＋ 종목 등록</button>
                    </form>

                    {/* Stock List */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                        {stocks.map(s => (
                            <div key={s.code} style={{
                                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                            }}>
                                <div>
                                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'white' }}>{s.code}</div>
                                    <div style={{ color: 'var(--text-secondary)' }}>{s.name}</div>
                                </div>
                                <button onClick={() => deleteStock(s.code)} style={{ color: 'var(--accent-red)', background: 'rgba(248, 113, 113, 0.1)', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', cursor: 'pointer' }}>삭제</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {view === 'journal' && (
                <>
                    {/* Top Summary Card */}
                    <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.8) 100%)' }}>
                        <div>
                            <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Realized Profit</h3>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem' }}>
                                <div style={{ fontSize: '2.5rem', fontWeight: '800', color: getTotalProfit() >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                    ${getTotalProfit().toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </div>
                                <div style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                                    (약 {(getTotalProfit() * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원)
                                </div>
                            </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ color: 'var(--text-secondary)' }}>총 거래 기록</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{transactions.length} 건</div>
                        </div>
                    </div>

                    {/* Input Form */}
                    <div className="glass-panel" style={{ padding: '2.5rem', marginBottom: '3rem', border: '1px solid var(--accent-blue)', boxShadow: '0 0 20px rgba(59, 130, 246, 0.1)' }}>
                        <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {formData.id ? '✏️ 매매 기록 수정' : '✨ 새 매매 기록 추가'}
                        </h3>
                        <form onSubmit={handleTxSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '2rem' }}>

                            {/* Row 1 */}
                            <div className="form-group">
                                <label>종목 선택</label>
                                <select
                                    value={formData.ticker}
                                    onChange={e => setFormData({ ...formData, ticker: e.target.value })}
                                    required
                                    className="input-field"
                                    style={{ background: '#e2e8f0', color: 'black', fontWeight: 'bold' }}
                                >
                                    <option value="" style={{ color: 'gray' }}>-- 종목을 선택하세요 --</option>
                                    {stocks.map(s => <option key={s.code} value={s.code} style={{ color: 'black' }}>{s.name} ({s.code})</option>)}
                                </select>
                            </div>

                            <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                <label>매매 구분</label>
                                <div style={{ display: 'flex', gap: '0.5rem', height: '48px', alignItems: 'center' }}>
                                    <div onClick={() => setFormData({ ...formData, trade_type: 'BUY' })}
                                        style={{
                                            flex: 1, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold',
                                            background: formData.trade_type === 'BUY' ? 'var(--accent-red)' : 'rgba(255,255,255,0.05)',
                                            color: formData.trade_type === 'BUY' ? 'white' : 'var(--text-secondary)',
                                            border: formData.trade_type === 'BUY' ? 'none' : '1px solid rgba(255,255,255,0.1)'
                                        }}>
                                        📈 매수 (Buy)
                                    </div>
                                    <div onClick={() => setFormData({ ...formData, trade_type: 'SELL' })}
                                        style={{
                                            flex: 1, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold',
                                            background: formData.trade_type === 'SELL' ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)',
                                            color: formData.trade_type === 'SELL' ? 'white' : 'var(--text-secondary)',
                                            border: formData.trade_type === 'SELL' ? 'none' : '1px solid rgba(255,255,255,0.1)'
                                        }}>
                                        📉 매도 (Sell)
                                    </div>
                                </div>
                            </div>

                            <div className="form-group">
                                <label>거래 일시</label>
                                <input type="datetime-local" value={formData.trade_date} onChange={e => setFormData({ ...formData, trade_date: e.target.value })} required className="input-field" style={{ height: '48px', background: 'rgba(0,0,0,0.2)', color: 'white' }} />
                            </div>

                            {/* Row 2 */}
                            <div className="form-group">
                                <label>가 격 ($)</label>
                                <input type="number" placeholder="0.00" step="0.01" value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })} required className="input-field" style={{ height: '48px' }} />
                            </div>

                            <div className="form-group">
                                <label>수 량</label>
                                <input type="number" placeholder="0" value={formData.qty} onChange={e => setFormData({ ...formData, qty: e.target.value })} required className="input-field" style={{ height: '48px' }} />
                            </div>

                            <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                <label>메 모 (선택)</label>
                                <input placeholder="매매 사유나 특이사항 입력" value={formData.memo} onChange={e => setFormData({ ...formData, memo: e.target.value })} className="input-field" style={{ height: '48px' }} />
                            </div>

                            {/* Submit Button */}
                            <button type="submit" className="btn-submit" style={{ gridColumn: 'span 4' }}>
                                {formData.id ? '수정 내용 저장하기' : '기록 저장하기'}
                            </button>

                            {formData.id && (
                                <button type="button" onClick={() => setFormData({ id: null, ticker: '', trade_type: 'BUY', qty: '', price: '', trade_date: '', memo: '' })} style={{ gridColumn: 'span 4', padding: '0.8rem', background: 'transparent', border: '1px solid var(--text-secondary)', color: 'var(--text-secondary)', borderRadius: '8px', cursor: 'pointer' }}>
                                    취소하고 입력창 비우기
                                </button>
                            )}

                        </form>
                    </div>

                    {/* Chart Section */}
                    {stats.length > 0 && (
                        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', height: '400px' }}>
                            <h3 style={{ marginBottom: '1rem' }}>📊 수익률 차트 (FIFO 실현손익)</h3>
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
                    )}

                    {/* Transaction Lists - Grouped by Stock */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                        {sortedTickers.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>아직 거래 내역이 없습니다.</div>
                        ) : (
                            sortedTickers.map(ticker => {
                                const stockTxs = groupedTransactions[ticker];
                                const profit = getStockProfit(ticker);
                                const period = getPeriod(stockTxs);
                                const stockName = stockTxs[0].stock_name || ticker;

                                return (
                                    <div key={ticker} className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                                        {/* Stock Section Header */}
                                        <div style={{
                                            padding: '1.5rem 2rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)',
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem'
                                        }}>
                                            <div>
                                                <h3 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    {stockName} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 'normal' }}>({ticker})</span>
                                                </h3>
                                                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
                                                    거래 기간: {period}
                                                </div>
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>합산 실현손익</div>
                                                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: profit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                                    {profit > 0 ? '+' : ''}{profit.toLocaleString(undefined, { minimumFractionDigits: 2 })}$
                                                </div>
                                                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                                    ≈ {(profit * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                                                </div>
                                            </div>
                                        </div>

                                        {/* Table */}
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem' }}>
                                            <thead>
                                                <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                                                    <th style={{ padding: '1rem 2rem', textAlign: 'left' }}>날짜</th>
                                                    <th style={{ padding: '1rem', textAlign: 'center' }}>구분</th>
                                                    <th style={{ padding: '1rem', textAlign: 'right' }}>가격</th>
                                                    <th style={{ padding: '1rem', textAlign: 'right' }}>수량</th>
                                                    <th style={{ padding: '1rem', textAlign: 'right' }}>합계</th>
                                                    <th style={{ padding: '1rem', textAlign: 'left' }}>메모</th>
                                                    <th style={{ padding: '1rem 2rem', textAlign: 'right' }}>관리</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {stockTxs.map(tx => (
                                                    <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                        <td style={{ padding: '1rem 2rem' }}>{new Date(tx.trade_date).toLocaleString()}</td>
                                                        <td style={{ padding: '1rem', textAlign: 'center' }}>
                                                            <span style={{
                                                                padding: '4px 12px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold',
                                                                background: tx.trade_type === 'BUY' ? 'rgba(248, 113, 113, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                                                color: tx.trade_type === 'BUY' ? 'var(--accent-red)' : 'var(--accent-blue)'
                                                            }}>
                                                                {tx.trade_type === 'BUY' ? '매수' : '매도'}
                                                            </span>
                                                        </td>
                                                        <td style={{ padding: '1rem', textAlign: 'right' }}>${tx.price.toFixed(2)}</td>
                                                        <td style={{ padding: '1rem', textAlign: 'right' }}>{tx.qty}</td>
                                                        <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 'bold', color: 'rgba(255,255,255,0.7)' }}>
                                                            ${(tx.price * tx.qty).toLocaleString()}
                                                        </td>
                                                        <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{tx.memo}</td>
                                                        <td style={{ padding: '1rem 2rem', textAlign: 'right' }}>
                                                            <button onClick={() => editTx(tx)} className="btn-icon">✏️</button>
                                                            <button onClick={() => deleteTx(tx.id)} className="btn-icon" style={{ color: 'var(--accent-red)' }}>🗑️</button>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </>
            )}

            <style>{`
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                .form-group label {
                    font-size: 0.9rem;
                    color: var(--text-secondary);
                    margin-left: 2px;
                }
                .input-field {
                    background: rgba(0,0,0,0.2);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: white;
                    padding: 0.9rem;
                    border-radius: 8px;
                    width: 100%;
                    outline: none;
                    transition: all 0.2s;
                }
                .input-field-lg {
                    background: rgba(0,0,0,0.2);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: white;
                    padding: 1.2rem;
                    font-size: 1.1rem;
                    border-radius: 8px;
                    width: 100%;
                    outline: none;
                }
                .input-field:focus, .input-field-lg:focus {
                    border-color: var(--accent-blue);
                    background: rgba(59, 130, 246, 0.05);
                }
                .btn-submit {
                    padding: 1.2rem;
                    background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 1.1rem;
                    cursor: pointer;
                    transition: transform 0.1s;
                }
                .btn-submit:hover {
                    filter: brightness(1.1);
                    transform: translateY(-1px);
                }
                .btn-primary-lg {
                    padding: 1.2rem 2.5rem;
                    background: var(--accent-green);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 1.1rem;
                    cursor: pointer;
                    white-space: nowrap;
                }
                .btn-icon {
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 1.1rem;
                    padding: 0.3rem;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                .btn-icon:hover {
                    background: rgba(255,255,255,0.1);
                }
            `}</style>
        </div>
    );
};

const TabButton = ({ children, active, onClick, icon }) => (
    <button
        onClick={onClick}
        style={{
            background: active ? '#1e293b' : 'transparent',
            color: active ? 'white' : 'var(--text-secondary)',
            border: 'none',
            padding: '0.8rem 1.5rem',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: active ? 'bold' : 'normal',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.2s',
            boxShadow: active ? '0 2px 10px rgba(0,0,0,0.2)' : 'none'
        }}
    >
        <span>{icon}</span>
        {children}
    </button>
);

export default JournalPage;
