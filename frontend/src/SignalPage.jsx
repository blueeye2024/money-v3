import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SignalPage = () => {
    const [signals, setSignals] = useState([]);
    const [smsLogs, setSmsLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [logsLoading, setLogsLoading] = useState(true);
    const [stocks, setStocks] = useState([]);

    const [smsEnabled, setSmsEnabled] = useState(true);
    const [prices, setPrices] = useState({}); // {ticker: price}

    // Filters (Default: Today)
    const getTodayString = () => {
        const now = new Date();
        const offset = now.getTimezoneOffset() * 60000;
        return (new Date(now - offset)).toISOString().slice(0, 10);
    };

    const [filters, setFilters] = useState({
        start_date: getTodayString(),
        end_date: getTodayString(),
        limit: 30
    });

    useEffect(() => {
        fetchStocks();
        fetchSignals();
        fetchSmsLogs();
        fetchSmsSetting();
    }, []);

    const fetchSmsSetting = async () => {
        try {
            const res = await fetch('/api/settings/sms');
            if (res.ok) {
                const data = await res.json();
                setSmsEnabled(data.enabled);
            }
        } catch (e) { console.error(e); }
    };

    const toggleSms = async (enabled) => {
        try {
            const res = await fetch('/api/settings/sms', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
            if (res.ok) {
                const data = await res.json();
                setSmsEnabled(data.enabled);
            }
        } catch (e) {
            alert('설정 변경 실패');
        }
    };

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

            // Parallel fetch: Signals and Market Report (for current prices)
            const [sigRes, reportRes] = await Promise.all([
                fetch(`/api/signals?${query}`),
                fetch(`/api/report`)
            ]);

            if (sigRes.ok) {
                const data = await sigRes.json();
                setSignals(data); // Reverse order done in backend? Assuming yes.
            }

            if (reportRes.ok) {
                const reportData = await reportRes.json();
                // Create map {ticker: current_price}
                const priceMap = {};
                if (reportData.stocks) {
                    reportData.stocks.forEach(s => {
                        priceMap[s.ticker] = s.current_price;
                    });
                }
                setPrices(priceMap);
            }

        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const calcProfit = (signalPrice, currentPrice, type) => {
        if (!signalPrice || !currentPrice) return '-';
        let pct = 0;
        if (type === 'BUY') {
            pct = ((currentPrice - signalPrice) / signalPrice) * 100;
        } else {
            // For SELL signal (Short view)
            pct = ((signalPrice - currentPrice) / signalPrice) * 100;
        }
        return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
    };

    const getProfitColor = (signalPrice, currentPrice, type) => {
        if (!signalPrice || !currentPrice) return 'white';
        let isGain = false;
        if (type === 'BUY') isGain = currentPrice > signalPrice;
        else isGain = currentPrice < signalPrice;
        return isGain ? 'var(--accent-red)' : 'var(--accent-blue)';
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
            start_date: getTodayString(),
            end_date: getTodayString(),
            limit: 30
        });
    };

    const deleteSignal = async (id) => {
        if (!confirm("이 신호 기록을 삭제하시겠습니까?")) return;
        try {
            const res = await fetch(`/api/signals/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchSignals();
            } else {
                alert("삭제 실패");
            }
        } catch (e) {
            console.error(e);
        }
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

    const deleteAllSignals = async () => {
        if (!confirm('정말로 모든 신호 내역을 삭제하시겠습니까?')) return;
        try {
            await axios.delete(`/api/signals/all`);
            fetchSignals();
        } catch (err) {
            console.error("Delete All Signals Error", err);
        }
    };

    const deleteSmsLog = async (id) => {
        if (!confirm('이 기록을 삭제하시겠습니까?')) return;
        try {
            await axios.delete(`/api/sms/history/${id}`);
            fetchSmsLogs();
        } catch (err) {
            console.error("Delete SMS Log Error", err);
        }
    };

    const deleteAllSmsLogs = async () => {
        if (!confirm('정말로 모든 문자 발송 기록을 삭제하시겠습니까?')) return;
        try {
            await axios.delete(`/api/sms/history/all`);
            fetchSmsLogs();
        } catch (err) {
            console.error("Delete All SMS Logs Error", err);
        }
    };

    return (
        <div className="container" style={{ paddingBottom: '6rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
                <h1 className="text-gradient" style={{ margin: 0, fontWeight: 700 }}>실시간 신호 포착 & 알림 내역</h1>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>시스템이 자동으로 탐지한 매수/매도 신호와 발송된 문자 기록입니다.</p>
            </div>

            {/* Filters & SMS Control */}
            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '3rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <h3 style={{ margin: 0 }}>🔍 신호 내역 조회</h3>

                    {/* SMS Global Control */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem 1.5rem', borderRadius: '50px' }}>
                        <span style={{ fontWeight: 'bold', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>SMS 전체 가동:</span>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: smsEnabled ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                            <input type="radio" checked={smsEnabled} onChange={() => toggleSms(true)} />
                            ON
                        </label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', color: !smsEnabled ? 'var(--accent-red)' : 'var(--text-secondary)' }}>
                            <input type="radio" checked={!smsEnabled} onChange={() => toggleSms(false)} />
                            OFF
                        </label>
                    </div>
                </div>

                <form onSubmit={applyFilters} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', alignItems: 'end' }}>
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
                            <option value="30">30개</option>
                            <option value="50">50개</option>
                            <option value="100">100개</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap' }}>
                        <button type="submit" className="btn-submit" style={{ flex: 1 }}>조회</button>
                        <button type="button" onClick={sendSampleSms} className="btn-icon" style={{ flex: 1, background: 'rgba(59, 130, 246, 0.1)', height: '44px', padding: '0 1rem', borderRadius: '8px', color: 'var(--accent-blue)', border: '1px solid rgba(59, 130, 246, 0.3)', fontWeight: 'bold' }}>테스트</button>
                    </div>
                </form>
            </div>

            {/* Signals Table */}
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden', marginBottom: '4rem' }}>
                <div style={{ padding: '1.2rem 1.5rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ margin: 0 }}>📊 신호 발생 히스토리</h3>
                    <button onClick={deleteAllSignals} style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--accent-red)', border: '1px solid var(--accent-red)', borderRadius: '6px', padding: '0.4rem 0.8rem', cursor: 'pointer' }}>전체 삭제</button>
                </div>
                <div className="table-container">
                    <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
                        <thead>
                            <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                                <th style={{ padding: '1.2rem', textAlign: 'left' }}>발생 시간</th>
                                <th style={{ padding: '1.2rem', textAlign: 'left' }}>종목</th>
                                <th style={{ padding: '1.2rem', textAlign: 'center' }}>구분</th>
                                <th style={{ padding: '1.2rem', textAlign: 'right' }}>신호가</th>
                                <th style={{ padding: '1.2rem', textAlign: 'right' }}>현재가</th>
                                <th style={{ padding: '1.2rem', textAlign: 'center' }}>수익률</th>
                                <th style={{ padding: '1.2rem', textAlign: 'left' }}>점수 / 상태</th>
                                <th style={{ padding: '1.2rem', textAlign: 'center' }}>관리</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>데이터 로딩 중...</td></tr>
                            ) : signals.length === 0 ? (
                                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>신호 내역이 없습니다.</td></tr>
                            ) : (
                                signals.map(sig => (
                                    <tr key={sig.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                        <td style={{ padding: '1.2rem', fontSize: '0.9rem' }}>
                                            {new Date(sig.signal_time).toLocaleString('ko-KR', {
                                                month: '2-digit', day: '2-digit',
                                                hour: '2-digit', minute: '2-digit', hour12: false
                                            })}
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
                                        <td style={{ padding: '1.2rem', textAlign: 'right', fontWeight: 'bold' }}>${sig.price}</td>
                                        <td style={{ padding: '1.2rem', textAlign: 'right' }}>
                                            {prices[sig.ticker] ? `$${prices[sig.ticker]}` : '-'}
                                        </td>
                                        <td style={{ padding: '1.2rem', textAlign: 'center', fontWeight: 'bold', color: getProfitColor(sig.price, prices[sig.ticker], sig.signal_type) }}>
                                            {calcProfit(sig.price, prices[sig.ticker], sig.signal_type)}
                                        </td>
                                        <td style={{ padding: '1.2rem' }}>
                                            <div style={{ fontSize: '0.9rem' }}>{sig.position_desc}</div>
                                            {sig.score > 0 && (
                                                <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '4px' }}>
                                                    ⭐ {sig.score}점 ({sig.interpretation || '-'})
                                                </div>
                                            )}
                                        </td>
                                        <td style={{ padding: '1.2rem', textAlign: 'center' }}>
                                            <button onClick={() => deleteSignal(sig.id)} style={{ background: 'rgba(255, 50, 50, 0.1)', border: 'none', color: '#ff6b6b', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem' }}>삭제</button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* SMS Logs Section */}
            <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                <div style={{ padding: '1.2rem 1.5rem', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ margin: 0 }}>📱 문자 발송 히스토리</h3>
                    <button onClick={deleteAllSmsLogs} style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--accent-red)', border: '1px solid var(--accent-red)', borderRadius: '6px', padding: '0.4rem 0.8rem', cursor: 'pointer' }}>전체 삭제</button>
                </div>
                <div className="table-container">
                    <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
                        <thead>
                            <tr style={{ background: 'rgba(0,0,0,0.2)', color: 'var(--text-secondary)' }}>
                                <th style={{ padding: '1rem', textAlign: 'left', width: '150px' }}>전송 일시</th>
                                <th style={{ padding: '1rem', textAlign: 'left', width: '130px' }}>수신 번호</th>
                                <th style={{ padding: '1rem', textAlign: 'left' }}>메시지 내용</th>
                                <th style={{ padding: '1rem', textAlign: 'center', width: '120px' }}>관리</th>
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
                                        <td style={{ padding: '1rem', fontSize: '0.85rem' }}>
                                            {new Date(log.created_at).toLocaleString('ko-KR', {
                                                month: '2-digit', day: '2-digit',
                                                hour: '2-digit', minute: '2-digit', hour12: false
                                            })}
                                        </td>
                                        <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{log.receiver}</td>
                                        <td style={{ padding: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{log.message}</td>
                                        <td style={{ padding: '1rem', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                                            <span style={{
                                                padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold',
                                                background: log.status === 'Success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                                color: log.status === 'Success' ? '#10b981' : '#ef4444'
                                            }}>
                                                OK
                                            </span>
                                            <button onClick={() => deleteSmsLog(log.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer' }}>🗑️</button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <style>{`
                .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
                .form-group label { font-size: 0.9rem; color: var(--text-secondary); margin-left: 2px; }
                .input-field {
                    background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); color: white;
                    padding: 0.75rem; border-radius: 8px; width: 100%; outline: none; transition: all 0.2s;
                    min-height: 44px;
                }
                .input-field:focus { border-color: var(--accent-blue); background: rgba(59, 130, 246, 0.05); }
                .btn-submit {
                    padding: 0.75rem 1.5rem; background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
                    color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;
                    min-height: 44px;
                }
                .btn-submit:hover { filter: brightness(1.1); }
            `}</style>
        </div>
    );
};


export default SignalPage;
