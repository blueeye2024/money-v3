import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Sector } from 'recharts';

const JournalPage = () => {
    const [allHoldings, setAllHoldings] = useState([]); // Raw data
    const [stocks, setStocks] = useState([]);
    const [exchangeRate, setExchangeRate] = useState(1444.5);
    const [totalCapitalKRW, setTotalCapitalKRW] = useState(14445000);
    const [totalCapitalKRWInput, setTotalCapitalKRWInput] = useState('14,445,000'); // [Fixed] Add state for formatted input
    const [showForm, setShowForm] = useState(false);
    const [showStockManager, setShowStockManager] = useState(false);
    const [loading, setLoading] = useState(true);
    const [stockForm, setStockForm] = useState({ code: '', name: '', is_active: true });
    const [form, setForm] = useState({
        ticker: '', qty: 1, price: '', trade_type: 'BUY',
        category: '기타', group_name: '', is_holding: true,
        expected_sell_date: '', target_sell_price: '', strategy_memo: ''
    });
    const [editingId, setEditingId] = useState(null); // Used as Ticker in editing mode
    const [updatingPrices, setUpdatingPrices] = useState(false);
    const [costRate, setCostRate] = useState(0.2);
    const [activeIndexGroup, setActiveIndexGroup] = useState(null);
    const [activeIndexAsset, setActiveIndexAsset] = useState(null);
    const [showDashboard, setShowDashboard] = useState(true);
    const [activeTab, setActiveTab] = useState('HOLDING');

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
            // [OPTIMIZATION] Fast Initial Load
            // 1. Fetch fast data and render immediately
            await Promise.all([fetchHoldings(), fetchStocks(), fetchCapital()]);
            setLoading(false); // Hide spinner ASAP based on fast data

            // 2. Fetch slow data (Exchange Rate) in background
            fetchReportData();
        } catch (e) {
            console.error(e);
            setLoading(false);
        }
    };

    const fetchReportData = async () => {
        try {
            const res = await axios.get('/api/report');
            const rate = res.data.market?.KRW?.value;
            if (rate) {
                setExchangeRate(rate);
                // Refresh holdings with new rate if it changed significantly?
                // Or just re-fetch since it's cheap (0.01s)
                fetchHoldings(rate);
            }
        } catch (e) { console.error("Report fetch failed:", e); }
    };

    const fetchHoldings = async (rateOverride = null) => {
        try {
            const currentRate = rateOverride || exchangeRate;

            // [Modified] Fetch both Transactions (Stats) and Managed Stocks (Meta)
            const [txRes, managedRes] = await Promise.all([
                axios.get('/api/transactions'),
                axios.get('/api/managed-stocks')
            ]);

            const txData = txRes.data || [];
            const managedData = managedRes.data || [];

            // Map for quick lookup
            const managedMap = {};
            managedData.forEach(m => managedMap[m.ticker] = m);

            const txMap = {};
            txData.forEach(t => txMap[t.ticker] = t);

            // Union of tickers
            const allTickers = new Set([...Object.keys(managedMap), ...Object.keys(txMap)]);

            const processed = Array.from(allTickers).map(ticker => {
                const tx = txMap[ticker] || {};
                const meta = managedMap[ticker] || {};

                // Determine group and category (Meta priority)
                const group_name = meta.group_name || tx.group_name || '기타';
                const category = meta.category || tx.category || '기타';
                const strategy_memo = meta.strategy_memo || tx.strategy_memo || meta.memo || '';

                // Determine is_holding
                let isHolding = false;
                if (typeof meta.is_holding !== 'undefined') {
                    // Robust check for 1, '1', true
                    isHolding = meta.is_holding === 1 || meta.is_holding === '1' || meta.is_holding === true;
                } else if (typeof tx.is_holding !== 'undefined') {
                    isHolding = tx.is_holding === 1 || tx.is_holding === true;
                } else {
                    isHolding = (tx.qty || 0) > 0;
                }

                // Stats (Transactions priority for Qty/Price, fallback to Manual for Watchlist)
                let qty = tx.qty || 0;
                let avgPrice = parseFloat(tx.avg_price || 0);

                if (!qty && !isHolding && meta.manual_qty) {
                    // Watchlist Simulation
                    qty = meta.manual_qty;
                    avgPrice = parseFloat(meta.manual_price || 0);
                }

                const curPrice = parseFloat(tx.current_price || meta.current_price || avgPrice || 0);

                const totalCost = qty * avgPrice;
                const currentValue = qty * curPrice;
                const profit = currentValue - totalCost - (currentValue * (costRate / 100)); // Apply cost
                const profitPct = totalCost > 0 ? (profit / totalCost) * 100 : 0;

                return {
                    ...tx, ...meta, // Merge props
                    ticker: ticker,
                    name: meta.name || tx.name || ticker,
                    qty,
                    avgPrice,
                    currentPrice: curPrice,
                    totalCost,
                    currentValue,
                    currentValueKRW: currentValue * currentRate,
                    profit,
                    profitPct,
                    group_name,
                    category,
                    is_holding: isHolding,
                    target_sell_price: meta.target_sell_price || tx.target_sell_price,
                    expected_sell_date: meta.expected_sell_date || tx.expected_sell_date,
                    strategy_memo,
                    stockId: ticker
                };
            });

            setAllHoldings(processed);
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
            setTotalCapitalKRWInput(cap.toLocaleString()); // [Fixed] Sync Formatted Input
        } catch (e) { console.error(e); }
    };

    const handleCapitalChange = (e) => {
        // Allow digits and comma only
        const raw = e.target.value.replace(/[^0-9,]/g, '');
        setTotalCapitalKRWInput(raw);
    };

    const handleCapitalBlur = async () => {
        // Parse "100,000" -> 100000
        const raw = totalCapitalKRWInput.replace(/,/g, '');
        const num = parseInt(raw, 10);
        if (!isNaN(num)) {
            setTotalCapitalKRW(num);
            setTotalCapitalKRWInput(num.toLocaleString()); // Re-format
            try {
                // Save to Backend
                await axios.post('/api/capital', { amount: num });
                console.log("Capital saved:", num);
            } catch (e) { console.error("Save capital error:", e); }
        } else {
            // Revert if invalid
            setTotalCapitalKRWInput(totalCapitalKRW.toLocaleString());
        }
    };

    const saveCapital = async () => {
        try {
            const val = parseFloat(totalCapitalKRWInput.replace(/,/g, '')) || 0;
            await axios.post('/api/capital', { amount: val });
            setTotalCapitalKRW(val);
            alert('총자산이 저장되었습니다.');
        } catch (e) { console.error(e); alert('저장 실패'); }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // [Modified] Use PUT (Upsert) only. No Transaction creation from this modal.
            const dataToSend = {
                ticker: form.ticker,
                qty: 0, // Transaction Qty ignored
                avg_price: 0, // Transaction Price ignored
                group_name: form.group_name || '기타',
                category: form.category || '기타',
                is_holding: form.is_holding,
                target_sell_price: form.target_sell_price ? parseFloat(form.target_sell_price) : null,
                expected_sell_date: form.expected_sell_date || null,
                strategy_memo: form.strategy_memo || '',
                manual_qty: form.qty ? parseInt(form.qty) : 0,
                manual_price: form.price ? parseFloat(form.price) : 0
            };

            await axios.put(`/api/holdings/${form.ticker}`, dataToSend);

            // Refetch
            setForm({ ticker: '', qty: 0, price: 0, trade_type: 'BUY', group_name: '', category: '기타', is_holding: true, target_sell_price: '', expected_sell_date: '', strategy_memo: '' });
            setEditingId(null);
            setShowForm(false);
            fetchHoldings(exchangeRate);

        } catch (e) {
            console.error('저장 오류:', e);
            alert('저장 실패: ' + (e.response?.data?.detail || e.message));
        }
    };

    const handleEdit = (holding) => {
        setForm({
            ticker: holding.ticker,
            qty: holding.qty, // [FIX] Use existing Quantity
            price: holding.avgPrice, // [FIX] Use existing Average Price
            trade_type: 'RESET', // [FIX] Use RESET for corrections
            group_name: holding.group_name || '',
            category: holding.category || '',
            is_holding: holding.is_holding, // Boolean logic is handled in fetchHoldings
            target_sell_price: holding.target_sell_price || '',
            expected_sell_date: holding.expected_sell_date || '',
            strategy_memo: holding.strategy_memo || ''
        });
        setEditingId(holding.ticker);
        setShowForm(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Delete entire holding? Or just reduce qty?
    // "Delete" usually means reset to 0.
    // Delete holding (Reset to 0)
    const handleDelete = async (ticker) => {
        if (!window.confirm('정말 이 보유 종목을 삭제하시겠습니까? (수량 0 처리)')) return;
        try {
            const h = allHoldings.find(i => i.ticker === ticker);
            if (h) {
                // [Fixed] Delete from managed_stocks List (Preserves Master Data)
                await axios.delete(`/api/holdings/${ticker}`);

                // Optimistic Update: Remove from list
                setAllHoldings(prev => prev.filter(item => item.ticker !== ticker));

                // Also Refresh Background
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
            setStockForm({ code: '', name: '', is_active: true });
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

    const totalValueUSD = allHoldings.reduce((sum, h) => sum + h.currentValue, 0);
    const totalValueKRW = totalValueUSD * exchangeRate;
    const totalCapitalUSD = totalCapitalKRW / exchangeRate;
    const totalProfit = allHoldings.reduce((sum, h) => sum + h.profit, 0);
    const totalInvested = allHoldings.reduce((sum, h) => sum + h.totalCost, 0);
    const totalProfitPct = totalInvested > 0 ? (totalProfit / totalInvested) * 100 : 0;

    // Calc weights
    const holdingsWithWeight = allHoldings.map(h => ({
        ...h,
        weight: totalValueUSD > 0 ? (h.currentValue / totalValueUSD) * 100 : 0
    }));

    // Filter by tab
    // Filter by tab (Strict separation based on is_holding)
    const activeHoldings = holdingsWithWeight.filter(h => h.is_holding);
    const watchHoldings = holdingsWithWeight.filter(h => !h.is_holding);

    // Group by group_name
    const holdingsByGroup = useMemo(() => {
        const groups = {};
        activeHoldings.forEach(h => {
            const group = h.group_name || '기타';
            if (!groups[group]) groups[group] = [];
            groups[group].push(h);
        });
        return groups;
    }, [allHoldings]);

    const sortedHoldings = holdingsWithWeight.sort((a, b) => b.weight - a.weight);

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header">
                <h1 className="page-title">Asset Management</h1>
                <p className="page-subtitle">투자 자산 통합 관리</p>
            </div>

            {/* Summary Cards + Charts (toggleable) */}
            {showDashboard && (
                <>
                    {/* Summary Cards */}
                    <div className="summary-grid">
                        <div className="glass-card card-purple">
                            <div className="card-label">총 자산 (Total Assets)</div>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '1rem' }}>
                                <input
                                    className="glass-input"
                                    type="text"
                                    value={totalCapitalKRWInput}
                                    onChange={handleCapitalChange}
                                    onBlur={handleCapitalBlur}
                                    style={{ width: '180px', textAlign: 'right', fontWeight: 'bold' }}
                                />
                                <span style={{ fontSize: '1.2rem', fontWeight: '600' }}>원</span>
                            </div>
                            {/* Save button removed as onBlur handles it now, or keep it as backup */}
                            <button className="glass-btn" style={{ width: '100%' }} onClick={handleCapitalBlur}>
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

                    {/* [Ver 6.6] Pie Charts Section */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
                        {/* Chart 1: 그룹별 주식 비중 */}
                        <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.15), rgba(59,130,246,0.08))', border: '2px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '1.5rem' }}>
                            <h3 style={{ margin: '0 0 1rem 0', color: '#bfdbfe', fontSize: '1.1rem', fontWeight: '700' }}>그룹별 주식 비중</h3>
                            <div style={{ minHeight: '280px' }}>
                                <ResponsiveContainer width="100%" height={280}>
                                    <PieChart>
                                        <defs>
                                            <radialGradient id="grad1" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#93c5fd" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#2563eb" stopOpacity="0.85" />
                                            </radialGradient>
                                            <radialGradient id="grad2" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#6ee7b7" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#059669" stopOpacity="0.85" />
                                            </radialGradient>
                                            <radialGradient id="grad3" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#fcd34d" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#d97706" stopOpacity="0.85" />
                                            </radialGradient>
                                            <radialGradient id="grad4" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#f9a8d4" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#db2777" stopOpacity="0.85" />
                                            </radialGradient>
                                            <radialGradient id="grad5" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#c4b5fd" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.85" />
                                            </radialGradient>
                                        </defs>
                                        <Pie
                                            data={(() => {
                                                const groups = {};
                                                sortedHoldings.forEach(h => {
                                                    const g = h.group_name || '기타';
                                                    if (!groups[g]) groups[g] = 0;
                                                    groups[g] += h.currentValue;
                                                });
                                                const arr = Object.entries(groups).map(([name, value]) => ({ name, value }));
                                                const total = arr.reduce((s, d) => s + d.value, 0);
                                                return arr.map(d => ({ ...d, percentage: total > 0 ? (d.value / total * 100) : 0 }));
                                            })()}
                                            cx="50%" cy="50%"
                                            innerRadius={65} outerRadius={105}
                                            paddingAngle={5}
                                            dataKey="value"
                                            label={(entry) => entry.percentage > 5 ? `${entry.name}\n${entry.percentage.toFixed(0)}%` : ''}
                                            labelLine={false}
                                            activeIndex={activeIndexGroup}
                                            activeShape={(props) => {
                                                const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
                                                return (
                                                    <Sector
                                                        cx={cx} cy={cy}
                                                        innerRadius={innerRadius}
                                                        outerRadius={outerRadius + 8}
                                                        startAngle={startAngle}
                                                        endAngle={endAngle}
                                                        fill={fill}
                                                        style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.4))' }}
                                                    />
                                                );
                                            }}
                                            onMouseEnter={(_, index) => setActiveIndexGroup(index)}
                                            onMouseLeave={() => setActiveIndexGroup(null)}
                                            style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.2))' }}
                                        >
                                            {Object.keys(holdingsByGroup).map((_, index) => (
                                                <Cell key={`cell-${index}`} fill={`url(#grad${(index % 5) + 1})`} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            formatter={(val, name, props) => [`$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${props.payload.percentage.toFixed(1)}%)`, name]}
                                            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(59,130,246,0.5)', borderRadius: '8px', color: '#fff' }}
                                            labelStyle={{ color: '#e0e7ff' }}
                                            itemStyle={{ color: '#fff' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            {/* Neon Table Legend */}
                            <div style={{ marginTop: '1rem' }}>
                                <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.4)' }}>
                                            <th style={{ textAlign: 'left', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>그룹</th>
                                            <th style={{ textAlign: 'right', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>비율</th>
                                            <th style={{ textAlign: 'right', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>금액</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {(() => {
                                            const colors = ['#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa'];
                                            const groups = {};
                                            sortedHoldings.forEach(h => {
                                                const g = h.group_name || '기타';
                                                if (!groups[g]) groups[g] = 0;
                                                groups[g] += h.currentValue;
                                            });
                                            const total = Object.values(groups).reduce((s, v) => s + v, 0);
                                            return Object.entries(groups).map(([name, value], idx) => (
                                                <tr key={name} style={{ borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                                                    <td style={{ padding: '0.6rem 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: colors[idx % 5], boxShadow: `0 0 8px ${colors[idx % 5]}` }}></span>
                                                        <span style={{ color: '#e0e7ff', fontWeight: '600' }}>{name}</span>
                                                    </td>
                                                    <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', color: '#93c5fd', fontWeight: '700' }}>{(total > 0 ? value / total * 100 : 0).toFixed(1)}%</td>
                                                    <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', color: '#e0e7ff', fontWeight: '600' }}>${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                                </tr>
                                            ));
                                        })()}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {/* Chart 2: 전체 자산 구성 */}
                        <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.15), rgba(59,130,246,0.08))', border: '2px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '1.5rem' }}>
                            <h3 style={{ margin: '0 0 1rem 0', color: '#bfdbfe', fontSize: '1.1rem', fontWeight: '700' }}>전체 자산 구성</h3>
                            <div style={{ minHeight: '280px' }}>
                                <ResponsiveContainer width="100%" height={280}>
                                    <PieChart>
                                        <defs>
                                            <radialGradient id="grad_asset_1" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#93c5fd" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#2563eb" stopOpacity="0.85" />
                                            </radialGradient>
                                            <radialGradient id="grad_asset_2" cx="30%" cy="30%" r="70%">
                                                <stop offset="0%" stopColor="#e9d5ff" stopOpacity="1" />
                                                <stop offset="100%" stopColor="#9333ea" stopOpacity="0.85" />
                                            </radialGradient>
                                        </defs>
                                        <Pie
                                            data={[
                                                { name: '주식', value: totalValueUSD },
                                                { name: '현금', value: Math.max(0, totalCapitalUSD - totalValueUSD) }
                                            ]}
                                            cx="50%" cy="50%"
                                            innerRadius={65} outerRadius={105}
                                            paddingAngle={5}
                                            dataKey="value"
                                            label={(entry) => `${entry.name}\n${((entry.value / (totalValueUSD + Math.max(0, totalCapitalUSD - totalValueUSD))) * 100).toFixed(0)}%`}
                                            labelLine={false}
                                            activeIndex={activeIndexAsset}
                                            activeShape={(props) => {
                                                const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
                                                return (
                                                    <Sector
                                                        cx={cx} cy={cy}
                                                        innerRadius={innerRadius}
                                                        outerRadius={outerRadius + 8}
                                                        startAngle={startAngle}
                                                        endAngle={endAngle}
                                                        fill={fill}
                                                        style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.4))' }}
                                                    />
                                                );
                                            }}
                                            onMouseEnter={(_, index) => setActiveIndexAsset(index)}
                                            onMouseLeave={() => setActiveIndexAsset(null)}
                                            style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.2))' }}
                                        >
                                            <Cell fill="url(#grad_asset_1)" />
                                            <Cell fill="url(#grad_asset_2)" />
                                        </Pie>
                                        <Tooltip
                                            formatter={(val, name) => [`$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, name]}
                                            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(59,130,246,0.5)', borderRadius: '8px', color: '#fff' }}
                                            labelStyle={{ color: '#e0e7ff' }}
                                            itemStyle={{ color: '#fff' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                            {/* Neon Table Legend */}
                            <div style={{ marginTop: '1rem' }}>
                                <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.4)' }}>
                                            <th style={{ textAlign: 'left', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>자산 유형</th>
                                            <th style={{ textAlign: 'right', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>비율</th>
                                            <th style={{ textAlign: 'right', padding: '0.5rem', color: '#93c5fd', fontWeight: '700', fontSize: '0.75rem', textTransform: 'uppercase' }}>금액</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {[
                                            { name: '주식 (Stocks)', value: totalValueUSD, color: '#60a5fa', grad: 'grad_asset_1' },
                                            { name: '현금 (Cash)', value: Math.max(0, totalCapitalUSD - totalValueUSD), color: '#c084fc', grad: 'grad_asset_2' }
                                        ].map((item, idx) => {
                                            const total = totalValueUSD + Math.max(0, totalCapitalUSD - totalValueUSD);
                                            return (
                                                <tr key={item.name} style={{ borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                                                    <td style={{ padding: '0.6rem 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: item.color, boxShadow: `0 0 8px ${item.color}` }}></span>
                                                        <span style={{ color: '#e0e7ff', fontWeight: '600' }}>{item.name}</span>
                                                    </td>
                                                    <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', color: '#93c5fd', fontWeight: '700' }}>{(total > 0 ? item.value / total * 100 : 0).toFixed(1)}%</td>
                                                    <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', color: '#e0e7ff', fontWeight: '600' }}>${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </>
            )
            }

            {/* Tabs + Action Buttons Row (Refactored) */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem' }}>
                {/* Left: Underline Tabs */}
                <div style={{ display: 'flex', gap: '2rem' }}>
                    <button
                        onClick={() => setActiveTab('HOLDING')}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === 'HOLDING' ? '2px solid #1e3a8a' : '2px solid transparent',
                            color: activeTab === 'HOLDING' ? '#1e3a8a' : '#94a3b8',
                            fontWeight: '700',
                            fontSize: '1rem',
                            padding: '0.5rem 0.2rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        보유 현황
                    </button>
                    <button
                        onClick={() => setActiveTab('WATCH')}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === 'WATCH' ? '2px solid #166534' : '2px solid transparent',
                            color: activeTab === 'WATCH' ? '#166534' : '#94a3b8',
                            fontWeight: '700',
                            fontSize: '1rem',
                            padding: '0.5rem 0.2rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        관심 종목
                    </button>
                </div>

                {/* Right: Text Actions (No Icons, Just Text) */}
                <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
                    <button
                        onClick={() => { setShowStockManager(!showStockManager); setShowForm(false); }}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.9rem', fontWeight: '500' }}
                    >
                        종목관리
                    </button>
                    <button
                        onClick={() => { setShowForm(!showForm); setShowStockManager(false); }}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.9rem', fontWeight: '500' }}
                    >
                        종목추가
                    </button>
                    <button
                        onClick={handleUpdatePrices}
                        disabled={updatingPrices}
                        style={{ background: 'transparent', border: 'none', color: updatingPrices ? '#94a3b8' : '#64748b', cursor: updatingPrices ? 'not-allowed' : 'pointer', fontSize: '0.9rem', fontWeight: '500' }}
                    >
                        {updatingPrices ? '업데이트 중...' : '시세 업데이트'}
                    </button>
                    <button
                        onClick={() => setShowDashboard(!showDashboard)}
                        style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '0.9rem', fontWeight: '500' }}
                    >
                        {showDashboard ? '차트 숨기기' : '차트 보기'}
                    </button>
                </div>
            </div>

            {/* Stock Manager */}
            {
                showStockManager && (
                    <div className="section-panel">
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '1.5rem', color: '#1e3a8a' }}>종목 관리</h2>
                        <form onSubmit={handleAddStock} style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                            <div style={{ flex: 1, minWidth: '120px' }}>
                                <input className="form-input" type="text" value={stockForm.code} onChange={(e) => setStockForm({ ...stockForm, code: e.target.value.toUpperCase(), name: stockForm.name || e.target.value.toUpperCase() })} placeholder="종목 코드 (예: SOXL)" required style={{ width: '100%' }} />
                            </div>
                            <div style={{ flex: 1.5, minWidth: '150px' }}>
                                <input className="form-input" type="text" value={stockForm.name} onChange={(e) => setStockForm({ ...stockForm, name: e.target.value })} placeholder="종목명" style={{ width: '100%' }} />
                            </div>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', background: 'rgba(255,255,255,0.5)', padding: '0.5rem 1rem', borderRadius: '8px' }}>
                                <input type="checkbox" checked={stockForm.is_active !== false} onChange={(e) => setStockForm({ ...stockForm, is_active: e.target.checked })} />
                                <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#1d1d1f' }}>거래 중 (Active)</span>
                            </label>
                            <button type="submit" className="btn-update" style={{ justifyContent: 'center', minWidth: '80px' }}>{stockForm.code && stocks.find(s => s.code === stockForm.code) ? '수정' : '추가'}</button>
                        </form>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem' }}>
                            {stocks.map(stock => (
                                <div key={stock.code} style={{ background: stock.is_active ? '#f5f5f7' : '#e5e5ea', padding: '1rem', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: stock.is_active ? 1 : 0.7 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: stock.is_active ? '#34c759' : '#8e8e93' }}></div>
                                        <div>
                                            <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#1d1d1f' }}>{stock.code}</div>
                                            <div style={{ fontSize: '0.85rem', color: '#8e8e93' }}>{stock.name}</div>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        <button onClick={() => setStockForm({ code: stock.code, name: stock.name, is_active: stock.is_active })} style={{ background: 'transparent', border: 'none', color: '#007aff', cursor: 'pointer', fontSize: '0.9rem', fontWeight: '600' }}>수정</button>
                                        <button onClick={() => handleDeleteStock(stock.code)} style={{ background: 'transparent', border: 'none', color: '#ff3b30', cursor: 'pointer', fontSize: '1.2rem', padding: '0 0.25rem' }}>×</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )
            }

            {/* Transaction Form */}
            {/* Transaction Form (MODAL) */}
            {/* Stock Form Modal */}
            {
                showForm && (
                    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                        <div style={{ background: 'white', padding: '2rem', borderRadius: '16px', width: '90%', maxWidth: '500px', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                <h2 style={{ fontSize: '1.25rem', fontWeight: '800', color: '#1e293b', margin: 0 }}>
                                    {editingId ? '⚡ 종목 수정 (Edit)' : '🚀 종목 추가 (Add)'}
                                </h2>
                                <button onClick={() => { setShowForm(false); setEditingId(null); setForm(initialFormState); }} style={{ background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#64748b' }}>×</button>
                            </div>
                            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                {/* Core Info */}
                                {/* Row 1: Ticker & Status (Radio Style) */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '1rem', alignItems: 'end' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>종목 (Ticker)</label>
                                        {editingId ? (
                                            <input className="form-input" value={form.ticker} disabled style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #e2e8f0', background: '#f8fafc', fontWeight: '700', color: '#334155' }} />
                                        ) : (
                                            <div style={{ position: 'relative' }}>
                                                <input className="form-input" list="stock-options" value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value.toUpperCase() })} placeholder="예: AAPL" required style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '1rem', fontWeight: '700' }} />
                                                <datalist id="stock-options">
                                                    {stocks.map(stock => (<option key={stock.code} value={stock.code}>{stock.name}</option>))}
                                                </datalist>
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>관리 상태 (Status)</label>
                                        <div style={{ display: 'flex', gap: '0.5rem', background: '#f1f5f9', padding: '0.3rem', borderRadius: '10px', height: '42px', alignItems: 'center' }}>
                                            {/* Radio Option 1: Holdings */}
                                            <label style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', background: form.is_holding ? 'white' : 'transparent', boxShadow: form.is_holding ? '0 1px 2px rgba(0,0,0,0.1)' : 'none', color: form.is_holding ? '#1e3a8a' : '#94a3b8', fontWeight: '700', transition: 'all 0.2s' }}>
                                                <input type="radio" name="is_holding" checked={form.is_holding === true} onChange={() => setForm({ ...form, is_holding: true })} style={{ display: 'none' }} />
                                                <span style={{ fontSize: '0.9rem' }}>보유</span>
                                            </label>
                                            {/* Radio Option 2: Watchlist */}
                                            <label style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', cursor: 'pointer', background: !form.is_holding ? 'white' : 'transparent', boxShadow: !form.is_holding ? '0 1px 2px rgba(0,0,0,0.1)' : 'none', color: !form.is_holding ? '#166534' : '#94a3b8', fontWeight: '700', transition: 'all 0.2s' }}>
                                                <input type="radio" name="is_holding" checked={form.is_holding === false} onChange={() => setForm({ ...form, is_holding: false })} style={{ display: 'none' }} />
                                                <span style={{ fontSize: '0.9rem' }}>관심</span>
                                            </label>
                                        </div>
                                    </div>
                                </div>

                                {/* Row 2: Qty & Price */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>수량 (Qty)</label>
                                        <input type="number" value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} placeholder="0" style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.95rem' }} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>평단가 (Avg Price)</label>
                                        <input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="0.00" style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.95rem' }} />
                                    </div>
                                </div>

                                {/* Row 3: Group & Category */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>그룹 (Group)</label>
                                        <input list="group-options" type="text" value={form.group_name} onChange={(e) => setForm({ ...form, group_name: e.target.value })} placeholder="직접 입력 또는 선택" style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.9rem' }} />
                                        <datalist id="group-options">{Object.keys(holdingsByGroup).map(g => <option key={g} value={g} />)}</datalist>
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>분류 (Category)</label>
                                        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '0.9rem', backgroundColor: 'white' }}>
                                            {['전략', '핵심', '배당', '성장', '단기', '기타'].map(c => <option key={c} value={c}>{c}</option>)}
                                        </select>
                                    </div>
                                </div>

                                {/* Row 4: Target & Date */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>목표가 ($)</label>
                                        <input type="number" step="0.01" value={form.target_sell_price} onChange={(e) => setForm({ ...form, target_sell_price: e.target.value })} placeholder="Target Price" style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1' }} />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.8rem', color: '#64748b', fontWeight: '700' }}>매도 예정일</label>
                                        <input type="date" value={form.expected_sell_date} onChange={(e) => setForm({ ...form, expected_sell_date: e.target.value })} style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', fontFamily: 'inherit' }} />
                                    </div>
                                </div>

                                {/* Row 5: Memo */}
                                <div>
                                    <textarea value={form.strategy_memo} onChange={(e) => setForm({ ...form, strategy_memo: e.target.value })} placeholder="운용 전략 메모..." rows="6" style={{ width: '100%', padding: '0.7rem', borderRadius: '10px', border: '1px solid #cbd5e1', resize: 'vertical', fontFamily: 'inherit', fontSize: '0.9rem' }}></textarea>
                                </div>

                                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                    <button type="button" onClick={() => { setForm({ ticker: '', qty: 0, price: 0, trade_type: 'BUY', group_name: '', is_holding: true, category: '기타' }); setEditingId(null); setShowForm(false); }} style={{ flex: 1, background: '#f1f5f9', color: '#475569', border: 'none', padding: '1rem', borderRadius: '12px', fontSize: '1rem', fontWeight: '700', cursor: 'pointer' }}>취소</button>
                                    <button type="submit" style={{ flex: 2, background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)', color: 'white', border: 'none', padding: '1rem', borderRadius: '12px', fontSize: '1rem', fontWeight: '700', cursor: 'pointer', boxShadow: '0 4px 12px rgba(37,99,235,0.3)' }}>저장 (Save)</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}


            {/* Holdings Table */}
            <div style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)' }}>
                <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(59,130,246,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0, color: '#1e3a8a' }}>
                        {activeTab === 'HOLDING' ? '보유 현황 (Holdings)' : '관심 종목 (Watchlist)'}
                    </h2>
                    <button onClick={handleUpdatePrices} disabled={updatingPrices} className="btn-update" style={{ background: updatingPrices ? '#9ca3af' : '', cursor: updatingPrices ? 'not-allowed' : 'pointer' }}>
                        {updatingPrices ? '⏳ 업데이트 중...' : '🔄 시세 업데이트'}
                    </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', color: '#334155' }}>
                        <thead style={{
                            background: activeTab === 'WATCH' ? 'rgba(240, 253, 244, 0.95)' : 'rgba(255,255,255,0.6)',
                            backdropFilter: 'blur(8px)',
                            borderBottom: activeTab === 'WATCH' ? '2px solid #166534' : '2px solid rgba(59,130,246,0.2)'
                        }}>
                            <tr>
                                <th style={{ padding: '0.8rem', textAlign: 'left', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '80px' }}>종목</th>
                                <th style={{ padding: '0.8rem', textAlign: 'left', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '100px' }}>이름</th>
                                <th style={{ padding: '0.8rem', textAlign: 'center', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '70px' }}>분류</th>
                                <th style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '60px' }}>수량</th>
                                <th style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '80px' }}>평단</th>
                                <th style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '80px' }}>현재가</th>
                                <th style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '80px' }}>손익</th>
                                <th style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '100px' }}>평가액</th>
                                <th style={{ padding: '0.8rem', textAlign: 'center', color: '#64748b', fontSize: '0.8rem', fontWeight: '700', whiteSpace: 'nowrap', minWidth: '110px' }}>관리</th>
                            </tr>
                        </thead>
                        <tbody style={{ fontSize: '0.9rem', color: '#334155' }}>
                            {loading ? (
                                <tr><td colSpan="9" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>로딩 중...</td></tr>
                            ) : activeTab === 'HOLDING' && Object.keys(holdingsByGroup).length === 0 ? (
                                <tr><td colSpan="9" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>보유 종목이 없습니다.</td></tr>
                            ) : activeTab === 'WATCH' && watchHoldings.length === 0 ? (
                                <tr><td colSpan="9" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>관심 종목이 없습니다.</td></tr>
                            ) : (
                                <>
                                    {/* Holdings List */}
                                    {activeTab === 'HOLDING' && holdingsByGroup && Object.entries(holdingsByGroup).map(([groupName, groupStocks]) => (
                                        <React.Fragment key={groupName}>
                                            {/* Group Header - Same as before */}
                                            <tr style={{ background: '#eff6ff', borderTop: '2px solid #bfdbfe', borderBottom: '1px solid #dbeafe' }}>
                                                <td colSpan="9" style={{ padding: '0.6rem 1rem' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <span style={{ fontWeight: '800', color: '#1e40af', fontSize: '0.95rem' }}>📂 {groupName || '미분류'} ({groupStocks.length})</span>
                                                        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column' }}>
                                                            <span style={{ fontSize: '0.9rem', fontWeight: '800', color: '#1e3a8a' }}>${groupStocks.reduce((sum, s) => sum + (s.currentValue || 0), 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                                            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>₩{(groupStocks.reduce((sum, s) => sum + (s.currentValue || 0), 0) * (exchangeRate || 1400)).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                            {/* Stock Rows */}
                                            {groupStocks.map(stock => (
                                                <tr key={stock.ticker} style={{ borderBottom: '1px solid #f1f5f9', background: 'white' }}>
                                                    <td style={{ padding: '0.8rem', fontWeight: '700', color: '#0f172a' }}>{stock.ticker}</td>
                                                    <td style={{ padding: '0.8rem', color: '#64748b' }}>{stock.name_kr || stock.name}</td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                        <span style={{ padding: '0.2rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', background: stock.category === '전략' ? '#dbeafe' : '#f1f5f9', color: stock.category === '전략' ? '#1e40af' : '#64748b' }}>
                                                            {stock.category}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '600' }}>{stock.qty}</td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b' }}>${stock.avgPrice?.toLocaleString()}</td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '600' }}>${stock.currentPrice?.toLocaleString()}</td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '700', color: stock.profit >= 0 ? '#16a34a' : '#dc2626' }}>
                                                        {stock.profit >= 0 ? '+' : ''}{stock.profitPct.toFixed(1)}%
                                                    </td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '800', color: '#1e293b' }}>${stock.currentValue?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                                    <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                        <div style={{ display: 'flex', gap: '0.3rem', justifyContent: 'center' }}>
                                                            <button onClick={() => handleEdit(stock)} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', background: 'white', color: '#334155', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '600' }}>편집</button>
                                                            <button onClick={() => handleDelete(stock.ticker)} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', background: 'white', color: '#dc2626', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '600' }}>삭제</button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </React.Fragment>
                                    ))}

                                    {/* Watchlist List - Unified Style */}
                                    {activeTab === 'WATCH' && watchHoldings.map(stock => (
                                        <tr key={stock.ticker} style={{ borderBottom: '1px solid #f1f5f9', background: 'white' }}>
                                            <td style={{ padding: '0.8rem', fontWeight: '700', color: '#0f172a' }}>{stock.ticker}</td>
                                            <td style={{ padding: '0.8rem', color: '#64748b' }}>{stock.name_kr || stock.name}</td>
                                            <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                <span style={{ padding: '0.2rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: '600', background: stock.category === '전략' ? '#dbeafe' : '#f1f5f9', color: stock.category === '전략' ? '#1e40af' : '#64748b' }}>
                                                    {stock.category}
                                                </span>
                                            </td>
                                            <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '600' }}>{stock.qty > 0 ? stock.qty : '-'}</td>
                                            <td style={{ padding: '0.8rem', textAlign: 'right', color: '#64748b' }}>${stock.price > 0 ? stock.price?.toLocaleString() : '-'}</td>
                                            <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '600' }}>${stock.currentPrice?.toLocaleString()}</td>
                                            <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '700', color: '#64748b' }}>
                                                -
                                            </td>
                                            <td style={{ padding: '0.8rem', textAlign: 'right', fontWeight: '800', color: '#1e293b' }}>${stock.currentValue?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                            <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                <div style={{ display: 'flex', gap: '0.3rem', justifyContent: 'center' }}>
                                                    <button onClick={() => handleEdit(stock)} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', background: 'white', color: '#334155', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '600' }}>편집</button>
                                                    <button onClick={() => handleDelete(stock.ticker)} style={{ padding: '0.2rem 0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1', background: 'white', color: '#dc2626', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '600' }}>삭제</button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div >
    );
};

export default JournalPage;
