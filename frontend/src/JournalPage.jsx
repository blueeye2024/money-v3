import React, { useState, useEffect } from 'react';
import axios from 'axios';

const JournalPage = () => {
    const [holdings, setHoldings] = useState([]);
    const [stocks, setStocks] = useState([]);
    const [exchangeRate, setExchangeRate] = useState(1444.5);
    const [totalCapitalKRW, setTotalCapitalKRW] = useState(14445000);
    const [capitalInput, setCapitalInput] = useState('14445000');
    const [showForm, setShowForm] = useState(false);
    const [showStockManager, setShowStockManager] = useState(false);
    const [loading, setLoading] = useState(true);
    const [stockForm, setStockForm] = useState({ code: '', name: '' });
    const [form, setForm] = useState({ ticker: '', qty: 1, price: '' });
    const [editingId, setEditingId] = useState(null); // Used as Ticker in editing mode
    const [updatingPrices, setUpdatingPrices] = useState(false);
    const [costRate, setCostRate] = useState(0.2);

    useEffect(() => {
        const savedCostRate = localStorage.getItem('costRate');
        if (savedCostRate) setCostRate(parseFloat(savedCostRate));
    }, []);

    const handleCostRateChange = (e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) {
            setCostRate(val);
            localStorage.setItem('costRate', val);
        } else {
            setCostRate('');
        }
    };

    useEffect(() => {
        fetchAll();
        const interval = setInterval(() => {
            console.log("Auto-refreshing holdings from DB...");
            fetchHoldings();
        }, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            await Promise.all([fetchHoldings(), fetchStocks(), fetchCapital()]);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const fetchHoldings = async () => {
        try {
            // API now returns merged holdings from managed_stocks
            // Structure: [{ticker, name, qty, avg_price, current_price, ...}, ...]
            const res = await axios.get('/api/transactions');
            const rawData = res.data || [];

            // Calculate derived metrics (Profit, Value, etc.)
            // We need Exchange Rate first, but it might be async. 
            // For now, use the state exchangeRate or fetch fresh if needed.
            // Actually, let's fetch report first to get exchange rate? 
            // Better: fetchHoldings waits for the basic data.
            // Let's assume exchangeRate is updated by another call or we update it here.

            // Note: fetchCurrentPrices was removed because get_holdings returns current_price!
            // But we still need Exchange Rate.
            const reportRes = await axios.get('/api/report');
            const rate = reportRes.data.market?.KRW?.value || 1444.5;
            setExchangeRate(rate);

            const processed = rawData.map(h => {
                const qty = h.qty || 0;
                const avgPrice = parseFloat(h.avg_price || 0);
                const curPrice = parseFloat(h.current_price || avgPrice); // Fallback to avg if 0

                const totalCost = qty * avgPrice;
                const currentValue = qty * curPrice;
                const profit = currentValue - totalCost - (currentValue * (costRate / 100)); // Apply cost
                const profitPct = totalCost > 0 ? (profit / totalCost) * 100 : 0;

                return {
                    ...h,
                    qty,
                    avgPrice,
                    currentPrice: curPrice,
                    totalCost,
                    currentValue,
                    currentValueKRW: currentValue * rate,
                    profit,
                    profitPct,
                    stockId: h.ticker // Use ticker as ID
                };
            });

            setHoldings(processed);
        } catch (e) { console.error(e); }
    };

    const fetchStocks = async () => {
        try {
            const res = await axios.get('/api/stocks');
            setStocks(res.data || []);
        } catch (e) { console.error(e); }
    };

    const fetchCapital = async () => {
        try {
            const res = await axios.get('/api/capital');
            const cap = res.data.amount || 14445000;
            setTotalCapitalKRW(cap);
            setCapitalInput(String(cap));
        } catch (e) { console.error(e); }
    };

    const saveCapital = async () => {
        try {
            const val = parseFloat(capitalInput) || 14445000;
            await axios.post('/api/capital', { amount: val });
            setTotalCapitalKRW(val);
            alert('총자산이 저장되었습니다.');
        } catch (e) { console.error(e); alert('저장 실패'); }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // trade_type determines add(+) or sub(-) in backend
            // Default to BUY (Add)
            const dataToSend = {
                ticker: form.ticker,
                trade_type: 'BUY',
                qty: parseInt(form.qty),
                price: parseFloat(form.price),
                trade_date: new Date().toISOString(), // Ignored by backend but required by API signature maybe?
                memo: ''
            };

            // Determine if SELL (Subtract) - We need a UI toggle for Buy/Sell or just use signs?
            // User asked for "Simplification". Let's assume standard Buy/Sell buttons in form?
            // I'll add a Trade Type selector to the form.
            if (form.trade_type === 'SELL') dataToSend.trade_type = 'SELL';

            await axios.post('/api/transactions', dataToSend);

            setForm({ ticker: '', qty: 1, price: '', trade_type: 'BUY' });
            setEditingId(null);
            setShowForm(false);
            await fetchHoldings();
        } catch (e) {
            console.error('저장 오류:', e);
            alert('저장 실패: ' + (e.response?.data?.detail || e.message));
        }
    };

    const handleEdit = (holding) => {
        setForm({
            ticker: holding.ticker,
            qty: 1, // Default to 1 for new trade 
            price: holding.currentPrice,
            trade_type: 'BUY'
        });
        setEditingId(holding.ticker); // Mark as editing this ticker
        setShowForm(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Delete entire holding? Or just reduce qty?
    // "Delete" usually means reset to 0.
    const handleDelete = async (ticker) => {
        if (!window.confirm('이 종목의 보유량을 0으로 초기화하시겠습니까?')) return;
        try {
            // We simulate a sell of all quantity
            // First find the holding
            const h = holdings.find(i => i.ticker === ticker);
            if (h) {
                await axios.post('/api/transactions', {
                    ticker: ticker,
                    trade_type: 'SELL',
                    qty: h.qty,
                    price: h.currentPrice, // Price doesn't matter for qty 0 but affects history if we kept it
                    trade_date: new Date().toISOString(),
                    memo: 'Reset'
                });
                fetchHoldings();
            }
        } catch (e) { alert('삭제 실패'); }
    };

    const handleUpdatePrices = async () => {
        setUpdatingPrices(true);
        try {
            const res = await axios.post('/api/stocks/update-prices');
            if (res.data.status === 'success') {
                alert('✅ 현재가 업데이트 완료!');
                await fetchHoldings();
            } else {
                alert('⚠️ 현재가 업데이트 실패: ' + (res.data.message || '알 수 없는 오류'));
            }
        } catch (e) {
            alert('❌ 현재가 업데이트 실패: ' + e.message);
        } finally {
            setUpdatingPrices(false);
        }
    };

    const handleAddStock = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/stocks', stockForm);
            setStockForm({ code: '', name: '' });
            fetchStocks();
        } catch (e) { alert('추가 실패'); }
    };

    const handleDeleteStock = async (code) => {
        if (!confirm(`${code} 종목을 삭제하시겠습니까?`)) return;
        try {
            await axios.delete(`/api/stocks/${code}`);
            fetchStocks();
        } catch (e) { alert('삭제 실패'); }
    };

    const totalValueUSD = holdings.reduce((sum, h) => sum + h.currentValue, 0);
    const totalValueKRW = totalValueUSD * exchangeRate;
    const totalCapitalUSD = totalCapitalKRW / exchangeRate;
    const totalProfit = holdings.reduce((sum, h) => sum + h.profit, 0);
    const totalInvested = holdings.reduce((sum, h) => sum + h.totalCost, 0);
    const totalProfitPct = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;

    // Calc weights
    const holdingsWithWeight = holdings.map(h => ({
        ...h,
        weight: totalValueUSD > 0 ? (h.currentValue / totalValueUSD) * 100 : 0
    }));

    const sortedHoldings = holdingsWithWeight.sort((a, b) => b.weight - a.weight);

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">Asset Management</h1>
                <p className="page-subtitle">투자 자산 통합 관리</p>
            </div>

            {/* Summary Cards */}
            <div className="summary-grid">
                <div className="glass-card card-purple">
                    <div className="card-label">총 자산 (Total Assets)</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '1rem' }}>
                        <input className="glass-input" type="number" value={capitalInput} onChange={(e) => setCapitalInput(e.target.value)} style={{ width: '180px' }} />
                        <span style={{ fontSize: '1.2rem', fontWeight: '600' }}>원</span>
                    </div>
                    <button className="glass-btn" style={{ width: '100%' }} onClick={saveCapital}>
                        저장
                    </button>
                    <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.7)', marginTop: '1rem' }}>
                        ≈ ${totalCapitalUSD.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                </div>

                <div className="glass-card card-blue">
                    <div className="card-label" style={{ color: '#1e40af' }}>평가 금액 (Current Value)</div>
                    <div className="card-value" style={{ color: '#1e3a8a' }}>
                        ${totalValueUSD.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                    <div style={{ fontSize: '1rem', color: '#3b82f6', marginBottom: '1.5rem' }}>
                        {totalValueKRW.toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                    </div>
                    <div style={{ borderTop: '1px solid rgba(59,130,246,0.2)', paddingTop: '1rem', marginTop: '1rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '500' }}>현금 비중</span>
                            <span style={{ fontSize: '1.1rem', color: '#1e3a8a', fontWeight: '700' }}>
                                {((totalCapitalUSD - totalValueUSD) / totalCapitalUSD * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                            ${(totalCapitalUSD - totalValueUSD).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            <span style={{ marginLeft: '0.5rem' }}>(
                                {((totalCapitalUSD - totalValueUSD) * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                                )</span>
                        </div>
                    </div>
                </div>

                <div className={`glass-card ${totalProfit >= 0 ? 'card-success' : 'card-danger'}`}>
                    <div className="card-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>평가 손익 (P&L)</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.8rem', background: 'rgba(0,0,0,0.1)', padding: '2px 6px', borderRadius: '6px' }}>
                            <span>비용</span>
                            <input
                                className="glass-input"
                                type="number"
                                value={costRate}
                                onChange={handleCostRateChange}
                                step="0.01"
                                style={{ width: '45px', padding: '2px', textAlign: 'right', fontSize: '0.9rem' }}
                            />
                            <span>%</span>
                        </div>
                    </div>
                    <div className="card-value">
                        {totalProfit >= 0 ? '+' : ''}${totalProfit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                    <div style={{ fontSize: '1rem', color: 'rgba(255,255,255,0.7)', marginBottom: '0.2rem' }}>
                        {(totalProfit * exchangeRate).toLocaleString(undefined, { maximumFractionDigits: 0 })}원
                    </div>
                    <div style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.9)', fontWeight: '600' }}>
                        {totalProfitPct >= 0 ? '+' : ''}{totalProfitPct.toFixed(2)}%
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="action-bar">
                <button className="btn-secondary" onClick={() => { setShowStockManager(!showStockManager); setShowForm(false); }}>
                    ⚙️ 종목 관리
                </button>
                <button className="btn-primary" onClick={() => { setShowForm(!showForm); setShowStockManager(false); }}>
                    + 보유 종목 추가
                </button>
            </div>

            {/* Stock Manager */}
            {showStockManager && (
                <div className="section-panel">
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1e3a8a' }}>종목 관리</h2>
                    <form onSubmit={handleAddStock} style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                        <input className="form-input" type="text" value={stockForm.code} onChange={(e) => setStockForm({ code: e.target.value.toUpperCase(), name: e.target.value.toUpperCase() })} placeholder="종목 코드 (예: SOXL)" required style={{ flex: 1 }} />
                        <input className="form-input" type="text" value={stockForm.name} readOnly placeholder="종목명 (티커와 동일)" style={{ flex: 1, background: '#e8e8ed', color: '#666' }} />
                        <button type="submit" className="btn-update" style={{ justifyContent: 'center' }}>추가</button>
                    </form>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '1rem' }}>
                        {stocks.map(stock => (
                            <div key={stock.code} style={{ background: '#f5f5f7', padding: '1rem', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#1d1d1f' }}>{stock.code}</div>
                                    <div style={{ fontSize: '0.85rem', color: '#8e8e93' }}>{stock.name}</div>
                                </div>
                                <button onClick={() => handleDeleteStock(stock.code)} style={{ background: 'transparent', border: 'none', color: '#ff3b30', cursor: 'pointer', fontSize: '1.2rem', padding: '0.25rem' }}>×</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Transaction Form */}
            {showForm && (
                <div className="section-panel" style={{ background: 'linear-gradient(135deg, #93c5fd 0%, #60a5fa 50%, #3b82f6 100%)' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1d1d1f' }}>{editingId ? '보유 수정 (Update)' : '보유 변경 (Update)'}</h2>
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>종목</label>
                                <select className="form-input" value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} required disabled={!!editingId}>
                                    <option value="">선택</option>
                                    {stocks.map(stock => (<option key={stock.code} value={stock.code}>{stock.code}</option>))}
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>구분</label>
                                <div style={{ display: 'flex', gap: '0.5rem', height: '42px' }}>
                                    <button type="button" onClick={() => setForm({ ...form, trade_type: 'BUY' })} style={{ flex: 1, borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: 'bold', background: form.trade_type === 'BUY' ? '#ef4444' : 'rgba(255,255,255,0.3)', color: form.trade_type === 'BUY' ? 'white' : '#1d1d1f' }}>
                                        매수 (Add)
                                    </button>
                                    <button type="button" onClick={() => setForm({ ...form, trade_type: 'SELL' })} style={{ flex: 1, borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: 'bold', background: form.trade_type === 'SELL' ? '#3b82f6' : 'rgba(255,255,255,0.3)', color: form.trade_type === 'SELL' ? 'white' : '#1d1d1f' }}>
                                        매도 (Sub)
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>수량</label>
                                <input className="form-input" type="number" value={form.qty} onChange={(e) => setForm({ ...form, qty: parseInt(e.target.value) || 1 })} min="1" required />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>단가 ($)</label>
                                <input className="form-input" type="number" step="0.0001" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button type="button" onClick={() => { setForm({ ticker: '', qty: 1, price: '', trade_type: 'BUY' }); setEditingId(null); setShowForm(false); }} className="btn-secondary" style={{ flex: 1, background: '#dbeafe', color: '#1e3a8a', border: 'none' }}>취소</button>
                            <button type="submit" className="btn-primary" style={{ flex: 1, background: '#2563eb' }}>저장</button>
                        </div>
                    </form>
                </div>
            )}

            {/* Holdings Table */}
            <div style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)' }}>
                <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(59,130,246,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0, color: '#1e3a8a' }}>보유 현황 (Holdings)</h2>
                    <button onClick={handleUpdatePrices} disabled={updatingPrices} className="btn-update" style={{ background: updatingPrices ? '#9ca3af' : '', cursor: updatingPrices ? 'not-allowed' : 'pointer' }}>
                        {updatingPrices ? '⏳ 업데이트 중...' : '🔄 시세 업데이트'}
                    </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>종목</th>
                                <th>평균가</th>
                                <th>수량</th>
                                <th>평가액</th>
                                <th>현재가</th>
                                <th>손익</th>
                                <th>비중</th>
                                <th>관리</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>로딩 중...</td></tr>
                            ) : sortedHoldings.length === 0 ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>보유 종목이 없습니다.</td></tr>
                            ) : (
                                sortedHoldings.map((h) => (
                                    <tr key={h.ticker}>
                                        <td>
                                            <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#1e3a8a', marginBottom: '0.25rem' }}>{h.ticker}</div>
                                            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{h.name}</div>
                                        </td>
                                        <td style={{ color: '#1e3a8a', fontWeight: '500' }}>${Number(h.avgPrice).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 4 })}</td>
                                        <td style={{ fontWeight: '700', color: '#1e3a8a' }}>{h.qty}</td>
                                        <td>
                                            <div style={{ fontSize: '1rem', fontWeight: '700', color: '#1e40af', marginBottom: '0.25rem' }}>${h.currentValue.toFixed(2)}</div>
                                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{Math.round(h.currentValueKRW).toLocaleString()}원</div>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '5px', justifyContent: 'flex-end', alignItems: 'center' }}>
                                                <div style={{ fontSize: '0.95rem', fontWeight: '600', color: h.isManualPrice ? '#f59e0b' : '#1e3a8a' }}>
                                                    ${Number(h.currentPrice).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 4 })}
                                                </div>
                                                {h.isManualPrice && (<span style={{ fontSize: '0.7rem', color: '#f59e0b' }} title="수동 입력값">✋</span>)}
                                            </div>
                                        </td>
                                        <td>
                                            <div style={{ fontSize: '1rem', fontWeight: '700', color: h.profit >= 0 ? '#10b981' : '#ef4444', marginBottom: '0.25rem' }}>
                                                {h.profit >= 0 ? '+' : ''}${h.profit.toFixed(2)}
                                            </div>
                                            <div style={{ fontSize: '0.85rem', color: h.profit >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                                                {h.profitPct >= 0 ? '+' : ''}{h.profitPct.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <span style={{ display: 'inline-block', padding: '0.35rem 0.75rem', background: 'rgba(59,130,246,0.2)', borderRadius: '8px', fontSize: '0.9rem', fontWeight: '700', color: '#1e3a8a' }}>
                                                {h.weight.toFixed(1)}%
                                            </span>
                                        </td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                {/* Edit: Trigger Add form with pre-filled price, just to modify state easier */}
                                                <button onClick={() => handleEdit(h)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(59,130,246,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af' }}>변경</button>
                                                <button onClick={() => handleDelete(h.ticker)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#dc2626' }}>초기화</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default JournalPage;
