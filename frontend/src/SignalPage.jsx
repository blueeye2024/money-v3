import React, { useState, useEffect } from 'react';

const SignalPage = () => {
    const [signals, setSignals] = useState([]);
    const [smsLogs, setSmsLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [logsLoading, setLogsLoading] = useState(true);
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
        fetchSmsLogs();
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

    const fetchSmsLogs = async () => {
        setLogsLoading(true);
        try {
            const res = await fetch('/api/sms/history');
            if (res.ok) setSmsLogs(await res.json());
        } catch (e) {
            console.error(e);
        } finally {
            setLogsLoading(false);
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
    };

    const sendSampleSms = async () => {
        if (!confirm(`샘플 신호(SOXL 매수)로 테스트 문자를 발송하시겠습니까?`)) return;

        try {
            const res = await fetch('/api/sms/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stock_name: "SOXL (Sample)",
                    signal_type: "매수 진입",
                    price: 45.20,
                    reason: "수동 테스트 발송"
                })
            });

            if (res.ok) {
                alert("테스트 문자가 발송 요청되었습니다.");
                fetchSmsLogs();
            } else {
                alert("발송 실패");
            }
        } catch (e) {
            console.error(e);
            alert("오류 발생");
        }
    };

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '6rem', fontFamily: "'Inter', sans-serif" }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', marginTop: '2rem' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.2rem', margin: 0, fontWeight: 700 }}>실시간 신호 포착 & 알림 내역</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>시스템이 자동으로 탐지한 매수/매도 신호와 발송된 문자 기록입니다.</p>
                </div>
            </div>

            {/* Filters */}
            <div className="glass-panel" style={{ padding: '2.5rem', marginBottom: '3rem' }}>
                <h3 style={{ marginBottom: '1.5rem' }}>🔍 신호 내역 조회</h3>
                <form onSubmit={applyFilters} style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'end' }}>
                    <div className="form-group" style={{ flex: '1 1 200px' }}>
                        <label>종목 필터</label>
                        <select name="ticker" value={filters.ticker} onChange={handleFilterChange} className="input-field" style={{ background: '#e2e8f0', color: 'black', fontWeight: 'bold' }}>
                            <option value="">모든 종목</option>
                            {stocks.map(s => <option key={s.code} value={s.code}>{s.name} ({s.code})</option>)}
                        </select>
                    </div>
                    <div className="form-group" style={{ flex: '1 1 150px', minWidth: '150px' }}>
                        <label>시작일</label>
                        <input type="date" name="start_date" value={filters.start_date} onChange={handleFilterChange} className="input-field" style={{ padding: '0.6rem 0.9rem' }} />
                    </div>
                    <div style={{ paddingBottom: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center' }}>~</div>
                    <div className="form-group" style={{ flex: '1 1 150px', minWidth: '150px' }}>
                        <label>종료일</label>
                        <input type="date" name="end_date" value={filters.end_date} onChange={handleFilterChange} className="input-field" style={{ padding: '0.6rem 0.9rem' }} />
                    </div>
                    <div className="form-group" style={{ flex: '0 0 120px' }}>
                        <label>표시 개수</label>
                        <select name="limit" value={filters.limit} onChange={handleFilterChange} className="input-field" style={{ background: '#e2e8f0', color: 'black', fontWeight: 'bold' }}>
                            <option value="30">30개</option>
                            <option value="50">50개</option>
                            <option value="100">100개</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', gap: '0.8rem', flex: '1 1 auto' }}>
                        <button type="submit" className="btn-submit" style={{ flex: 2, padding: '0.9rem' }}>조회하기</button>
                        <button type="button" onClick={resetFilters} className="btn-icon" style={{ flex: 1, background: 'rgba(255,255,255,0.05)', height: '48px', padding: '0 1rem', borderRadius: '8px', color: 'var(--text-secondary)', border: '1px solid rgba(255,255,255,0.1)' }}>초기화</button>
                        <button type="button" onClick={sendSampleSms} className="btn-icon" style={{ flex: 1.5, background: 'rgba(59, 130, 246, 0.1)', height: '48px', padding: '0 1rem', borderRadius: '8px', color: 'var(--accent-blue)', border: '1px solid rgba(59, 130, 246, 0.3)', fontWeight: 'bold' }}>💬 SMS 테스트</button>
                    </div>
                </form>
            </div>

            {/* Signals Table */}
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', marginBottom: '4rem' }}>
                <div style={{ padding: '1.5rem 2rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <h3 style={{ margin: 0 }}>📊 신호 발생 히스토리</h3>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '1.2rem 2rem', textAlign: 'left' }}>발생 시간</th>
                            <th style={{ padding: '1.2rem', textAlign: 'left' }}>종목</th>
                            <th style={{ padding: '1.2rem', textAlign: 'center' }}>구분</th>
                            <th style={{ padding: '1.2rem', textAlign: 'right' }}>가격</th>
                            <th style={{ padding: '1.2rem 2rem', textAlign: 'left' }}>상태 / 비고</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>데이터 로딩 중...</td></tr>
                        ) : signals.length === 0 ? (
                            <tr><td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>신호 내역이 없습니다.</td></tr>
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
                                    <td style={{ padding: '1.2rem', textAlign: 'right' }}>
                                        <span style={{ fontWeight: 'bold', color: 'rgba(255,255,255,0.9)' }}>${sig.price?.toFixed(2)}</span>
                                    </td>
                                    <td style={{ padding: '1.2rem 2rem' }}>
                                        <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{sig.position_desc}</div>
                                        {sig.is_sent && <span style={{ fontSize: '0.75rem', color: 'var(--accent-green)' }}>● 자동문자발송됨</span>}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* SMS Logs Section */}
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <div style={{ padding: '1.5rem 2rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <h3 style={{ margin: 0 }}>📱 문자 발송 히스토리 (최근 30개)</h3>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '1rem 2rem', textAlign: 'left', width: '200px' }}>전송 일시</th>
                            <th style={{ padding: '1rem', textAlign: 'left', width: '150px' }}>수신 번호</th>
                            <th style={{ padding: '1rem', textAlign: 'left' }}>메시지 내용</th>
                            <th style={{ padding: '1rem 2rem', textAlign: 'center', width: '120px' }}>상태</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logsLoading ? (
                            <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>로딩 중...</td></tr>
                        ) : smsLogs.length === 0 ? (
                            <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>발송 기록이 없습니다.</td></tr>
                        ) : (
                            smsLogs.map(log => (
                                <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '1rem 2rem', fontSize: '0.85rem' }}>{new Date(log.created_at).toLocaleString()}</td>
                                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{log.receiver}</td>
                                    <td style={{ padding: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{log.message}</td>
                                    <td style={{ padding: '1rem 2rem', textAlign: 'center' }}>
                                        <span style={{
                                            padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold',
                                            background: log.status === 'Success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                            color: log.status === 'Success' ? '#10b981' : '#ef4444'
                                        }}>
                                            {log.status}
                                        </span>
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
                    height: 48px;
                }
                .input-field:focus {
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
                    font-size: 1rem;
                    cursor: pointer;
                    transition: all 0.2s;
                    height: 48px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .btn-submit:hover {
                    filter: brightness(1.1);
                    transform: translateY(-1px);
                }
                .btn-icon {
                    background: none;
                    border: none;
                    cursor: pointer;
                    transition: background 0.2s;
                }
            `}</style>
        </div>
    );
};

export default SignalPage;
