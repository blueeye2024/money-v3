import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const TradingJournalPage = () => {
    const [journals, setJournals] = useState([]);
    const [stocks, setStocks] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [filter, setFilter] = useState({ status: '', ticker: '' });
    const [showCloseModal, setShowCloseModal] = useState(null);
    const [viewJournal, setViewJournal] = useState(null); // View mode
    const [imagePreview, setImagePreview] = useState(null);
    const fileInputRef = useRef(null);

    // Form state
    const [form, setForm] = useState({
        ticker: '', buy_date: '', buy_price: '', buy_qty: 1,
        buy_reason: '', market_condition: '', emotion_before: '',
        score_at_entry: '', tags: '', screenshot: null
    });

    // Close form state
    const [closeForm, setCloseForm] = useState({
        sell_date: '', sell_price: '', sell_reason: '',
        emotion_after: '', score_at_exit: '', lesson: ''
    });

    useEffect(() => { fetchAll(); }, [filter]);

    const fetchAll = async () => {
        setLoading(true);
        try { await Promise.all([fetchJournals(), fetchStocks(), fetchStats()]); }
        catch (e) { console.error(e); }
        setLoading(false);
    };

    const fetchJournals = async () => {
        try {
            let url = '/api/journal?limit=100';
            if (filter.status) url += `&status=${filter.status}`;
            if (filter.ticker) url += `&ticker=${filter.ticker}`;
            const res = await axios.get(url);
            setJournals(res.data || []);
        } catch (e) { console.error(e); }
    };

    const fetchStocks = async () => {
        try { const res = await axios.get('/api/stocks'); setStocks(res.data || []); }
        catch (e) { console.error(e); }
    };

    const fetchStats = async () => {
        try { const res = await axios.get('/api/journal/stats'); setStats(res.data || {}); }
        catch (e) { console.error(e); }
    };

    const handleOpenModal = (journal = null) => {
        if (journal) {
            setEditingId(journal.id);
            setForm({
                ticker: journal.ticker, buy_date: journal.buy_date?.slice(0, 16) || '',
                buy_price: journal.buy_price, buy_qty: journal.buy_qty,
                buy_reason: journal.buy_reason || '', market_condition: journal.market_condition || '',
                emotion_before: journal.emotion_before || '', score_at_entry: journal.score_at_entry || '',
                tags: journal.tags || '', screenshot: journal.screenshot || null
            });
            setImagePreview(journal.screenshot || null);
        } else {
            setEditingId(null);
            setForm({ ticker: '', buy_date: '', buy_price: '', buy_qty: 1, buy_reason: '', market_condition: '', prediction_score: '', total_assets: '', score_at_entry: '', tags: '', screenshot: null, memo: '' });
            setImagePreview(null);
        }
        setIsModalOpen(true);
    };

    const handleCloseModal = () => { setIsModalOpen(false); setEditingId(null); setImagePreview(null); };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => { setImagePreview(reader.result); setForm(prev => ({ ...prev, screenshot: reader.result })); };
            reader.readAsDataURL(file);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const payload = {
            ...form,
            buy_price: parseFloat(form.buy_price) || 0,
            buy_qty: parseInt(form.buy_qty) || 1,
            total_assets: parseFloat(form.total_assets) || 0,
            score_at_entry: parseInt(form.score_at_entry) || 0,
            tags: Array.isArray(form.tags) ? form.tags.join(',') : form.tags || ''
        };
        try {
            if (editingId) { await axios.put(`/api/journal/${editingId}`, payload); }
            else { await axios.post('/api/journal', payload); }
            handleCloseModal(); fetchAll();
        } catch (e) {
            console.error('Save failed details:', e.response?.data);
            const errorMsg = e.response?.data?.detail
                ? (typeof e.response.data.detail === 'object' ? JSON.stringify(e.response.data.detail) : e.response.data.detail)
                : e.message;
            alert('저장 실패: ' + errorMsg);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm('정말 이 거래를 삭제하시겠습니까?')) return;
        try { await axios.delete(`/api/journal/${id}`); fetchAll(); }
        catch (e) { alert('삭제 실패'); }
    };

    const handleClose = async (id) => {
        try {
            await axios.put(`/api/journal/${id}`, { ...closeForm, status: 'CLOSED' });
            setShowCloseModal(null);
            setCloseForm({ sell_date: '', sell_price: '', sell_reason: '', emotion_after: '', score_at_exit: '', lesson: '' });
            fetchAll();
        } catch (e) { alert('청산 처리 실패'); }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        return d.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    };

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;

    return (
        <div className="page-container">
            {/* Super Container - Wrapping everything - Transparent Dark Glass */}
            <div className="glass-panel" style={{
                padding: '2.5rem',
                background: 'rgba(59, 130, 246, 0.08)',
                borderRadius: '30px',
                border: '1px solid rgba(147, 197, 253, 0.2)',
                backdropFilter: 'blur(20px)',
                boxShadow: '0 20px 60px rgba(59, 130, 246, 0.15)'
            }}>
                {/* Header */}
                <div className="page-header" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
                    <h1 className="page-title" style={{ color: 'white', textShadow: '0 2px 4px rgba(0,0,0,0.5)' }}>매매일지</h1>
                    <p className="page-subtitle" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>거래 분석 및 복기를 위한 매매일지</p>
                </div>

                {/* Summary Cards - JournalPage Style */}
                <div className="summary-grid">
                    <div className="glass-card" style={{
                        background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', // Luxury Royal Blue
                        boxShadow: '0 10px 40px rgba(30, 58, 138, 0.2)',
                        color: 'white',
                        border: '1px solid rgba(255, 255, 255, 0.1)'
                    }}>
                        <div className="card-label" style={{ color: 'rgba(255, 255, 255, 0.8)' }}>총 거래</div>
                        <div className="card-value" style={{ color: 'white' }}>{stats.total_trades || 0}</div>
                        <div style={{ fontSize: '0.9rem', color: 'rgba(255, 255, 255, 0.7)' }}>
                            진행 {stats.open_trades || 0} / 청산 {stats.closed_trades || 0}
                        </div>
                    </div>

                    <div className="glass-card" style={{
                        background: (stats.win_rate || 0) >= 50
                            ? 'linear-gradient(135deg, #d4af37 0%, #a67c00 100%)' // Luxury Gold
                            : 'linear-gradient(135deg, #be123c 0%, #881337 100%)', // Luxury Ruby
                        boxShadow: (stats.win_rate || 0) >= 50
                            ? '0 10px 40px rgba(212, 175, 55, 0.3)'
                            : '0 10px 40px rgba(190, 18, 60, 0.3)',
                        color: 'white'
                    }}>
                        <div className="card-label">승률</div>
                        <div className="card-value">{stats.win_rate || 0}%</div>
                        <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.8)' }}>
                            {stats.wins || 0}승 {stats.losses || 0}패
                        </div>
                    </div>

                    <div className="glass-card" style={{
                        background: (stats.total_pnl || 0) >= 0
                            ? 'linear-gradient(135deg, #059669 0%, #047857 100%)' // Luxury Emerald
                            : 'linear-gradient(135deg, #9f1239 0%, #881337 100%)', // Luxury Deep Red
                        boxShadow: (stats.total_pnl || 0) >= 0
                            ? '0 10px 40px rgba(5, 150, 105, 0.3)'
                            : '0 10px 40px rgba(159, 18, 57, 0.3)',
                        color: 'white'
                    }}>
                        <div className="card-label">총 손익</div>
                        <div className="card-value">
                            {(stats.total_pnl || 0) >= 0 ? '+' : ''}${(stats.total_pnl || 0).toFixed(2)}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.8)' }}>
                            평균 {(stats.avg_pnl_pct || 0) >= 0 ? '+' : ''}{(stats.avg_pnl_pct || 0).toFixed(1)}%
                        </div>
                    </div>
                </div>



                {/* Action Bar */}
                <div className="action-bar" style={{ marginBottom: '2rem', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <select className="glass-input" value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })} style={{ width: '120px', color: '#f1f5f9', fontSize: '0.9rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.1)' }}>
                            <option value="" style={{ color: 'black' }}>전체 상태</option>
                            <option value="OPEN" style={{ color: 'black' }}>진행 중</option>
                            <option value="CLOSED" style={{ color: 'black' }}>청산 완료</option>
                        </select>
                        <select className="glass-input" value={filter.ticker} onChange={(e) => setFilter({ ...filter, ticker: e.target.value })} style={{ width: '120px', color: '#f1f5f9', fontSize: '0.9rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.1)' }}>
                            <option value="" style={{ color: 'black' }}>전체 종목</option>
                            {stocks.map(s => <option key={s.code} value={s.code} style={{ color: 'black' }}>{s.code}</option>)}
                        </select>
                    </div>
                    <button className="btn-primary" onClick={() => handleOpenModal()}>+ 새 매매 기록</button>
                </div>

                {/* Holdings Table - Asset Management Style (Blue Gradient) */}
                <div style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 50%, #93c5fd 100%)', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 20px rgba(59,130,246,0.2)', border: '1px solid rgba(147,197,253,0.3)' }}>
                    <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid rgba(59,130,246,0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', margin: 0, color: '#1e3a8a' }}>매매일지</h2>
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>종목</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>상태</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>매수</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>매도</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>손익</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>보유</th>
                                    <th style={{ color: '#1e3a8a', fontSize: '0.85rem', fontWeight: 'bold', background: 'rgba(255,255,255,0.3)' }}>관리</th>
                                </tr>
                            </thead>
                            <tbody>
                                {journals.length === 0 ? (
                                    <tr><td colSpan="7" style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>거래 기록이 없습니다.</td></tr>
                                ) : journals.map(j => (
                                    <tr key={j.id} style={{ borderBottom: '1px solid rgba(59,130,246,0.1)' }}>
                                        <td style={{ color: '#1e40af' }}>
                                            <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>{j.ticker}</div>
                                        </td>
                                        <td>
                                            <span style={{
                                                padding: '0.25rem 0.5rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: '600',
                                                background: j.status === 'OPEN' ? 'rgba(22, 163, 74, 0.2)' : 'rgba(71, 85, 105, 0.2)',
                                                color: j.status === 'OPEN' ? '#15803d' : '#475569'
                                            }}>
                                                {j.status === 'OPEN' ? '진행 중' : '청산'}
                                            </span>
                                        </td>
                                        <td style={{ color: '#1e3a8a', fontWeight: '500' }}>
                                            <div style={{ fontWeight: '600' }}>${Number(j.buy_price).toFixed(2)} x {j.buy_qty}</div>
                                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{formatDate(j.buy_date)}</div>
                                        </td>
                                        <td style={{ color: '#1e3a8a', fontWeight: '500' }}>
                                            {j.sell_price ? (
                                                <>
                                                    <div style={{ fontWeight: '600' }}>${Number(j.sell_price).toFixed(2)}</div>
                                                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{formatDate(j.sell_date)}</div>
                                                </>
                                            ) : <span style={{ color: '#94a3b8' }}>-</span>}
                                        </td>
                                        <td>
                                            {j.realized_pnl !== null ? (
                                                <>
                                                    <div style={{ fontSize: '1rem', fontWeight: '700', color: j.realized_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                                                        {j.realized_pnl >= 0 ? '+' : ''}${j.realized_pnl}
                                                    </div>
                                                    <div style={{ fontSize: '0.85rem', color: j.realized_pnl_pct >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                                                        {j.realized_pnl_pct >= 0 ? '+' : ''}{j.realized_pnl_pct}%
                                                    </div>
                                                </>
                                            ) : <span style={{ color: '#94a3b8' }}>-</span>}
                                        </td>
                                        <td style={{ color: '#64748b' }}>{j.hold_days !== null ? `${j.hold_days}일` : '-'}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                <button onClick={() => setViewJournal(j)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(59,130,246,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#1e40af' }}>보기</button>
                                                {j.status === 'OPEN' && (
                                                    <button onClick={() => setShowCloseModal(j.id)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#dc2626' }}>청산</button>
                                                )}
                                                <button onClick={() => handleOpenModal(j)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(100,116,139,0.2)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#334155' }}>수정</button>
                                                <button onClick={() => handleDelete(j.id)} style={{ padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.1)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: '600', color: '#dc2626' }}>삭제</button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* View Modal - Report Style */}
            {
                viewJournal && (
                    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000, padding: '2rem' }}>
                        <div style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', borderRadius: '20px', maxWidth: '700px', width: '100%', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 25px 50px rgba(0,0,0,0.25)' }}>
                            {/* Report Header */}
                            <div style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)', padding: '2rem', borderRadius: '20px 20px 0 0', color: 'white' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <div style={{ fontSize: '2rem', fontWeight: '800', marginBottom: '0.5rem' }}>{viewJournal.ticker}</div>
                                        <span style={{
                                            padding: '0.35rem 0.75rem', borderRadius: '20px', fontSize: '0.85rem', fontWeight: '600',
                                            background: viewJournal.status === 'OPEN' ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.2)',
                                            color: 'white'
                                        }}>
                                            {viewJournal.status === 'OPEN' ? '진행 중' : '청산 완료'}
                                        </span>
                                    </div>
                                    <button onClick={() => setViewJournal(null)} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', width: '36px', height: '36px', borderRadius: '50%', color: 'white', fontSize: '1.2rem', cursor: 'pointer' }}>×</button>
                                </div>
                            </div>

                            {/* Report Body */}
                            <div style={{ padding: '2rem' }}>
                                {/* Trade Summary */}
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                                    <div style={{ background: 'rgba(59,130,246,0.1)', padding: '1rem', borderRadius: '12px', textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>매수가</div>
                                        <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#1e40af' }}>${Number(viewJournal.buy_price).toFixed(2)}</div>
                                        <div style={{ fontSize: '0.85rem', color: '#64748b' }}>x {viewJournal.buy_qty}주</div>
                                    </div>
                                    <div style={{ background: viewJournal.sell_price ? 'rgba(59,130,246,0.1)' : 'rgba(100,116,139,0.1)', padding: '1rem', borderRadius: '12px', textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>매도가</div>
                                        <div style={{ fontSize: '1.4rem', fontWeight: '700', color: viewJournal.sell_price ? '#1e40af' : '#94a3b8' }}>
                                            {viewJournal.sell_price ? `$${Number(viewJournal.sell_price).toFixed(2)}` : '-'}
                                        </div>
                                    </div>
                                    <div style={{ background: viewJournal.realized_pnl !== null ? (viewJournal.realized_pnl >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)') : 'rgba(100,116,139,0.1)', padding: '1rem', borderRadius: '12px', textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>손익</div>
                                        <div style={{ fontSize: '1.4rem', fontWeight: '700', color: viewJournal.realized_pnl !== null ? (viewJournal.realized_pnl >= 0 ? '#10b981' : '#ef4444') : '#94a3b8' }}>
                                            {viewJournal.realized_pnl !== null ? `${viewJournal.realized_pnl >= 0 ? '+' : ''}$${viewJournal.realized_pnl}` : '-'}
                                        </div>
                                        {viewJournal.realized_pnl_pct !== null && (
                                            <div style={{ fontSize: '0.85rem', color: viewJournal.realized_pnl_pct >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                                                {viewJournal.realized_pnl_pct >= 0 ? '+' : ''}{viewJournal.realized_pnl_pct}%
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Details */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>매수 일시</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{formatDate(viewJournal.buy_date)}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>매도 일시</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.sell_date ? formatDate(viewJournal.sell_date) : '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>보유 기간</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.hold_days !== null ? `${viewJournal.hold_days}일` : '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>시장 상황</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.market_condition || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>예측 지수</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.prediction_score || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>청산 감정</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.emotion_after || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>진입 점수</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.score_at_entry || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>청산 점수</div>
                                        <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e3a8a' }}>{viewJournal.score_at_exit || '-'}</div>
                                    </div>
                                </div>

                                {/* Tags */}
                                {viewJournal.tags && (
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.5rem' }}>태그</div>
                                        <div style={{ color: '#3b82f6', fontWeight: '500' }}>{viewJournal.tags}</div>
                                    </div>
                                )}

                                {/* Reasons */}
                                {viewJournal.buy_reason && (
                                    <div style={{ background: 'rgba(59,130,246,0.1)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#1e40af', fontWeight: '600', marginBottom: '0.5rem' }}>매수 근거</div>
                                        <div style={{ color: '#334155', lineHeight: 1.6 }}>{viewJournal.buy_reason}</div>
                                    </div>
                                )}

                                {viewJournal.sell_reason && (
                                    <div style={{ background: 'rgba(239,68,68,0.1)', padding: '1rem', borderRadius: '12px', marginBottom: '1rem' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#dc2626', fontWeight: '600', marginBottom: '0.5rem' }}>매도 근거</div>
                                        <div style={{ color: '#334155', lineHeight: 1.6 }}>{viewJournal.sell_reason}</div>
                                    </div>
                                )}

                                {viewJournal.lesson && (
                                    <div style={{ background: 'rgba(245,158,11,0.1)', padding: '1rem', borderRadius: '12px', marginBottom: '1.5rem', borderLeft: '4px solid #f59e0b' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#d97706', fontWeight: '600', marginBottom: '0.5rem' }}>교훈 / 배운 점</div>
                                        <div style={{ color: '#334155', lineHeight: 1.6 }}>{viewJournal.lesson}</div>
                                    </div>
                                )}

                                {/* Screenshot */}
                                {viewJournal.screenshot && (
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.5rem' }}>차트 스크린샷</div>
                                        <img src={viewJournal.screenshot} alt="Chart Screenshot" style={{ width: '100%', borderRadius: '12px', border: '1px solid #e2e8f0' }} />
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Entry Modal */}
            {
                isModalOpen && (
                    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', padding: '2rem', zIndex: 1000, alignItems: 'center' }}>
                        <div className="glass-panel" style={{ width: '600px', padding: '2rem', maxHeight: '90vh', overflowY: 'auto', position: 'relative' }}>
                            <button onClick={handleCloseModal} style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', background: 'transparent', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer' }}>×</button>
                            <h2 style={{ marginBottom: '1.5rem', color: '#ffffff', fontWeight: '800', textShadow: '0 2px 4px rgba(0,0,0,0.5)' }}>{editingId ? '거래 수정' : '새 매매 기록'}</h2>
                            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>종목</label>
                                        <select className="glass-input" value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} required style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }}>
                                            <option value="">선택</option>
                                            {stocks.map(s => <option key={s.code} value={s.code}>{s.code} - {s.name}</option>)}
                                        </select>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>매수 일시</label>
                                        <input className="glass-input" type="datetime-local" value={form.buy_date} onChange={(e) => setForm({ ...form, buy_date: e.target.value })} required style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} />
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>매수가 ($)</label>
                                        <input className="glass-input" type="number" step="0.01" value={form.buy_price} onChange={(e) => setForm({ ...form, buy_price: e.target.value })} required style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} />
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>수량</label>
                                        <input className="glass-input" type="number" value={form.buy_qty} onChange={(e) => setForm({ ...form, buy_qty: Number(e.target.value) })} required style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} />
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>시장 상황</label>
                                        <select className="glass-input" value={form.market_condition} onChange={(e) => setForm({ ...form, market_condition: e.target.value })} style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }}>
                                            <option value="">선택</option>
                                            <option value="상승장">상승장</option>
                                            <option value="하락장">하락장</option>
                                            <option value="보합">보합</option>
                                        </select>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>예측 지수</label>
                                        <select className="glass-input" value={form.prediction_score || ''} onChange={(e) => setForm({ ...form, prediction_score: e.target.value })} style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }}>
                                            <option value="">선택</option>
                                            <option value="매우 확신 (100~80%)">매우 확신 (100~80%)</option>
                                            <option value="확신 (80~60%)">확신 (80~60%)</option>
                                            <option value="보통 (60~50%)">보통 (60~50%)</option>
                                            <option value="불확실 (50% 이하)">불확실 (50% 이하)</option>
                                        </select>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>현재 총 자산 ($)</label>
                                        <input className="glass-input" type="number" step="0.01" value={form.total_assets} onChange={(e) => setForm({ ...form, total_assets: e.target.value })} style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} placeholder="숫자만 입력" />
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>진입 점수</label>
                                        <input className="glass-input" type="number" value={form.score_at_entry} onChange={(e) => setForm({ ...form, score_at_entry: e.target.value })} style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} placeholder="예: 85" />
                                    </div>
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>태그</label>
                                    <input className="glass-input" type="text" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="#추세추종" style={{ width: '100%', fontSize: '0.85rem', color: '#000', background: 'rgba(255,255,255,0.9)' }} />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>메모</label>
                                    <textarea
                                        className="glass-input"
                                        value={form.buy_reason}
                                        onChange={(e) => setForm({ ...form, buy_reason: e.target.value })}
                                        placeholder="매매 전략, 생각, 특이사항 등을 기록하세요."
                                        style={{
                                            width: '100%', minHeight: '120px', fontSize: '0.9rem', padding: '1rem',
                                            lineHeight: '1.6',
                                            background: 'linear-gradient(#fdfbf7 95%, #e2e8f0 100%)', // Notebook paper feel
                                            backgroundSize: '100% 2rem',
                                            border: '1px solid #e2e8f0',
                                            color: '#334155'
                                        }}
                                    />
                                </div>
                                <div style={{ marginBottom: '1rem' }}>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#ccc' }}>차트 스크린샷</label>
                                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                                        <input type="file" ref={fileInputRef} accept="image/*" onChange={handleImageChange} style={{ display: 'none' }} />
                                        <button type="button" onClick={() => fileInputRef.current.click()} className="btn-secondary" style={{ padding: '0.5rem 1rem' }}>이미지 선택</button>
                                        {imagePreview && (
                                            <div style={{ position: 'relative' }}>
                                                <img src={imagePreview} alt="Preview" style={{ maxWidth: '150px', maxHeight: '100px', borderRadius: '8px' }} />
                                                <button type="button" onClick={() => { setImagePreview(null); setForm({ ...form, screenshot: null }); }} style={{ position: 'absolute', top: '-8px', right: '-8px', width: '20px', height: '20px', borderRadius: '50%', background: '#ef4444', color: 'white', border: 'none', cursor: 'pointer', fontSize: '12px' }}>×</button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                    <button type="button" onClick={handleCloseModal} className="btn-secondary" style={{ flex: 1 }}>취소</button>
                                    <button type="submit" className="btn-primary" style={{ flex: 1 }}>저장</button>
                                </div>
                            </form>
                        </div>
                    </div>
                )
            }

            {/* Close Trade Modal */}
            {
                showCloseModal && (
                    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', padding: '2rem', zIndex: 1000, alignItems: 'center' }}>
                        <div className="glass-panel" style={{ width: '500px', padding: '2rem', maxHeight: '90vh', overflowY: 'auto' }}>
                            <h2 style={{ marginBottom: '1.5rem' }}>거래 청산</h2>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>매도 일시</label>
                                        <input className="glass-input" type="datetime-local" value={closeForm.sell_date} onChange={(e) => setCloseForm({ ...closeForm, sell_date: e.target.value })} required style={{ width: '100%' }} />
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>매도가 ($)</label>
                                        <input className="glass-input" type="number" step="0.01" value={closeForm.sell_price} onChange={(e) => setCloseForm({ ...closeForm, sell_price: e.target.value })} required style={{ width: '100%' }} />
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>청산 감정</label>
                                        <select className="glass-input" value={closeForm.emotion_after} onChange={(e) => setCloseForm({ ...closeForm, emotion_after: e.target.value })} style={{ width: '100%', fontSize: '0.85rem', color: '#1e3a8a', background: 'rgba(255,255,255,0.1)' }}>
                                            <option value="">선택</option>
                                            <option value="만족">만족</option>
                                            <option value="후회">후회</option>
                                            <option value="중립">중립</option>
                                        </select>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>청산 점수</label>
                                        <input className="glass-input" type="number" value={closeForm.score_at_exit} onChange={(e) => setCloseForm({ ...closeForm, score_at_exit: e.target.value })} style={{ width: '100%' }} />
                                    </div>
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#888' }}>매도 근거</label>
                                    <textarea className="glass-input" value={closeForm.sell_reason} onChange={(e) => setCloseForm({ ...closeForm, sell_reason: e.target.value })} rows={2} style={{ width: '100%', resize: 'vertical' }} />
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '5px', fontSize: '0.85rem', color: '#f59e0b' }}>교훈 / 배운 점</label>
                                    <textarea className="glass-input" value={closeForm.lesson} onChange={(e) => setCloseForm({ ...closeForm, lesson: e.target.value })} rows={2} placeholder="이 거래에서 배운 점은?" style={{ width: '100%', resize: 'vertical' }} />
                                </div>
                                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                    <button onClick={() => setShowCloseModal(null)} className="btn-secondary" style={{ flex: 1 }}>취소</button>
                                    <button onClick={() => handleClose(showCloseModal)} className="btn-primary" style={{ flex: 1, background: '#dc2626' }}>청산 완료</button>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
};

export default TradingJournalPage;
