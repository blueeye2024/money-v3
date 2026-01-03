import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const TabButton = ({ active, onClick, children, icon }) => (
    <button
        onClick={onClick}
        style={{
            padding: '0.6rem 1.2rem',
            background: active ? 'var(--accent-blue)' : 'transparent',
            color: active ? 'white' : 'var(--text-secondary)',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 'bold',
            fontSize: '0.9rem',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
        }}
    >
        <span>{icon}</span> {children}
    </button>
);

const JournalPage = () => {
    // === State ===
    const [stocks, setStocks] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [stats, setStats] = useState([]);
    const [signalHistory, setSignalHistory] = useState([]); // Master Signal History
    const [view, setView] = useState('journal'); // 'journal' | 'stocks'

    const [exchangeRate, setExchangeRate] = useState(1350);
    const [prices, setPrices] = useState({}); // {ticker: current_price}
    const [marketRegime, setMarketRegime] = useState(null);
    const [totalCapitalKRW, setTotalCapitalKRW] = useState(0);  // Store in KRW
    const [capitalLoading, setCapitalLoading] = useState(false);

    // Form State (Journal)
    const getLocalISOString = () => {
        const now = new Date();
        const offset = now.getTimezoneOffset() * 60000;
        return (new Date(now - offset)).toISOString().slice(0, 16);
    };

    const [formData, setFormData] = useState({
        id: null,
        ticker: '',
        trade_type: 'BUY',
        qty: '',
        price: '',
        trade_date: getLocalISOString(),
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
        fetchCurrentPrices();
        fetchCapital();
        fetchSignalHistory();

        // Auto Refresh every 1 min for real-time signals
        const interval = setInterval(() => {
            fetchCurrentPrices();
            fetchExchangeRate();
            fetchSignalHistory();
        }, 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchSignalHistory = async () => {
        try {
            const res = await fetch('/api/signals?limit=10'); // Fetch last 10 signals
            if (res.ok) setSignalHistory(await res.json());
        } catch (e) { console.error(e); }
    };

    const fetchCapital = async () => {
        try {
            const res = await fetch('/api/capital');
            if (res.ok) {
                const d = await res.json();
                setTotalCapitalKRW(Math.round(d.amount * 1350));
            }
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        if (exchangeRate > 0) {
            const reloadCapital = async () => {
                const res = await fetch('/api/capital');
                if (res.ok) {
                    const d = await res.json();
                    setTotalCapitalKRW(Math.round(d.amount * exchangeRate));
                }
            };
            reloadCapital();
        }
    }, [exchangeRate]);

    const saveCapital = async (val) => {
        setCapitalLoading(true);
        try {
            const usdAmount = parseFloat(val) / exchangeRate;
            await fetch('/api/capital', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: usdAmount })
            });
        } catch (e) { console.error(e); }
        setCapitalLoading(false);
    };

    const fetchCurrentPrices = async () => {
        try {
            const res = await fetch('/api/report');
            if (res.ok) {
                const data = await res.json();
                setMarketRegime(data.market_regime);
                const priceMap = {};
                if (data.stocks) {
                    data.stocks.forEach(s => {
                        priceMap[s.ticker] = s.current_price;
                    });
                }
                setPrices(priceMap);
            }
        } catch (e) { console.error(e); }
    };

    const fetchExchangeRate = async () => {
        try {
            const res = await fetch('/api/exchange-rate');
            if (res.ok) {
                const data = await res.json();
                setExchangeRate(data.rate);
            }
        } catch (e) { console.error(e); }
    };

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
        }
    };

    const deleteStock = async (code) => {
        if (!confirm("정말 삭제하시겠습니까? 관련 매매 기록도 삭제될 수 있습니다.")) return;
        const res = await fetch(`/api/stocks/${code}`, { method: 'DELETE' });
        if (res.ok) fetchStocks();
    };

    const handleTxSubmit = async (e) => {
        e.preventDefault();
        const qty = parseInt(formData.qty);
        const price = parseFloat(formData.price);
        if (isNaN(qty) || isNaN(price)) return;

        const payload = { ...formData, qty, price };
        if (!formData.id) delete payload.id;

        const url = formData.id ? `/api/transactions/${formData.id}` : '/api/transactions';
        const method = formData.id ? 'PUT' : 'POST';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            setFormData({
                id: null, ticker: formData.ticker,
                trade_type: 'BUY', qty: '', price: '',
                trade_date: getLocalISOString(), memo: ''
            });
            fetchTransactions();
            fetchStats();
        }
    };

    const editTx = (tx) => {
        setFormData({
            id: tx.id, ticker: tx.ticker, trade_type: tx.trade_type,
            qty: tx.qty, price: tx.price, trade_date: tx.trade_date, memo: tx.memo
        });
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

    const getStockProfit = (ticker) => {
        return stats.filter(s => s.ticker === ticker).reduce((sum, item) => sum + item.profit, 0);
    };

    const groupedTransactions = transactions.reduce((acc, tx) => {
        if (!acc[tx.ticker]) acc[tx.ticker] = [];
        acc[tx.ticker].push(tx);
        return acc;
    }, {});

    const sortedTickers = Object.keys(groupedTransactions).sort();

    const { totalInvested, totalUnrealized } = useMemo(() => {
        if (!transactions || transactions.length === 0) return { totalInvested: 0, totalUnrealized: 0 };
        let invested = 0;
        let unrealized = 0;

        const grouped = transactions.reduce((acc, tx) => {
            if (!acc[tx.ticker]) acc[tx.ticker] = [];
            acc[tx.ticker].push(tx);
            return acc;
        }, {});

        Object.keys(grouped).forEach(ticker => {
            const txs = grouped[ticker];
            const queue = [];
            [...txs].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date)).forEach(tx => {
                if (tx.trade_type === 'BUY') queue.push({ price: tx.price, qty: tx.qty });
                else {
                    let sell = tx.qty;
                    while (sell > 0 && queue.length) {
                        let batch = queue[0];
                        if (batch.qty > sell) { batch.qty -= sell; sell = 0; }
                        else { sell -= batch.qty; queue.shift(); }
                    }
                }
            });

            const netQty = queue.reduce((acc, q) => acc + q.qty, 0);
            const cost = queue.reduce((acc, q) => acc + (q.price * q.qty), 0);
            const curPrice = prices[ticker] || 0;

            if (netQty > 0) {
                invested += cost;
                if (curPrice > 0) {
                    unrealized += ((netQty * curPrice) - cost);
                }
            }
        });
        return { totalInvested: invested, totalUnrealized: unrealized };
    }, [transactions, prices]);

    const getPeriod = (txList) => {
        if (!txList || txList.length === 0) return '-';
        const dates = txList.map(t => new Date(t.trade_date).getTime());
        const min = new Date(Math.min(...dates));
        const max = new Date(Math.max(...dates));
        return `${min.toLocaleDateString()} ~ ${max.toLocaleDateString()}`;
    };

    return (
        <div className="container" style={{ paddingBottom: '6rem' }}>

            {/* Header Area */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem', flexWrap: 'wrap', gap: '1.5rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ margin: 0, fontWeight: 700, fontSize: 'clamp(1.5rem, 5vw, 2.2rem)' }}>매매 일지 & 수익률 분석</h1>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem', marginTop: '1rem' }}>
                        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>나만의 트레이딩 기록과 성과를 관리하세요.</p>

                        {/* Current Regime (UPRO based) */}
                        {marketRegime?.details?.upro_status && (
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: '10px',
                                background: 'rgba(255,255,255,0.06)', padding: '6px 16px', borderRadius: '30px',
                                border: '1px solid rgba(255,255,255,0.1)', fontSize: '0.9rem',
                                boxShadow: '0 4px 10px rgba(0,0,0,0.2)'
                            }}>
                                <span style={{ color: '#aaa', fontWeight: 'bold' }}>CURRENT REGIME:</span>
                                <span style={{
                                    fontWeight: '900',
                                    color: marketRegime.details.upro_status.label === '상승장' ? '#f87171' : marketRegime.details.upro_status.label === '하락장' ? '#60a5fa' : '#ccc'
                                }}>
                                    {marketRegime.details.upro_status.label}
                                    ({marketRegime.details.upro_status.change_pct >= 0 ? '+' : ''}{marketRegime.details.upro_status.change_pct}%)
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', background: 'rgba(255,255,255,0.05)', padding: '0.4rem', borderRadius: '10px' }}>
                    <TabButton active={view === 'journal'} onClick={() => setView('journal')} icon="📝">일지</TabButton>
                    <TabButton active={view === 'stocks'} onClick={() => setView('stocks')} icon="💼">포트폴리오</TabButton>
                </div>
            </div>

            {
                view === 'stocks' && (
                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>💼 포트폴리오(관심 종목) 관리</h2>
                        <form onSubmit={handleStockSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', alignItems: 'end', marginBottom: '3rem' }}>
                            <div className="form-group"><label>종목 코드</label><input placeholder="예: SOXL" value={stockForm.code} onChange={e => setStockForm({ ...stockForm, code: e.target.value.toUpperCase() })} required className="input-field" /></div>
                            <div className="form-group"><label>종목명</label><input placeholder="예: 반도체 3배" value={stockForm.name} onChange={e => setStockForm({ ...stockForm, name: e.target.value })} required className="input-field" /></div>
                            <button type="submit" className="btn-submit">＋ 종목 등록</button>
                        </form>
                        <div className="grid-cards">
                            {stocks.map(s => (
                                <div key={s.code} className="glass-panel" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div><div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{s.code}</div><div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{s.name}</div></div>
                                    <button onClick={() => deleteStock(s.code)} style={{ color: 'var(--accent-red)', background: 'rgba(248, 113, 113, 0.1)', border: 'none', padding: '0.5rem 0.75rem', borderRadius: '6px', cursor: 'pointer' }}>삭제</button>
                                </div>
                            ))}
                        </div>
                    </div>
                )
            }

            {
                view === 'journal' && (
                    <>
                        <div className="glass-panel summary-grid" style={{ padding: '1.5rem', marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.8) 100%)' }}>
                            <div className="summary-item main">
                                <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Live Profit</h3>
                                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
                                    <div style={{ fontSize: '2rem', fontWeight: '800', color: totalUnrealized >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>{totalUnrealized > 0 ? '+' : ''}${totalUnrealized.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                                    <div style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 600 }}>(약 {(totalUnrealized * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원)</div>
                                </div>
                                <div style={{ marginTop: '1rem', paddingTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <label style={{ fontSize: '0.85rem', color: '#ccc' }}>💰 총 자산 (KRW):</label>
                                    <input type="number" className="input-field" style={{ width: '120px', height: '32px', textAlign: 'right', fontWeight: 'bold', color: 'var(--accent-gold)', padding: '0 0.5rem' }} value={totalCapitalKRW} onChange={(e) => setTotalCapitalKRW(e.target.value)} onBlur={(e) => saveCapital(e.target.value)} />
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>(Rate: {exchangeRate})</span>
                                    {capitalLoading && <span style={{ fontSize: '0.8rem' }}>💾</span>}
                                </div>
                            </div>
                            <div className="summary-item"><div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Invested</div><div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>${totalInvested.toLocaleString()}</div><div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>≈ {(totalInvested * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원</div></div>
                            <div className="summary-item"><div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Transactions</div><div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{transactions.length} 건</div></div>
                        </div>

                        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '3rem', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                            <h3 style={{ marginBottom: '1.25rem' }}>{formData.id ? '✏️ 매매 기록 수정' : '✨ 새 매매 기록 추가'}</h3>
                            <form onSubmit={handleTxSubmit} className="journal-form-grid">
                                <div className="form-group"><label>종목 선택</label><select value={formData.ticker} onChange={e => setFormData({ ...formData, ticker: e.target.value })} required className="input-field" style={{ fontWeight: 'bold' }}><option value="" style={{ color: 'black' }}>-- 선택 --</option>{stocks.map(s => <option key={s.code} value={s.code} style={{ color: 'black' }}>{s.name} ({s.code})</option>)}</select></div>
                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>매매 구분</label>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <button type="button" onClick={() => setFormData({ ...formData, trade_type: 'BUY' })} style={{ flex: 1, height: '44px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', background: formData.trade_type === 'BUY' ? 'var(--accent-red)' : 'rgba(255,255,255,0.05)', color: formData.trade_type === 'BUY' ? 'white' : '#888', border: '1px solid rgba(255,255,255,0.1)' }}>📈 매수</button>
                                        <button type="button" onClick={() => setFormData({ ...formData, trade_type: 'SELL' })} style={{ flex: 1, height: '44px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', background: formData.trade_type === 'SELL' ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)', color: formData.trade_type === 'SELL' ? 'white' : '#888', border: '1px solid rgba(255,255,255,0.1)' }}>📉 매도</button>
                                    </div>
                                </div>
                                <div className="form-group"><label>거래 일시</label><input type="datetime-local" value={formData.trade_date} onChange={e => setFormData({ ...formData, trade_date: e.target.value })} required className="input-field" /></div>
                                <div className="form-group"><label>가격 ($)</label><input type="number" step="0.01" value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })} required className="input-field" /></div>
                                <div className="form-group"><label>수량</label><input type="number" value={formData.qty} onChange={e => setFormData({ ...formData, qty: e.target.value })} required className="input-field" /></div>
                                <div className="form-group" style={{ gridColumn: 'span 2' }}><label>메모</label><input value={formData.memo} onChange={e => setFormData({ ...formData, memo: e.target.value })} className="input-field" /></div>
                                <button type="submit" className="btn-submit" style={{ gridColumn: '1 / -1' }}>{formData.id ? '수정 내용 저장' : '기록 저장'}</button>
                                {formData.id && <button type="button" onClick={() => setFormData({ id: null, ticker: '', trade_type: 'BUY', qty: '', price: '', trade_date: getLocalISOString(), memo: '' })} style={{ gridColumn: '1 / -1', padding: '0.8rem', background: 'transparent', border: '1px solid #888', color: '#888', borderRadius: '8px', cursor: 'pointer' }}>취소</button>}
                            </form>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            {sortedTickers.map(ticker => {
                                const stockTxs = groupedTransactions[ticker];
                                const profit = getStockProfit(ticker);
                                const period = getPeriod(stockTxs);
                                const stockName = stockTxs[0].stock_name || ticker;
                                return (
                                    <div key={ticker} className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                                        <div style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div><h3 style={{ fontSize: '1.25rem', margin: 0 }}>{stockName} <span style={{ fontSize: '0.9rem', color: '#888' }}>({ticker})</span></h3><div style={{ fontSize: '0.8rem', color: '#888' }}>기간: {period}</div></div>
                                            <div style={{ textAlign: 'right' }}><div style={{ fontSize: '0.8rem', color: '#888' }}>누적 실현손익</div><div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: profit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>{profit > 0 ? '+' : ''}{profit.toLocaleString()}$</div></div>
                                        </div>
                                        <div className="table-container">
                                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                                <thead><tr style={{ background: 'rgba(0,0,0,0.2)' }}><th style={{ padding: '0.8rem' }}>날짜</th><th style={{ padding: '0.8rem' }}>구분</th><th style={{ padding: '0.8rem', textAlign: 'right' }}>가격</th><th style={{ padding: '0.8rem', textAlign: 'right' }}>수량</th><th style={{ padding: '0.8rem', textAlign: 'right' }}>합계</th><th style={{ padding: '0.8rem' }}>메모</th><th style={{ padding: '0.8rem', textAlign: 'right' }}>관리</th></tr></thead>
                                                <tbody>
                                                    {stockTxs.map(tx => (
                                                        <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}><td style={{ padding: '0.8rem' }}>{new Date(tx.trade_date).toLocaleDateString()}</td><td style={{ textAlign: 'center' }}><span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold', background: tx.trade_type === 'BUY' ? 'rgba(248,113,113,0.15)' : 'rgba(59,130,246,0.15)', color: tx.trade_type === 'BUY' ? 'var(--accent-red)' : 'var(--accent-blue)' }}>{tx.trade_type === 'BUY' ? '매수' : '매도'}</span></td><td style={{ textAlign: 'right' }}>${tx.price.toFixed(2)}</td><td style={{ textAlign: 'right' }}>{tx.qty}</td><td style={{ textAlign: 'right' }}>${(tx.price * tx.qty).toLocaleString()}</td><td style={{ color: '#888' }}>{tx.memo}</td><td style={{ textAlign: 'right' }}><button onClick={() => editTx(tx)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>✏️</button><button onClick={() => deleteTx(tx.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent-red)' }}>🗑️</button></td></tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </>
                )
            }

            <style>{`
                .container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; font-family: 'Inter', sans-serif; }
                .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
                .input-field { background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 0.8rem; border-radius: 8px; outline: none; transition: all 0.2; min-height: 44px; }
                .btn-submit { padding: 1rem; background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
                .summary-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 1.5rem; }
                .table-container { overflow-x: auto; }
            `}</style>
        </div >
    );
};

export default JournalPage;
