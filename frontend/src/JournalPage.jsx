import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const JournalPage = () => {
    const [entries, setEntries] = useState([]);
    const [formData, setFormData] = useState({
        ticker: '',
        stock_name: '',
        entry_date: new Date().toISOString().slice(0, 16),
        entry_price: '',
        quantity: '',
        reason: '',
        exit_date: '',
        exit_price: ''
    });

    useEffect(() => {
        fetchJournal();
    }, []);

    const fetchJournal = async () => {
        try {
            const res = await fetch('/api/journal');
            const data = await res.json();
            setEntries(data);
        } catch (e) {
            console.error("Failed to fetch journal", e);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                exit_date: formData.exit_date ? formData.exit_date : null,
                exit_price: formData.exit_price ? parseFloat(formData.exit_price) : null
            };

            const res = await fetch('/api/journal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                alert("등록되었습니다.");
                fetchJournal();
                setFormData({
                    ticker: '', stock_name: '', entry_date: new Date().toISOString().slice(0, 16),
                    entry_price: '', quantity: '', reason: '', exit_date: '', exit_price: ''
                });
            } else {
                alert("등록 실패");
            }
        } catch (e) {
            console.error(e);
            alert("오류 발생");
        }
    };

    // Calculate Stats for Chart
    const statsData = entries.map(e => ({
        name: e.ticker,
        profit: e.profit_loss,
        pct: e.profit_pct
    })).filter(e => e.profit !== 0);

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '4rem' }}>
            <h1 className="text-gradient" style={{ fontSize: '2rem', marginBottom: '2rem' }}>매매 일지 & 수익률 분석</h1>

            {/* Input Form */}
            <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
                <h3 style={{ marginBottom: '1rem' }}>새 매매 기록 추가</h3>
                <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>

                    <input name="ticker" placeholder="종목코드 (예: SOXL)" value={formData.ticker} onChange={handleChange} required className="input-field" />
                    <input name="stock_name" placeholder="종목명" value={formData.stock_name} onChange={handleChange} className="input-field" />

                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>매수일시</label>
                        <input type="datetime-local" name="entry_date" value={formData.entry_date} onChange={handleChange} required className="input-field" />
                    </div>

                    <input type="number" name="entry_price" placeholder="매수가($)" step="0.01" value={formData.entry_price} onChange={handleChange} required className="input-field" />
                    <input type="number" name="quantity" placeholder="수량" value={formData.quantity} onChange={handleChange} required className="input-field" />

                    <input name="reason" placeholder="매매 사유 (간략히)" value={formData.reason} onChange={handleChange} className="input-field" style={{ gridColumn: '1 / -1' }} />

                    <div style={{ gridColumn: '1 / -1', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem', marginTop: '0.5rem' }}>
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>매도 정보 (선택사항 - 매도시 입력)</span>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>매도일시</label>
                        <input type="datetime-local" name="exit_date" value={formData.exit_date} onChange={handleChange} className="input-field" />
                    </div>
                    <input type="number" name="exit_price" placeholder="매도가($)" step="0.01" value={formData.exit_price} onChange={handleChange} className="input-field" />

                    <button type="submit" style={{
                        gridColumn: '1 / -1',
                        padding: '1rem',
                        background: 'var(--accent-blue)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        marginTop: '1rem'
                    }}>
                        매매 기록 저장
                    </button>
                </form>
            </div>

            {/* Chart */}
            <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', height: '400px' }}>
                <h3 style={{ marginBottom: '1rem' }}>최근 매매 손익 현황</h3>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={statsData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="name" stroke="var(--text-secondary)" />
                        <YAxis stroke="var(--text-secondary)" />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid var(--glass-border)' }}
                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        />
                        <Legend />
                        <Bar dataKey="profit" name="손익금($)" fill="#8884d8">
                            {statsData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.profit >= 0 ? 'var(--accent-red)' : 'var(--accent-blue)'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* List Table */}
            <div className="glass-panel" style={{ padding: '2rem', overflowX: 'auto' }}>
                <h3 style={{ marginBottom: '1rem' }}>매매 기록 리스트</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                    <thead>
                        <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--glass-border)' }}>
                            <th style={{ padding: '1rem', textAlign: 'left' }}>종목</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>진입가</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>청산가</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>수량</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>P/L($)</th>
                            <th style={{ padding: '1rem', textAlign: 'right' }}>수익률</th>
                            <th style={{ padding: '1rem', textAlign: 'left' }}>사유</th>
                        </tr>
                    </thead>
                    <tbody>
                        {entries.length === 0 ? (
                            <tr><td colSpan="7" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>기록이 없습니다.</td></tr>
                        ) : (
                            entries.map(entry => (
                                <tr key={entry.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <strong>{entry.ticker}</strong>
                                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{new Date(entry.entry_date).toLocaleDateString()}</div>
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>${entry.entry_price}</td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>{entry.exit_price ? `$${entry.exit_price}` : '-'}</td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>{entry.quantity}</td>
                                    <td style={{ padding: '1rem', textAlign: 'right', color: entry.profit_loss > 0 ? 'var(--accent-red)' : entry.profit_loss < 0 ? 'var(--accent-blue)' : 'inherit' }}>
                                        {entry.profit_loss ? `$${entry.profit_loss.toFixed(2)}` : '-'}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'right', fontWeight: 'bold', color: entry.profit_pct > 0 ? 'var(--accent-red)' : entry.profit_pct < 0 ? 'var(--accent-blue)' : 'inherit' }}>
                                        {entry.profit_pct ? `${entry.profit_pct.toFixed(2)}%` : '-'}
                                    </td>
                                    <td style={{ padding: '1rem', maxWidth: '200px', color: 'var(--text-secondary)' }}>{entry.reason}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

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
