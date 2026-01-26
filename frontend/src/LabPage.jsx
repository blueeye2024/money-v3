
import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import { useDropzone } from 'react-dropzone';

const LabPage = () => {
    // State
    const [period, setPeriod] = useState('5m'); // Default 5m (Single Source)
    const [ticker, setTicker] = useState('SOXL');
    const [statusFilter, setStatusFilter] = useState('ALL'); // ALL, COMPLETE, INCOMPLETE
    const [page, setPage] = useState(1);
    const [data, setData] = useState([]);
    const [pagination, setPagination] = useState({});
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [selectedIds, setSelectedIds] = useState([]);

    // Custom Ticker Edit Mode (Optional, keep or replace with Select)
    // User requested: "Select from SOXL, SOXS, UPRO"

    // Filter
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');

    // Fetch existing data on mount/period/page/filter change
    useEffect(() => {
        fetchData();
    }, [period, page, ticker, statusFilter]); // Auto-fetch on filter change? Yes usually better UX.

    const fetchData = async () => {
        setLoading(true);
        try {
            // [Req] Pagination 20
            let url = `/api/lab/data/${period}?page=${page}&limit=20&ticker=${ticker}&status=${statusFilter}`;
            if (dateFrom) url += `&date_from=${dateFrom}`;
            if (dateTo) url += `&date_to=${dateTo}`;

            const res = await fetch(url);
            const json = await res.json();
            if (json.status === 'success') {
                setData(json.data);
                setPagination(json.pagination);
                setSelectedIds([]); // Clear selection on refresh
            }
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    // --- Batch Calculation Logic ---
    const handleCalculateAction = async () => {
        // [Req] Support Partial Scoring via Checkbox
        const isSelectionMode = selectedIds.length > 0;

        let confirmText = isSelectionMode
            ? `선택한 ${selectedIds.length}개 데이터를 채점하시겠습니까?`
            : '전체 채점 혹은 미완료 채점을 선택하세요.';

        // If selection, no need for complex popup, just confirm.
        if (isSelectionMode) {
            const result = await Swal.fire({
                title: '선택 채점',
                text: confirmText,
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#3b82f6',
                confirmButtonText: '채점 실행'
            });
            if (!result.isConfirmed) return;

            // Execute Selection Calc
            setLoading(true);
            try {
                // Send IDs as comma separated
                const idsStr = selectedIds.join(',');
                const res = await fetch(`/api/lab/calculate?period=${period}&ticker=${ticker}&ids=${idsStr}`, {
                    method: 'POST'
                });
                const json = await res.json();
                if (json.status === 'success') {
                    Swal.fire('완료', `선택된 ${json.updated_count}개 채점 완료`, 'success');
                    fetchData();
                } else {
                    Swal.fire('Error', json.message, 'error');
                }
            } catch (e) {
                Swal.fire('Error', e.message, 'error');
            }
            setLoading(false);
            return;
        }

        // Standard Batch Logic (Existing)
        const { value: calcType } = await Swal.fire({
            title: '채점 옵션 선택',
            input: 'radio',
            inputOptions: {
                'all': '전체 채점',
                'missing': '미완료 부분 채점'
            },
            inputValue: 'missing',
            showCancelButton: true,
            confirmButtonColor: '#3b82f6',
            confirmButtonText: '실행',
            cancelButtonText: '취소'
        });

        if (!calcType) return;
        const onlyMissing = (calcType === 'missing');

        // Start Batch Process
        setLoading(true);
        const BATCH_SIZE = 200; // Keep batch buffer
        let totalProcessed = 0;

        Swal.fire({
            title: '채점 진행 중...',
            html: '준비 중...',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            for (let i = 0; i < 1000; i++) {
                // Determine Offset
                // If onlyMissing: as we process, they disappear from "Total=0" set. So offset 0 is correct.
                // If All: we update in place, so offset increases.
                let currentOffset = onlyMissing ? 0 : (i * BATCH_SIZE);

                const res = await fetch(`/api/lab/calculate?period=${period}&ticker=${ticker}&offset=${currentOffset}&limit=${BATCH_SIZE}&only_missing=${onlyMissing}`, {
                    method: 'POST'
                });
                const json = await res.json();
                if (json.status !== 'success') throw new Error(json.message);

                const count = json.updated_count || 0;
                totalProcessed += count;

                Swal.update({ html: `현재 <b>${totalProcessed}</b>개 처리 완료...<br>(Batch ${i + 1})` });

                if (count === 0 && json.message.includes("No rows")) break;
                if (count < BATCH_SIZE) break;
            }

            Swal.fire('채점 완료!', `총 ${totalProcessed}개 데이터 처리가 끝났습니다.`, 'success');
            fetchData();

        } catch (e) {
            Swal.fire('Error', e.message || 'Unknown error', 'error');
        }
        setLoading(false);
    };

    const handleDelete = async () => {
        if (selectedIds.length === 0) return;
        const result = await Swal.fire({
            title: '삭제',
            text: `선택한 ${selectedIds.length}개 데이터를 삭제합니다.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#ef4444',
            confirmButtonText: '삭제'
        });

        if (result.isConfirmed) {
            try {
                const ids = selectedIds.join(',');
                const res = await fetch(`/api/lab/data/${period}?ids=${ids}`, { method: 'DELETE' });
                const json = await res.json();
                if (json.status === 'success') {
                    Swal.fire('삭제 완료', json.message, 'success');
                    fetchData();
                } else {
                    Swal.fire('Error', json.message, 'error');
                }
            } catch (e) {
                Swal.fire('Error', 'Network error', 'error');
            }
        }
    };

    // File Upload Handler
    const onDrop = async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return;
        const file = acceptedFiles[0];
        setUploading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`/api/lab/upload?period=${period}&ticker=${ticker}`, {
                method: 'POST',
                body: formData
            });
            const json = await res.json();
            if (res.ok) {
                Swal.fire('업로드 성공', json.message, 'success');
                fetchData();
            } else {
                Swal.fire('업로드 실패', json.detail || 'Unknown error', 'error');
            }
        } catch (e) {
            Swal.fire('Error', 'Network error during upload', 'error');
        }
        setUploading(false);
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        multiple: false,
        accept: { 'application/vnd.ms-excel': ['.xls', '.xlsx'] }
    });

    const toggleSelect = (id) => {
        if (selectedIds.includes(id)) setSelectedIds(selectedIds.filter(x => x !== id));
        else setSelectedIds([...selectedIds, id]);
    };

    const toggleSelectAll = () => {
        if (selectedIds.length === data.length) setSelectedIds([]);
        else setSelectedIds(data.map(d => d.id));
    };

    return (
        <div style={{ padding: '20px', minHeight: '100vh', background: '#0f172a', color: '#fff' }}>
            {/* Header Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #334155', paddingBottom: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <h2 style={{ margin: 0, color: '#38bdf8' }}>🧪 Lab 2.0</h2>
                    <div style={{ display: 'flex', background: '#1e293b', borderRadius: '6px', padding: '6px 12px', fontSize: '0.9rem', color: '#94a3b8' }}>
                        <span>Analysis Source: <b>5m Candle</b> (Auto-30m Gen)</span>
                    </div>
                </div>

                {/* Right Actions */}
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {/* [Req] Ticker Select */}
                    <select
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value)}
                        style={{ background: '#1e293b', color: '#fff', padding: '6px 10px', borderRadius: '6px', border: '1px solid #475569', fontWeight: 'bold' }}
                    >
                        <option value="SOXL">SOXL</option>
                        <option value="SOXS">SOXS</option>
                        <option value="UPRO">UPRO</option>
                    </select>

                    <div {...getRootProps()} style={{ cursor: 'pointer', background: isDragActive ? '#334155' : '#1e293b', padding: '8px 12px', borderRadius: '6px', fontSize: '0.9rem', border: '1px dashed #64748b' }}>
                        <input {...getInputProps()} />
                        {uploading ? '⏳...' : '📁 Upload'}
                    </div>

                    <button onClick={handleCalculateAction} style={{ background: '#3b82f6', border: 'none', color: '#fff', padding: '8px 12px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', boxShadow: '0 2px 5px rgba(0,0,0,0.2)' }}>
                        ⚡ 채점 ({selectedIds.length > 0 ? selectedIds.length : 'All'})
                    </button>

                    <button onClick={() => fetchData()} style={{ background: '#334155', border: 'none', color: '#fff', padding: '8px', borderRadius: '6px', cursor: 'pointer' }}>
                        🔄
                    </button>
                </div>
            </div>

            {/* Filter & Pagination Bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={inputStyle} />
                    <span style={{ color: '#64748b' }}>~</span>
                    <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={inputStyle} />

                    {/* [Req] Status Filter */}
                    <div style={{ display: 'flex', background: '#1e293b', borderRadius: '4px', overflow: 'hidden', marginLeft: '10px' }}>
                        {['ALL', 'COMPLETE', 'INCOMPLETE'].map(st => (
                            <button
                                key={st}
                                onClick={() => setStatusFilter(st)}
                                style={{
                                    padding: '6px 12px', border: 'none', cursor: 'pointer', fontSize: '0.8rem',
                                    background: statusFilter === st ? '#64748b' : 'transparent',
                                    color: statusFilter === st ? '#fff' : '#94a3b8'
                                }}
                            >
                                {st === 'ALL' ? '전체' : st === 'COMPLETE' ? '완료' : '미완료'}
                            </button>
                        ))}
                    </div>

                    <button onClick={() => { setPage(1); fetchData(); }} style={btnStyle}>🔍 Search</button>
                </div>

                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {selectedIds.length > 0 && (
                        <button onClick={handleDelete} style={{ ...btnStyle, background: '#ef4444' }}>
                            🗑️ Delete ({selectedIds.length})
                        </button>
                    )}
                    <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                        Pg {pagination.page} / {pagination.total_pages} (T:{pagination.total})
                    </span>
                    <button disabled={page <= 1} onClick={() => setPage(page - 1)} style={pageBtnStyle}>◀</button>
                    <button disabled={page >= pagination.total_pages} onClick={() => setPage(page + 1)} style={pageBtnStyle}>▶</button>
                </div>
            </div>

            {/* Data Grid */}
            <div style={{ background: '#1e293b', borderRadius: '12px', overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                        <thead>
                            <tr style={{ background: '#0f172a', color: '#94a3b8' }}>
                                <th style={{ ...thStyle, width: '40px', textAlign: 'center' }}>
                                    <input type="checkbox" onChange={toggleSelectAll} checked={data.length > 0 && selectedIds.length === data.length} />
                                </th>
                                <th style={thStyle}>Status</th>
                                <th style={thStyle}>Time (US)</th>
                                <th style={thStyle}>Close</th>
                                <th style={thStyle}>Chg(%)</th>
                                <th style={{ ...thStyle, color: '#fbbf24' }}>Total</th>
                                <th style={thStyle}>C1</th>
                                <th style={thStyle}>C2</th>
                                <th style={thStyle}>C3</th>
                                <th style={thStyle}>Eng</th>
                                <th style={thStyle}>RSI</th>
                                <th style={thStyle}>MACD</th>
                                <th style={thStyle}>Vol</th>
                                <th style={thStyle}>ATR</th>
                                <th style={thStyle}>Ver</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.map((row) => {
                                // [Req] Highlight Red if Total != Sum
                                // Note: DB might include sell_penalty in total but not stored?
                                // Assuming Sum Match is expected.
                                const sum = (row.score_cheongan_1 || 0) + (row.score_cheongan_2 || 0) + (row.score_cheongan_3 || 0) +
                                    (row.score_energy || 0) + (row.score_rsi || 0) + (row.score_macd || 0) +
                                    (row.score_vol || 0) + (row.score_atr || 0);

                                // Loose check for sell_penalty? 
                                // [Req] Allow 1 point tolerance for rounding differences
                                const isMismatch = Math.abs(row.total_score - sum) > 1;
                                // If total is 0, it might just be uncalc. isMismatch might not be useful then.
                                // If uncalc, Sum is 0, Total 0 -> Match.
                                // If calc, Sum should match Total (unless penalty).
                                // User requested "Red" for mismatch.
                                // Let's highlight incomplete/mismatch.

                                const isSelected = selectedIds.includes(row.id);
                                const rowBg = isMismatch && row.total_score !== 0 ? 'rgba(239, 68, 68, 0.15)' : isSelected ? '#334155' : 'transparent';

                                return (
                                    <tr key={row.id} style={{ borderBottom: '1px solid #334155', background: rowBg }}>
                                        <td style={{ ...tdStyle, textAlign: 'center' }}>
                                            <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(row.id)} />
                                        </td>
                                        <td style={tdStyle}>
                                            {/* [Req] "updated" text instead of icon */}
                                            {row.calculated_at ? (
                                                <span style={{ color: '#4ade80', fontSize: '0.75rem' }}>updated</span>
                                            ) : (
                                                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>-</span>
                                            )}
                                        </td>
                                        <td style={tdStyle}>{new Date(row.candle_time).toLocaleString()}</td>
                                        <td style={tdStyle}>{row.close}</td>
                                        <td style={{ ...tdStyle, color: row.change_pct > 0 ? '#4ade80' : row.change_pct < 0 ? '#f87171' : '#fff' }}>
                                            {row.change_pct}%
                                        </td>
                                        <td style={{ ...tdStyle, color: isMismatch ? '#f87171' : '#fbbf24', fontWeight: 'bold' }}>{row.total_score}</td>
                                        <td style={tdStyle}>{row.score_cheongan_1}</td>
                                        <td style={tdStyle}>{row.score_cheongan_2}</td>
                                        <td style={tdStyle}>{row.score_cheongan_3}</td>
                                        <td style={tdStyle}>{row.score_energy}</td>
                                        <td style={tdStyle}>{row.score_rsi}</td>
                                        <td style={tdStyle}>{row.score_macd}</td>
                                        <td style={tdStyle}>{row.score_vol}</td>
                                        <td style={tdStyle}>{row.score_atr}</td>
                                        <td style={{ ...tdStyle, fontSize: '0.75rem', color: '#94a3b8' }}>{row.algo_version || '-'}</td>
                                    </tr>
                                );
                            })}
                            {data.length === 0 && (
                                <tr>
                                    <td colSpan="15" style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
                                        No data found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

const tabStyle = { padding: '6px 15px', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem' };
const btnStyle = { background: '#334155', border: 'none', color: '#fff', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer' };
const pageBtnStyle = { background: '#1e293b', border: '1px solid #475569', color: '#fff', width: '30px', height: '30px', borderRadius: '4px', cursor: 'pointer' };
const inputStyle = { background: '#1e293b', border: '1px solid #475569', color: '#fff', padding: '5px', borderRadius: '4px' };
const thStyle = { padding: '10px', textAlign: 'left', whiteSpace: 'nowrap' };
const tdStyle = { padding: '8px 10px', borderBottom: '1px solid #334155' };

export default LabPage;
