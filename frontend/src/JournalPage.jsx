import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const JournalPage = () => {
    // === State ===
    const [stocks, setStocks] = useState([]);
    const [transactions, setTransactions] = useState([]);
    const [stats, setStats] = useState([]);
    const [view, setView] = useState('journal'); // 'journal' | 'stocks'

    const [exchangeRate, setExchangeRate] = useState(1350);
    const [prices, setPrices] = useState({}); // {ticker: current_price}
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
        fetchCapital(); // Fetch Capital
    }, []);

    const fetchCapital = async () => {
        try {
            const res = await fetch('/api/capital');
            if (res.ok) {
                const d = await res.json();
                // Convert USD to KRW for display (approx) or wait for Exchange Rate?
                // Better to refetch after exchange rate is set. 
                // However, useEffect calls them in parallel.
                // Let's assume exchangeRate is updated or default 1350.
                setTotalCapitalKRW(Math.round(d.amount * 1350)); // Initial approx
            }
        } catch (e) { console.error(e); }
    };

    // Need to update capital display when exchange rate loads properly
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
            // Convert input KRW to USD
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

        // Type Conversion & Basic Validation
        const qty = parseInt(formData.qty);
        const price = parseFloat(formData.price);

        if (isNaN(qty) || isNaN(price)) {
            alert("수량과 가격을 정확히 입력해주세요.");
            return;
        }

        const payload = {
            ...formData,
            qty: qty,
            price: price
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
                id: null, ticker: formData.ticker,
                trade_type: 'BUY', qty: '', price: '',
                trade_date: getLocalISOString(), memo: ''
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

    // Calc Total Invested (Holdings)
    // Calc Total Invested & Unrealized (Live)
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

    // === Render ===
    return (
        <div className="container" style={{ paddingBottom: '6rem' }}>

            {/* Header Area */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1.5rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ margin: 0, fontWeight: 700, fontSize: 'clamp(1.5rem, 5vw, 2.2rem)' }}>매매 일지 & 수익률 분석</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>나만의 트레이딩 기록과 성과를 관리하세요.</p>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', background: 'rgba(255,255,255,0.05)', padding: '0.4rem', borderRadius: '10px' }}>
                    <TabButton active={view === 'journal'} onClick={() => setView('journal')} icon="📝">일지</TabButton>
                    <TabButton active={view === 'stocks'} onClick={() => setView('stocks')} icon="💼">종목</TabButton>
                </div>
            </div>

            {/* Content Switch */}
            {view === 'stocks' && (
                <div className="glass-panel" style={{ padding: '1.5rem' }}>
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>💼 관심 종목 관리</h2>

                    {/* Add Stock Form */}
                    <form onSubmit={handleStockSubmit} style={{
                        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', alignItems: 'end', marginBottom: '3rem'
                    }}>
                        <div className="form-group">
                            <label>종목 코드 (Symbol)</label>
                            <input
                                placeholder="예: SOXL"
                                value={stockForm.code}
                                onChange={e => setStockForm({ ...stockForm, code: e.target.value.toUpperCase() })}
                                required
                                className="input-field"
                            />
                        </div>
                        <div className="form-group">
                            <label>종목명 (Company Name)</label>
                            <input
                                placeholder="예: 반도체 3배 Bull ETF"
                                value={stockForm.name}
                                onChange={e => setStockForm({ ...stockForm, name: e.target.value })}
                                required
                                className="input-field"
                            />
                        </div>
                        <button type="submit" className="btn-submit">＋ 종목 등록</button>
                    </form>

                    {/* Stock List */}
                    <div className="grid-cards">
                        {stocks.map(s => (
                            <div key={s.code} className="glass-panel" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{s.code}</div>
                                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{s.name}</div>
                                </div>
                                <button onClick={() => deleteStock(s.code)} style={{ color: 'var(--accent-red)', background: 'rgba(248, 113, 113, 0.1)', border: 'none', padding: '0.5rem 0.75rem', borderRadius: '6px', cursor: 'pointer' }}>삭제</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {view === 'journal' && (
                <>
                    {/* Top Summary Card */}
                    <div className="glass-panel summary-grid" style={{ padding: '1.5rem', marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.8) 100%)' }}>
                        <div className="summary-item main">
                            <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Live Profit</h3>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
                                <div style={{ fontSize: '2rem', fontWeight: '800', color: totalUnrealized >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                    {totalUnrealized > 0 ? '+' : ''}${totalUnrealized.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </div>
                                <div style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                                    (약 {(totalUnrealized * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원)
                                </div>
                            </div>

                            {/* Total Capital Input */}
                            <div style={{ marginTop: '1rem', paddingTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <label style={{ fontSize: '0.85rem', color: '#ccc' }}>💰 총 자산 (KRW):</label>
                                <input
                                    type="number"
                                    className="input-field"
                                    style={{ width: '120px', height: '32px', textAlign: 'right', fontWeight: 'bold', color: 'var(--accent-gold)', padding: '0 0.5rem' }}
                                    value={totalCapitalKRW}
                                    onChange={(e) => setTotalCapitalKRW(e.target.value)}
                                    onBlur={(e) => saveCapital(e.target.value)}
                                    placeholder="원화 입력"
                                />
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    (Rate: {exchangeRate})
                                </span>
                                {capitalLoading && <span style={{ fontSize: '0.8rem' }}>💾</span>}
                            </div>
                        </div>
                        <div className="summary-item">
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Invested</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>${totalInvested.toLocaleString()}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                ≈ {(totalInvested * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                            </div>
                        </div>
                        <div className="summary-item">
                            <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Transactions</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{transactions.length} 건</div>
                        </div>
                    </div>

                    {/* Input Form */}
                    <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '3rem', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                        <h3 style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {formData.id ? '✏️ 매매 기록 수정' : '✨ 새 매매 기록 추가'}
                        </h3>
                        <form onSubmit={handleTxSubmit} className="journal-form-grid">

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
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button type="button" onClick={() => setFormData({ ...formData, trade_type: 'BUY' })}
                                        style={{
                                            flex: 1, height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold',
                                            background: formData.trade_type === 'BUY' ? 'var(--accent-red)' : 'rgba(255,255,255,0.05)',
                                            color: formData.trade_type === 'BUY' ? 'white' : 'var(--text-secondary)',
                                            border: formData.trade_type === 'BUY' ? 'none' : '1px solid rgba(255,255,255,0.1)'
                                        }}>
                                        📈 매수 (Buy)
                                    </button>
                                    <button type="button" onClick={() => setFormData({ ...formData, trade_type: 'SELL' })}
                                        style={{
                                            flex: 1, height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold',
                                            background: formData.trade_type === 'SELL' ? 'var(--accent-blue)' : 'rgba(255,255,255,0.05)',
                                            color: formData.trade_type === 'SELL' ? 'white' : 'var(--text-secondary)',
                                            border: formData.trade_type === 'SELL' ? 'none' : '1px solid rgba(255,255,255,0.1)'
                                        }}>
                                        📉 매도 (Sell)
                                    </button>
                                </div>
                            </div>

                            <div className="form-group">
                                <label>거래 일시</label>
                                <input type="datetime-local" value={formData.trade_date} onChange={e => setFormData({ ...formData, trade_date: e.target.value })} required className="input-field" style={{ background: 'rgba(0,0,0,0.2)', color: 'white' }} />
                            </div>

                            {/* Row 2 */}
                            <div className="form-group">
                                <label>가 격 ($)</label>
                                <input type="number" placeholder="0.00" step="0.01" value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })} required className="input-field" />
                            </div>

                            <div className="form-group">
                                <label>수 량</label>
                                <input type="number" placeholder="0" value={formData.qty} onChange={e => setFormData({ ...formData, qty: e.target.value })} required className="input-field" />
                            </div>

                            <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                <label>메 모 (선택)</label>
                                <input placeholder="매매 사유나 특이사항 입력" value={formData.memo} onChange={e => setFormData({ ...formData, memo: e.target.value })} className="input-field" />
                            </div>

                            {/* Submit Button */}
                            <button type="submit" className="btn-submit" style={{ gridColumn: '1 / -1' }}>
                                {formData.id ? '수정 내용 저장하기' : '기록 저장하기'}
                            </button>

                            {formData.id && (
                                <button type="button" onClick={() => setFormData({ id: null, ticker: '', trade_type: 'BUY', qty: '', price: '', trade_date: '', memo: '' })} style={{ gridColumn: '1 / -1', padding: '0.8rem', background: 'transparent', border: '1px solid var(--text-secondary)', color: 'var(--text-secondary)', borderRadius: '8px', cursor: 'pointer' }}>
                                    취소하고 입력창 비우기
                                </button>
                            )}

                        </form>
                    </div>

                    {/* Chart Section */}
                    {stats.length > 0 && (
                        <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '3rem', height: '350px' }}>
                            <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>📊 수익률 차트 (FIFO 실현손익)</h3>
                            <ResponsiveContainer width="100%" height="80%">
                                <BarChart data={stats}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fontSize: 10 }} tickFormatter={(val) => new Date(val).toLocaleDateString()} />
                                    <YAxis stroke="var(--text-secondary)" tick={{ fontSize: 10 }} />
                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid var(--glass-border)', fontSize: '12px' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                                    <Bar dataKey="profit" name="실현손익($)">
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
                                const profit = getStockProfit(ticker); // Realized
                                const period = getPeriod(stockTxs);
                                const stockName = stockTxs[0].stock_name || ticker;

                                // --- Calc Live Holdings (FIFO) ---
                                let netQty = 0;
                                let costBasis = 0;
                                const queue = [];
                                // Sort by date ascending for calc
                                [...stockTxs].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date)).forEach(tx => {
                                    if (tx.trade_type === 'BUY') {
                                        queue.push({ price: tx.price, qty: tx.qty });
                                    } else {
                                        let sellQty = tx.qty;
                                        while (sellQty > 0 && queue.length > 0) {
                                            let batch = queue[0];
                                            if (batch.qty > sellQty) {
                                                batch.qty -= sellQty;
                                                sellQty = 0; // Filled
                                            } else {
                                                sellQty -= batch.qty;
                                                queue.shift(); // Batch used up
                                            }
                                        }
                                    }
                                });
                                netQty = queue.reduce((acc, q) => acc + q.qty, 0);
                                costBasis = queue.reduce((acc, q) => acc + (q.price * q.qty), 0);

                                const curPrice = prices[ticker];
                                const evalValue = curPrice ? netQty * curPrice : 0;
                                const unrealizedProfit = evalValue - costBasis;
                                const unrealizedRate = costBasis > 0 ? (unrealizedProfit / costBasis) * 100 : 0;
                                // ----------------------------------

                                return (
                                    <div key={ticker} className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                                        {/* Stock Section Header */}
                                        <div style={{
                                            padding: '1.25rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)',
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem'
                                        }}>
                                            <div>
                                                <h3 style={{ fontSize: '1.25rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                    {stockName} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 'normal' }}>({ticker})</span>
                                                </h3>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.3rem' }}>
                                                    거래 기간: {period}
                                                </div>
                                            </div>
                                            <div style={{ textAlign: 'right', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                                                {/* Live Holdings Info */}
                                                {netQty > 0 && (
                                                    <div style={{ textAlign: 'right', paddingRight: '1.5rem', borderRight: '1px solid rgba(255,255,255,0.1)' }}>
                                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>보유 현황 (Live)</div>
                                                        <div style={{ fontSize: '0.8rem', marginTop: '0.2rem', color: '#ccc' }}>
                                                            {netQty}주 ({curPrice ? `$${curPrice}` : '-'})
                                                        </div>
                                                        <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: unrealizedProfit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                                            평가: {(evalValue * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                                                        </div>
                                                        <div style={{ fontSize: '0.8rem', color: unrealizedProfit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                                            ({unrealizedRate.toFixed(2)}%)
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Realized Profit Info */}
                                                <div style={{ textAlign: 'right' }}>
                                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>합산 실현손익</div>
                                                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: profit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                                        {profit > 0 ? '+' : ''}{profit.toLocaleString(undefined, { minimumFractionDigits: 2 })}$
                                                    </div>
                                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                        ≈ {(profit * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Table */}
                                        <div className="table-container">
                                            <table style={{ minWidth: '800px', width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                                                <thead>
                                                    <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                                                        <th style={{ padding: '0.8rem 1.25rem', textAlign: 'left' }}>날짜</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'center' }}>구분</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>가격</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>현재가</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>수량</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>예상손익 (KRW)</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'right' }}>합계</th>
                                                        <th style={{ padding: '0.8rem', textAlign: 'left' }}>메모</th>
                                                        <th style={{ padding: '0.8rem 1.25rem', textAlign: 'right' }}>관리</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {stockTxs.map(tx => (
                                                        <tr key={tx.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                            <td style={{ padding: '0.8rem 1.25rem' }}>{new Date(tx.trade_date).toLocaleDateString()}</td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                                <span style={{
                                                                    padding: '3px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold',
                                                                    background: tx.trade_type === 'BUY' ? 'rgba(248, 113, 113, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                                                    color: tx.trade_type === 'BUY' ? 'var(--accent-red)' : 'var(--accent-blue)'
                                                                }}>
                                                                    {tx.trade_type === 'BUY' ? '매수' : '매도'}
                                                                </span>
                                                            </td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>${tx.price.toFixed(2)}</td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'right', color: '#aaa' }}>
                                                                {prices[ticker] ? `$${prices[ticker]}` : '-'}
                                                            </td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>{tx.qty}</td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'right' }}>
                                                                {tx.trade_type === 'BUY' && prices[ticker] ? (
                                                                    <div>
                                                                        <div style={{ fontSize: '0.8rem', color: (prices[ticker] - tx.price) >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                                                                            {(((prices[ticker] - tx.price) / tx.price) * 100).toFixed(2)}%
                                                                        </div>
                                                                        <div style={{ fontSize: '0.7rem', color: '#aaa' }}>
                                                                            {((prices[ticker] - tx.price) * tx.qty * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                                                                        </div>
                                                                    </div>
                                                                ) : '-'}
                                                            </td>
                                                            <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: 'bold', color: 'rgba(255,255,255,0.7)' }}>
                                                                ${(tx.price * tx.qty).toLocaleString()}
                                                            </td>
                                                            <td style={{ padding: '0.8rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{tx.memo}</td>
                                                            <td style={{ padding: '0.8rem 1.25rem', textAlign: 'right' }}>
                                                                <button onClick={() => editTx(tx)} className="btn-icon">✏️</button>
                                                                <button onClick={() => deleteTx(tx.id)} className="btn-icon" style={{ color: 'var(--accent-red)' }}>🗑️</button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </>
            )}

            <style>{`
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1rem; /* Add horizontal padding for smaller screens */
                    font-family: 'Inter', sans-serif;
                }
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
                    min-height: 44px; /* Ensure consistent height */
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
                    min-height: 44px; /* Ensure consistent height */
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

                /* New/Updated Styles */
                .grid-cards {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 1rem;
                }
                .summary-grid {
                    display: grid;
                    grid-template-columns: 2fr 1fr 1fr;
                    gap: 1.5rem;
                    align-items: center; /* Align items vertically */
                }
                .summary-item {
                    padding: 0.5rem 1rem; /* Add some padding */
                }
                .summary-item:not(:last-child) {
                    border-right: 1px solid rgba(255,255,255,0.1);
                }
                .summary-item.main {
                    padding-left: 0; /* Remove left padding for the main item */
                }
                .journal-form-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 1.25rem;
                }
                .table-container {
                    overflow-x: auto; /* Enable horizontal scrolling for tables */
                    -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
                }
                .table-container table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.9rem;
                }
                .table-container th, .table-container td {
                    padding: 0.8rem;
                    text-align: left;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    white-space: nowrap; /* Prevent text wrapping in table cells */
                }
                .table-container th {
                    background: rgba(0,0,0,0.2);
                    color: var(--text-secondary);
                    font-weight: normal;
                }
                .table-container td:first-child, .table-container th:first-child { padding-left: 1.25rem; }
                .table-container td:last-child, .table-container th:last-child { padding-right: 1.25rem; }


                @media (max-width: 768px) {
                    .summary-grid {
                        grid-template-columns: 1fr;
                        gap: 1rem;
                    }
                    .summary-item:not(:last-child) {
                        border-right: none; /* Remove border on smaller screens */
                        border-bottom: 1px solid rgba(255,255,255,0.1); /* Add bottom border */
                        padding-bottom: 1rem;
                        margin-bottom: 1rem;
                    }
                    .summary-item.main {
                        padding-left: 0.5rem; /* Add back some padding */
                    }
                    .journal-form-grid {
                        grid-template-columns: 1fr; /* Stack form fields on small screens */
                    }
                    .journal-form-grid > div[style*="gridColumn: span 2"] {
                        grid-column: auto !important; /* Reset span for smaller screens */
                    }
                    .journal-form-grid > button[style*="gridColumn: 1 / -1"] {
                        grid-column: auto !important; /* Reset span for smaller screens */
                    }
                    .table-container table {
                        font-size: 0.8rem; /* Smaller font for tables on small screens */
                    }
                    .table-container th, .table-container td {
                        padding: 0.6rem 0.8rem;
                    }
                    .table-container td:first-child, .table-container th:first-child { padding-left: 0.8rem; }
                    .table-container td:last-child, .table-container th:last-child { padding-right: 0.8rem; }
                }

                @media (max-width: 480px) {
                    .container {
                        padding: 0 0.5rem;
                    }
                    .glass-panel {
                        padding: 1rem !important;
                    }
                    h1 {
                        font-size: clamp(1.2rem, 8vw, 2rem) !important;
                    }
                    .summary-item .div {
                        font-size: 0.7rem !important;
                    }
                    .summary-item .div:first-child {
                        font-size: 1.5rem !important;
                    }
                    .btn-submit {
                        font-size: 1rem;
                        padding: 0.8rem;
                    }
                    .btn-icon {
                        font-size: 0.9rem;
                        padding: 0.2rem;
                    }
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
