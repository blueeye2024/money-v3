import React, { useState, useEffect } from 'react';
import axios from 'axios';

const JournalPage = () => {
    const [transactions, setTransactions] = useState([]);
    const [stocks, setStocks] = useState([]);
    const [currentPrices, setCurrentPrices] = useState({});
    const [exchangeRate, setExchangeRate] = useState(1444.5);
    const [totalCapitalKRW, setTotalCapitalKRW] = useState(14445000);
    const [capitalInput, setCapitalInput] = useState('14445000');
    const [showForm, setShowForm] = useState(false);
    const [showStockManager, setShowStockManager] = useState(false);
    const [showMemoPopup, setShowMemoPopup] = useState(false);
    const [selectedMemo, setSelectedMemo] = useState({ ticker: '', memo: '' });
    const [loading, setLoading] = useState(true);
    const [stockForm, setStockForm] = useState({ code: '', name: '' });
    const [form, setForm] = useState({ ticker: '', qty: 1, price: '', memo: '' });
    const [editingId, setEditingId] = useState(null);

    useEffect(() => { fetchAll(); }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            await Promise.all([fetchTransactions(), fetchStocks(), fetchCurrentPrices(), fetchCapital()]);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const fetchTransactions = async () => {
        try {
            const res = await axios.get('/api/transactions');
            setTransactions(res.data || []);
        } catch (e) { console.error(e); }
    };

    const fetchStocks = async () => {
        try {
            const res = await axios.get('/api/stocks');
            setStocks(res.data || []);
        } catch (e) { console.error(e); }
    };

    const fetchCurrentPrices = async () => {
        try {
            const res = await axios.get('/api/report');
            const priceMap = {};
            if (res.data.market_regime?.details) {
                const d = res.data.market_regime.details;
                if (d.soxl?.current_price) priceMap['SOXL'] = d.soxl.current_price;
                if (d.soxs?.current_price) priceMap['SOXS'] = d.soxs.current_price;
                if (d.upro?.current_price) priceMap['UPRO'] = d.upro.current_price;

                console.log('API 응답 details:', d); // 디버깅
                console.log('현재가 데이터:', priceMap); // 디버깅
            } else {
                console.log('market_regime.details가 없습니다:', res.data);
            }
            if (res.data.market?.KRW) setExchangeRate(res.data.market.KRW.value || 1444.5);
            setCurrentPrices(priceMap);
        } catch (e) {
            console.error('현재가 가져오기 실패:', e);
        }
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
        } catch (e) {
            console.error(e);
            alert('저장 실패');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // Add trade_date (current date in YYYY-MM-DD format)
            const today = new Date().toISOString().split('T')[0];
            // 무조건 BUY로 고정
            const dataToSend = { ...form, trade_type: 'BUY', trade_date: today };

            // 같은 종목이 있는지 확인
            const existingTx = transactions.find(tx => tx.ticker === form.ticker);

            if (existingTx && !editingId) {
                // 같은 종목이 있으면 경고 메시지 표시
                alert(`${form.ticker} 종목이 이미 등록되어 있습니다.\n수정 모드로 전환합니다.`);
                // 수정 모드로 전환
                setForm({
                    ticker: existingTx.ticker,
                    qty: existingTx.qty,
                    price: existingTx.price,
                    memo: existingTx.memo || ''
                });
                setEditingId(existingTx.id);
                return; // 저장하지 않고 종료
            } else if (editingId) {
                // 수정 모드
                await axios.put(`/api/transactions/${editingId}`, dataToSend);
            } else {
                // 새로 추가
                await axios.post('/api/transactions', dataToSend);
            }

            setForm({ ticker: '', qty: 1, price: '', memo: '' });
            setEditingId(null);
            setShowForm(false);
            await fetchTransactions();
            await fetchCurrentPrices(); // 현재가 재로드
        } catch (e) {
            console.error('저장 오류:', e);
            alert('저장 실패: ' + (e.response?.data?.detail || e.message));
        }
    };

    const handleEdit = (tx) => {
        setForm({ ticker: tx.ticker, qty: tx.qty, price: tx.price, memo: tx.memo || '' });
        setEditingId(tx.id);
        setShowForm(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleDelete = async (id) => {
        if (!window.confirm('삭제하시겠습니까?')) return;
        try {
            await axios.delete(`/api/transactions/${id}`);
            fetchTransactions();
        } catch (e) { alert('삭제 실패'); }
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

    const calculateHoldings = () => {
        const holdings = {};

        // 각 종목의 최신 거래만 사용 (누적이 아닌 단일 보유 현황)
        transactions.forEach(tx => {
            if (tx.trade_type === 'BUY') {
                holdings[tx.ticker] = {
                    qty: tx.qty,
                    avgPrice: tx.price,
                    totalCost: tx.qty * tx.price,
                    latestTrade: tx
                };
            }
        });

        Object.keys(holdings).forEach(ticker => {
            const h = holdings[ticker];
            if (h.qty > 0) {
                h.currentPrice = currentPrices[ticker] || h.avgPrice; // API 현재가 우선, 없으면 마지막 거래 가격
                h.currentValue = h.qty * h.currentPrice;
                h.currentValueKRW = h.currentValue * exchangeRate;
                h.profit = h.currentValue - h.totalCost;
                h.profitPct = (h.profit / h.totalCost) * 100;
                const stock = stocks.find(s => s.code === ticker);
                h.name = stock ? stock.name : ticker;
            } else {
                delete holdings[ticker];
            }
        });
        return holdings;
    };

    const holdings = calculateHoldings();
    const totalValueUSD = Object.values(holdings).reduce((sum, h) => sum + h.currentValue, 0);
    const totalValueKRW = totalValueUSD * exchangeRate;
    const totalCapitalUSD = totalCapitalKRW / exchangeRate;
    const totalProfit = totalValueUSD - totalCapitalUSD;
    const totalProfitPct = totalCapitalUSD > 0 ? (totalProfit / totalCapitalUSD) * 100 : 0;

    // 비중 계산 및 비중 높은 순으로 정렬
    Object.values(holdings).forEach(h => {
        h.weight = totalValueUSD > 0 ? (h.currentValue / totalValueUSD) * 100 : 0;
    });

    const sortedHoldings = Object.entries(holdings).sort((a, b) => b[1].weight - a[1].weight);

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
            {/* Header */}
            <div style={{ marginBottom: '3rem' }}>
                <h1 style={{ fontSize: '2.5rem', fontWeight: '700', margin: '0 0 0.5rem 0', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Portfolio
                </h1>
                <p style={{ fontSize: '1.1rem', color: '#8e8e93', margin: 0 }}>투자 포트폴리오 관리</p>
            </div>

            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
                <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', borderRadius: '20px', padding: '2rem', boxShadow: '0 10px 40px rgba(102, 126, 234, 0.3)', transition: 'transform 0.2s', cursor: 'pointer' }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                    <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.8)', marginBottom: '1rem', fontWeight: '500' }}>총 자산</div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '1rem' }}>
                        <input type="number" value={capitalInput} onChange={(e) => setCapitalInput(e.target.value)} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: 'white', padding: '0.5rem', borderRadius: '10px', fontSize: '1.8rem', fontWeight: '700', width: '180px', outline: 'none' }} />
                        <span style={{ fontSize: '1.2rem', color: 'white', fontWeight: '600' }}>원</span>
                    </div>
                    <button onClick={saveCapital} style={{ background: 'rgba(255,255,255,0.25)', backdropFilter: 'blur(10px)', border: 'none', color: 'white', padding: '0.75rem 1.5rem', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', width: '100%', transition: 'all 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.35)'} onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.25)'}>
                        저장
                    </button>
                    <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.7)', marginTop: '1rem' }}>
                        ≈ ${totalCapitalUSD.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                </div>

                <div style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%)', borderRadius: '20px', padding: '2rem', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)' }}>
                    <div style={{ fontSize: '0.9rem', color: '#1e40af', marginBottom: '1rem', fontWeight: '500' }}>평가 금액</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: '700', color: '#1e3a8a', marginBottom: '0.5rem' }}>
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

                <div style={{ background: totalProfit >= 0 ? 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' : 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)', borderRadius: '20px', padding: '2rem', boxShadow: totalProfit >= 0 ? '0 10px 40px rgba(17, 153, 142, 0.3)' : '0 10px 40px rgba(235, 51, 73, 0.3)' }}>
                    <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.8)', marginBottom: '1rem', fontWeight: '500' }}>평가 손익</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: '700', color: 'white', marginBottom: '0.5rem' }}>
                        {totalProfit >= 0 ? '+' : ''}${totalProfit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                    <div style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.9)', fontWeight: '600' }}>
                        {totalProfitPct >= 0 ? '+' : ''}{totalProfitPct.toFixed(2)}%
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
                <button onClick={() => { setShowStockManager(!showStockManager); setShowForm(false); }} style={{ background: showStockManager ? '#f5f5f7' : 'white', border: '1px solid #d2d2d7', color: '#1d1d1f', padding: '0.75rem 1.5rem', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', transition: 'all 0.2s', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }} onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)'} onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)'}>
                    ⚙️ 종목 관리
                </button>
                <button onClick={() => { setShowForm(!showForm); setShowStockManager(false); }} style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', border: 'none', color: 'white', padding: '0.75rem 1.5rem', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', transition: 'all 0.2s', boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)' }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'} onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                    + 보유 종목
                </button>
            </div>

            {/* Stock Manager */}
            {showStockManager && (
                <div style={{ background: 'linear-gradient(135deg, #bfdbfe 0%, #93c5fd 50%, #60a5fa 100%)', borderRadius: '20px', padding: '2rem', marginBottom: '2rem', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)', animation: 'slideDown 0.3s ease' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1e3a8a' }}>종목 관리</h2>
                    <form onSubmit={handleAddStock} style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                        <input type="text" value={stockForm.code} onChange={(e) => setStockForm({ ...stockForm, code: e.target.value.toUpperCase() })} placeholder="종목 코드" required style={{ flex: 1, padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', transition: 'all 0.2s' }} onFocus={(e) => e.currentTarget.style.background = '#e8e8ed'} onBlur={(e) => e.currentTarget.style.background = '#f5f5f7'} />
                        <input type="text" value={stockForm.name} onChange={(e) => setStockForm({ ...stockForm, name: e.target.value })} placeholder="종목명" required style={{ flex: 2, padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', transition: 'all 0.2s' }} onFocus={(e) => e.currentTarget.style.background = '#e8e8ed'} onBlur={(e) => e.currentTarget.style.background = '#f5f5f7'} />
                        <button type="submit" style={{ padding: '0.75rem 1.5rem', background: '#007aff', color: 'white', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem' }}>추가</button>
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
                <div style={{ background: 'linear-gradient(135deg, #93c5fd 0%, #60a5fa 50%, #3b82f6 100%)', borderRadius: '20px', padding: '2rem', marginBottom: '2rem', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)', animation: 'slideDown 0.3s ease' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1d1d1f' }}>{editingId ? '보유 수정' : '보유 추가'}</h2>
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>종목</label>
                                <select value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} required style={{ width: '100%', padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', color: '#1d1d1f', fontWeight: '500' }}>
                                    <option value="">선택</option>
                                    {stocks.map(stock => (<option key={stock.code} value={stock.code}>{stock.code} - {stock.name}</option>))}
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>수량</label>
                                <input type="number" value={form.qty} onChange={(e) => setForm({ ...form, qty: parseInt(e.target.value) || 1 })} min="1" required style={{ width: '100%', padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', color: '#1d1d1f', fontWeight: '500' }} />
                            </div>
                            <div>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>가격 ($)</label>
                                <input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required style={{ width: '100%', padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', color: '#1d1d1f', fontWeight: '500' }} />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: '#1d1d1f', fontWeight: '600' }}>매매 사유</label>
                            <textarea value={form.memo} onChange={(e) => setForm({ ...form, memo: e.target.value })} rows="3" placeholder="매매 사유를 입력하세요..." style={{ width: '100%', padding: '0.75rem 1rem', background: '#f5f5f7', border: 'none', borderRadius: '10px', fontSize: '0.95rem', outline: 'none', resize: 'vertical', color: '#1d1d1f', fontFamily: 'inherit' }} />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <button type="button" onClick={() => { setForm({ ticker: '', trade_type: 'BUY', qty: 1, price: '', memo: '' }); setEditingId(null); setShowForm(false); }} style={{ flex: 1, padding: '0.85rem', background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)', color: '#1e3a8a', border: 'none', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', transition: 'all 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'} onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}>취소</button>
                            <button type="submit" style={{ flex: 1, padding: '0.85rem', background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: 'white', border: 'none', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem', boxShadow: '0 4px 12px rgba(59,130,246,0.3)', transition: 'all 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'} onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>저장</button>
                        </div>
                    </form>
                </div>
            )}

            {/* Holdings Table */}
            <div style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)' }}>
                <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0, color: '#1e3a8a' }}>보유 현황</h2>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr style={{ background: 'rgba(59,130,246,0.15)', borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'left', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>종목</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>평균가</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>수량</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>평가액</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>현재가</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>손익</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'center', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>비중</th>
                                <th style={{ padding: '1rem 1.5rem', textAlign: 'right', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>관리</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>로딩 중...</td></tr>
                            ) : sortedHoldings.length === 0 ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>보유 종목이 없습니다.</td></tr>
                            ) : (
                                sortedHoldings.map(([ticker, h]) => (
                                    <tr key={ticker} style={{ borderBottom: '1px solid rgba(59,130,246,0.15)', transition: 'background 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(59,130,246,0.08)'} onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                                        <td style={{ padding: '1.25rem 1.5rem' }}>
                                            <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#1e3a8a', marginBottom: '0.25rem' }}>{ticker}</div>
                                            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{h.name}</div>
                                        </td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', fontSize: '0.95rem', color: '#1e3a8a', fontWeight: '500' }}>${h.avgPrice.toFixed(2)}</td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', fontSize: '1rem', color: '#1e3a8a', fontWeight: '700' }}>{h.qty}</td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                            <div style={{ fontSize: '1rem', fontWeight: '700', color: '#1e40af', marginBottom: '0.25rem' }}>${h.currentValue.toFixed(2)}</div>
                                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{h.currentValueKRW.toLocaleString(undefined, { maximumFractionDigits: 0 })}원</div>
                                        </td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', fontSize: '0.95rem', color: '#1e3a8a', fontWeight: '500' }}>${h.currentPrice.toFixed(2)}</td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                            <div style={{ fontSize: '1rem', fontWeight: '700', color: h.profit >= 0 ? '#10b981' : '#ef4444', marginBottom: '0.25rem' }}>
                                                {h.profit >= 0 ? '+' : ''}${h.profit.toFixed(2)}
                                            </div>
                                            <div style={{ fontSize: '0.85rem', color: h.profit >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                                                {h.profitPct >= 0 ? '+' : ''}{h.profitPct.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'center' }}>
                                            <span style={{ display: 'inline-block', padding: '0.35rem 0.75rem', background: 'rgba(59,130,246,0.2)', borderRadius: '8px', fontSize: '0.9rem', fontWeight: '700', color: '#1e3a8a' }}>
                                                {h.weight.toFixed(1)}%
                                            </span>
                                        </td>
                                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                <button onClick={() => { setSelectedMemo({ ticker, memo: h.latestTrade?.memo || '매매 사유 없음' }); setShowMemoPopup(true); }} style={{ padding: '0.5rem 0.75rem', background: 'rgba(59,130,246,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem' }}>📄</button>
                                                <button onClick={() => handleEdit(h.latestTrade)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(59,130,246,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af' }}>수정</button>
                                                <button onClick={() => handleDelete(h.latestTrade.id)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#dc2626' }}>삭제</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Memo Popup */}
            {showMemoPopup && (
                <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(10px)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000, animation: 'fadeIn 0.2s ease' }} onClick={() => setShowMemoPopup(false)}>
                    <div style={{ background: 'linear-gradient(135deg, #faf5ff 0%, #f5f3ff 50%, #ffffff 100%)', borderRadius: '20px', padding: '2.5rem', maxWidth: '600px', width: '90%', maxHeight: '80vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.3)', animation: 'slideUp 0.3s ease' }} onClick={(e) => e.stopPropagation()}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1d1d1f' }}>매매 사유 - {selectedMemo.ticker}</h2>
                        <div style={{ background: '#f5f5f7', padding: '1.5rem', borderRadius: '12px', lineHeight: '1.8', fontSize: '1rem', color: '#1d1d1f', whiteSpace: 'pre-wrap', minHeight: '100px' }}>
                            {selectedMemo.memo}
                        </div>
                        <button onClick={() => setShowMemoPopup(false)} style={{ marginTop: '1.5rem', width: '100%', padding: '0.85rem', background: '#007aff', color: 'white', border: 'none', borderRadius: '12px', cursor: 'pointer', fontWeight: '600', fontSize: '0.95rem' }}>닫기</button>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(30px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default JournalPage;
