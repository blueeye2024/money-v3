import React, { useState, useEffect } from 'react';

const SignalPage = () => {
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [stocks, setStocks] = useState([]);
    const [filters, setFilters] = useState({
        ticker: '',
        start_date: '',
        end_date: '',
        limit: 30
    });

    useEffect(() => {
        fetchStocks();
        fetchSignals();
    }, []);

    const fetchStocks = async () => {
        try {
            const res = await fetch('/api/stocks');
            if (res.ok) setStocks(await res.json());
        } catch (e) { console.error(e); }
    };

    const fetchSignals = async () => {
        setLoading(true);
        try {
            const query = new URLSearchParams(filters).toString();
            const res = await fetch(`/api/signals?${query}`);
            if (res.ok) {
                const data = await res.json();
                setSignals(data);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (e) => {
        const { name, value } = e.target;
        setFilters(prev => ({ ...prev, [name]: value }));
    };

    const applyFilters = (e) => {
        e.preventDefault();
        fetchSignals();
    };

    const resetFilters = () => {
        setFilters({
            ticker: '',
            start_date: '',
            end_date: '',
            limit: 30
        });
        // We need to wait for state update or use dummy
    };

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '4rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h1 className="text-gradient" style={{ fontSize: '2.2rem', margin: 0, fontWeight: 700 }}>실시간 신호 포착 내역</h1>
                <p style={{ color: 'var(--text-secondary)' }}>시스템이 자동으로 탐지한 매수/매도 신호 기록입니다.</p>
            </div>

            {/* Filters */}
            <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2.5rem' }}>
                <form onSubmit={applyFilters} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', alignItems: 'end' }}>
                    <div className="form-group">
                        <label>종목 필터</label>
                        <select name="ticker" value={filters.ticker} onChange={handleFilterChange} className="input-field" style={{ background: '#e2e8f0', color: 'black', fontWeight: 'bold' }}>
                            <option value="">모든 종목</option>
                            {stocks.map(s => <option key={s.code} value={s.code}>{s.name} ({s.code})</option>)}
                        </select>
                    </div>
                    <div className="form-group">
                        <label>시작일</label>
                        <input type="date" name="start_date" value={filters.start_date} onChange={handleFilterChange} className="input-field" />
                    </div>
                    <div className="form-group">
                        <label>종료일</label>
                        <input type="date" name="end_date" value={filters.end_date} onChange={handleFilterChange} className="input-field" />
                    </div>
                    <div className="form-group">
                        <label>표시 개수</label>
                        <select name="limit" value={filters.limit} onChange={handleFilterChange} className="input-field" style={{ background: '#e2e8f0', color: 'black', fontWeight: 'bold' }}>
                            <option value="30">최근 30개</option>
                            <option value="50">최근 50개</option>
                            <option value="100">최근 100개</option>
                            <option value="500">최근 500개</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button type="submit" className="btn-submit" style={{ flex: 2, padding: '0.8rem' }}>조회</button>
                        <button type="button" onClick={resetFilters} className="input-field" style={{ flex: 1, padding: '0.8rem', background: 'transparent' }}>초기화</button>
                    </div>
                </form>
            </div>

            {/* Signals Table */}
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '1.2rem 2rem', textAlign: 'left' }}>시간</th>
                            <th style={{ padding: '1.2rem', textAlign: 'left' }}>종목</th>
                            <th style={{ padding: '1.2rem', textAlign: 'center' }}>구분</th>
                            <th style={{ padding: '1.2rem', textAlign: 'right' }}>가격</th>
                            <th style={{ padding: '1.2rem 2rem', textAlign: 'left' }}>사유 / 상세 정보</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>데이터 로딩 중...</td></tr>
                        ) : signals.length === 0 ? (
                            <tr><td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>신호 내역이 없습니다.</td></tr>
                        ) : (
                            signals.map(sig => (
                                <tr key={sig.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '1.2rem 2rem', fontSize: '0.9rem' }}>
                                        {new Date(sig.signal_time).toLocaleString()}
                                    </td>
                                    <td style={{ padding: '1.2rem' }}>
                                        <div style={{ fontWeight: 'bold' }}>{sig.ticker}</div>
                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{sig.name}</div>
                                    </td>
                                    <td style={{ padding: '1.2rem', textAlign: 'center' }}>
                                        <span style={{
                                            padding: '4px 12px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 'bold',
                                            background: sig.signal_type === 'BUY' ? 'rgba(248, 113, 113, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                            color: sig.signal_type === 'BUY' ? 'var(--accent-red)' : 'var(--accent-blue)'
                                        }}>
                                            {sig.signal_type === 'BUY' ? '매수' : '매도'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1.2rem', textAlign: 'right', fontWeight: 'bold' }}>
                                        ${sig.price?.toFixed(2)}
                                    </td>
                                    <td style={{ padding: '1.2rem 2rem' }}>
                                        <div style={{ color: 'var(--text-primary)' }}>{sig.position_desc}</div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <style>{`
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                .form-group label {
                    font-size: 0.85rem;
                    color: var(--text-secondary);
                    margin-left: 2px;
                }
            `}</style>
        </div>
    );
};

export default SignalPage;
