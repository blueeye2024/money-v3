/**
 * DailyReportPage.jsx
 * 일일 리포트 & 마켓 이벤트 관리 페이지
 * Ver 5.8.2 - 캘린더 이벤트 UI 개선 (flex-wrap, 인라인 패널)
 * 
 * 구조:
 * - 왼쪽: 캘린더 + 이벤트 목록
 * - 오른쪽: 리포트 리스트 (기본) / 뷰어 (클릭 시) / 에디터 (작성/수정 시)
 */
import React, { useState, useEffect } from 'react';
import EventCalendar from './components/EventCalendar';
import { Plus, Trash2, Calendar as CalIcon, FileText, Edit3, Eye, ArrowLeft, Save, Upload, X, Image } from 'lucide-react';
import Swal from 'sweetalert2';

const DailyReportPage = () => {
    // 기본 상태
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [reports, setReports] = useState([]);
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    // 뷰 모드: 'list' | 'view' | 'edit'
    const [viewMode, setViewMode] = useState('list');
    const [viewingReport, setViewingReport] = useState(null);

    // 에디터 폼 상태
    const [editForm, setEditForm] = useState({
        report_date: '',
        pre_market_strategy: '',
        post_market_memo: '',
        profit_rate: '',
        existing_images: [],
        new_images: [],
        image_previews: []
    });

    // 데이터 로드
    const fetchData = async () => {
        setLoading(true);
        try {
            const repRes = await fetch('/api/daily-reports');
            if (repRes.ok) setReports(await repRes.json());

            const sDate = new Date(selectedDate);
            const evtRes = await fetch(`/api/market-events?year=${sDate.getFullYear()}&month=${sDate.getMonth() + 1}`);
            if (evtRes.ok) setEvents(await evtRes.json());
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [selectedDate]);

    // 현재 선택된 날짜의 데이터
    const currentEvents = events.filter(e => e.event_date === selectedDate);
    const selectedReport = reports.find(r => r.report_date === selectedDate);

    // ========== 이벤트 핸들러 ==========

    // 리포트 보기
    const handleViewReport = (report) => {
        setViewingReport(report);
        setViewMode('view');
    };

    // 새 리포트 작성
    const handleNewReport = (date = selectedDate) => {
        setEditForm({
            report_date: date,
            pre_market_strategy: '',
            post_market_memo: '',
            profit_rate: '',
            existing_images: [],
            new_images: [],
            image_previews: []
        });
        setViewMode('edit');
    };

    // 리포트 수정
    const handleEditReport = (report) => {
        setEditForm({
            report_date: report.report_date,
            pre_market_strategy: report.pre_market_strategy || '',
            post_market_memo: report.post_market_memo || '',
            profit_rate: report.profit_rate || '',
            existing_images: report.image_paths || [],
            new_images: [],
            image_previews: []
        });
        setViewMode('edit');
    };

    // 리포트 저장
    const handleSaveReport = async () => {
        try {
            const formData = new FormData();
            formData.append('report_date', editForm.report_date);
            formData.append('pre_market_strategy', editForm.pre_market_strategy);
            formData.append('post_market_memo', editForm.post_market_memo);
            formData.append('profit_rate', editForm.profit_rate || '0');
            formData.append('existing_images', JSON.stringify(editForm.existing_images));
            editForm.new_images.forEach(file => formData.append('new_images', file));

            const res = await fetch('/api/daily-reports', { method: 'POST', body: formData });
            if (!res.ok) throw new Error("저장 실패");

            await Swal.fire({
                icon: 'success', title: '저장 완료!',
                text: '리포트가 성공적으로 저장되었습니다.',
                timer: 1500, showConfirmButton: false
            });

            await fetchData();
            setViewMode('list');
        } catch (e) {
            Swal.fire('오류', e.message, 'error');
        }
    };

    // 리포트 삭제
    const handleDeleteReport = async (dateStr) => {
        const result = await Swal.fire({
            title: '리포트 삭제',
            text: `${dateStr} 리포트를 삭제하시겠습니까?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#ef4444',
            confirmButtonText: '삭제',
            cancelButtonText: '취소'
        });

        if (result.isConfirmed) {
            await fetch(`/api/daily-reports/${dateStr}`, { method: 'DELETE' });
            await fetchData();
            setViewMode('list');
        }
    };

    // 목록으로 돌아가기
    const handleBackToList = () => {
        setViewMode('list');
        setViewingReport(null);
    };

    // 이미지 핸들러
    const handleImageChange = (e) => {
        if (e.target.files) {
            const files = Array.from(e.target.files);
            const newPreviews = files.map(file => URL.createObjectURL(file));
            setEditForm(prev => ({
                ...prev,
                new_images: [...prev.new_images, ...files],
                image_previews: [...prev.image_previews, ...newPreviews]
            }));
        }
    };

    const removeNewImage = (idx) => {
        setEditForm(prev => ({
            ...prev,
            new_images: prev.new_images.filter((_, i) => i !== idx),
            image_previews: prev.image_previews.filter((_, i) => i !== idx)
        }));
    };

    const removeExistingImage = (idx) => {
        setEditForm(prev => ({
            ...prev,
            existing_images: prev.existing_images.filter((_, i) => i !== idx)
        }));
    };

    // 이벤트 추가/삭제
    const handleAddEvent = async () => {
        const { value: formValues } = await Swal.fire({
            title: '새 이벤트 추가',
            html: `
                <div style="text-align: left; display: flex; flex-direction: column; gap: 10px;">
                    <label style="font-size: 0.9rem; font-weight: bold; color: #333;">제목</label>
                    <input id="evt-title" class="swal2-input" placeholder="예: CPI 발표" style="margin: 0; width: 100%;">
                    
                    <label style="font-size: 0.9rem; font-weight: bold; color: #333;">시간 (선택)</label>
                    <input id="evt-time" type="time" class="swal2-input" style="margin: 0; width: 100%;">
                    
                    <label style="font-size: 0.9rem; font-weight: bold; color: #333;">설명</label>
                    <textarea id="evt-desc" class="swal2-textarea" placeholder="상세 내용..." style="margin: 0; width: 100%; height: 80px; resize: none;"></textarea>
                    
                    <label style="font-size: 0.9rem; font-weight: bold; color: #333;">중요도</label>
                    <select id="evt-imp" class="swal2-select" style="margin: 0; width: 100%;">
                        <option value="HIGH">높음 (빨강)</option>
                        <option value="MEDIUM" selected>보통 (주황)</option>
                        <option value="LOW">낮음 (파랑)</option>
                    </select>
                </div>
            `,
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: '추가',
            cancelButtonText: '취소',
            preConfirm: () => {
                const title = document.getElementById('evt-title').value;
                const time = document.getElementById('evt-time').value;
                const desc = document.getElementById('evt-desc').value;
                const imp = document.getElementById('evt-imp').value;
                if (!title) Swal.showValidationMessage('제목을 입력해주세요');
                return { title, time, desc, imp };
            }
        });

        if (formValues) {
            await fetch('/api/market-events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    event_date: selectedDate,
                    event_time: formValues.time,
                    title: formValues.title,
                    description: formValues.desc,
                    importance: formValues.imp
                })
            });
            fetchData();
        }
    };

    const handleDeleteEvent = async (id) => {
        if (confirm("이 이벤트를 삭제하시겠습니까?")) {
            await fetch(`/api/market-events/${id}`, { method: 'DELETE' });
            fetchData();
        }
    };

    // ========== 렌더링 ==========

    // 리포트 리스트 렌더링
    const renderReportList = () => {
        const sortedReports = [...reports].sort((a, b) => b.report_date.localeCompare(a.report_date));

        return (
            <div className="glass-panel" style={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* 헤더 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '16px' }}>
                    <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 'bold', color: 'white', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <FileText size={22} color="var(--accent-blue)" />
                        일일 리포트
                    </h2>
                    <button
                        onClick={() => handleNewReport()}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '6px',
                            background: 'var(--accent-blue)', color: 'white',
                            padding: '8px 16px', borderRadius: '8px', border: 'none',
                            fontWeight: 'bold', cursor: 'pointer', fontSize: '0.9rem'
                        }}
                    >
                        <Plus size={16} /> 새 리포트 작성
                    </button>
                </div>

                {/* 리스트 */}
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {sortedReports.length === 0 ? (
                        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '60px 20px' }}>
                            <FileText size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
                            <p style={{ margin: 0 }}>작성된 리포트가 없습니다</p>
                            <p style={{ margin: '8px 0 0', fontSize: '0.85rem' }}>위의 "새 리포트 작성" 버튼을 눌러 시작하세요</p>
                        </div>
                    ) : (
                        sortedReports.map(report => {
                            const profitRate = parseFloat(report.profit_rate || 0);
                            const profitColor = profitRate > 0 ? '#f87171' : profitRate < 0 ? '#60a5fa' : '#94a3b8';
                            const hasImages = report.image_paths && report.image_paths.length > 0;

                            return (
                                <div
                                    key={report.report_date}
                                    onClick={() => handleViewReport(report)}
                                    style={{
                                        background: 'rgba(30, 41, 59, 0.4)',
                                        padding: '16px', borderRadius: '12px',
                                        border: report.report_date === selectedDate ? '1px solid var(--accent-blue)' : '1px solid rgba(255,255,255,0.05)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                                                <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'white', fontFamily: 'monospace' }}>
                                                    {report.report_date}
                                                </span>
                                                {hasImages && <Image size={14} color="#a78bfa" />}
                                            </div>
                                            <p style={{
                                                margin: 0, fontSize: '0.85rem', color: '#94a3b8',
                                                overflow: 'hidden', textOverflow: 'ellipsis',
                                                display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'
                                            }}>
                                                {report.pre_market_strategy || '(전략 미입력)'}
                                            </p>
                                        </div>
                                        <div style={{ textAlign: 'right', minWidth: '80px' }}>
                                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: profitColor }}>
                                                {profitRate > 0 ? '+' : ''}{profitRate.toFixed(2)}%
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                                                수익률
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        );
    };

    // 리포트 뷰어 렌더링
    const renderReportViewer = () => {
        if (!viewingReport) return null;

        const profitRate = parseFloat(viewingReport.profit_rate || 0);
        const profitColor = profitRate > 0 ? '#f87171' : profitRate < 0 ? '#60a5fa' : '#94a3b8';
        const images = viewingReport.image_paths || [];

        return (
            <div className="glass-panel" style={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* 헤더 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <button
                            onClick={handleBackToList}
                            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                        >
                            <ArrowLeft size={20} />
                        </button>
                        <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 'bold', color: 'white' }}>
                            📄 {viewingReport.report_date}
                        </h2>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            onClick={() => handleEditReport(viewingReport)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '6px',
                                background: 'rgba(255,255,255,0.1)', color: 'white',
                                padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)',
                                cursor: 'pointer', fontSize: '0.85rem'
                            }}
                        >
                            <Edit3 size={14} /> 수정
                        </button>
                        <button
                            onClick={() => handleDeleteReport(viewingReport.report_date)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '6px',
                                background: 'rgba(239, 68, 68, 0.1)', color: '#f87171',
                                padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)',
                                cursor: 'pointer', fontSize: '0.85rem'
                            }}
                        >
                            <Trash2 size={14} /> 삭제
                        </button>
                    </div>
                </div>

                {/* 컨텐츠 */}
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {/* 수익률 */}
                    <div style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '16px', borderRadius: '12px', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '8px' }}>일일 수익률</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: profitColor }}>
                            {profitRate > 0 ? '+' : ''}{profitRate.toFixed(2)}%
                        </div>
                    </div>

                    {/* 전략 */}
                    <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#34d399', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }}></span>
                            🎯 장전 전략 (Pre-Market Strategy)
                        </div>
                        <div style={{
                            background: 'rgba(15, 23, 42, 0.4)', padding: '16px', borderRadius: '8px',
                            color: '#e2e8f0', lineHeight: '1.6', whiteSpace: 'pre-wrap', minHeight: '80px'
                        }}>
                            {viewingReport.pre_market_strategy || '(미입력)'}
                        </div>
                    </div>

                    {/* 피드백 */}
                    <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#fbbf24', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }}></span>
                            📝 장후 피드백 (Post-Market Feedback)
                        </div>
                        <div style={{
                            background: 'rgba(15, 23, 42, 0.4)', padding: '16px', borderRadius: '8px',
                            color: '#e2e8f0', lineHeight: '1.6', whiteSpace: 'pre-wrap', minHeight: '80px'
                        }}>
                            {viewingReport.post_market_memo || '(미입력)'}
                        </div>
                    </div>

                    {/* 이미지 */}
                    {images.length > 0 && (
                        <div>
                            <div style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#a78bfa', marginBottom: '10px' }}>
                                🖼 첨부 이미지 ({images.length}개)
                            </div>
                            <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', padding: '12px', background: 'rgba(2, 6, 23, 0.3)', borderRadius: '12px' }}>
                                {images.map((img, idx) => (
                                    <img
                                        key={idx}
                                        src={img}
                                        alt={`첨부 ${idx + 1}`}
                                        style={{ width: '120px', height: '120px', objectFit: 'cover', borderRadius: '8px', cursor: 'pointer', border: '1px solid #334155' }}
                                        onClick={() => window.open(img, '_blank')}
                                    />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    // 리포트 에디터 렌더링
    const renderReportEditor = () => {
        const isEditing = reports.some(r => r.report_date === editForm.report_date);

        return (
            <div className="glass-panel" style={{ padding: '24px', height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* 헤더 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <button
                            onClick={handleBackToList}
                            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                        >
                            <ArrowLeft size={20} />
                        </button>
                        <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 'bold', color: 'white' }}>
                            {isEditing ? '📝 리포트 수정' : '✏️ 새 리포트 작성'}
                        </h2>
                    </div>
                    <button
                        onClick={handleSaveReport}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '6px',
                            background: '#2563eb', color: 'white',
                            padding: '10px 20px', borderRadius: '8px', border: 'none',
                            fontWeight: 'bold', cursor: 'pointer', fontSize: '0.9rem',
                            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)'
                        }}
                    >
                        <Save size={16} /> 저장하기
                    </button>
                </div>

                {/* 폼 */}
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {/* 날짜 */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 'bold', color: '#60a5fa', marginBottom: '8px' }}>
                            📅 날짜
                        </label>
                        <input
                            type="date"
                            value={editForm.report_date}
                            onChange={(e) => setEditForm(prev => ({ ...prev, report_date: e.target.value }))}
                            style={{
                                width: '100%', padding: '12px 16px',
                                background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)',
                                borderRadius: '10px', color: '#e2e8f0', fontSize: '1rem'
                            }}
                        />
                    </div>

                    {/* 수익률 */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 'bold', color: '#60a5fa', marginBottom: '8px' }}>
                            💰 일일 수익률 (%)
                        </label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="number"
                                step="0.01"
                                placeholder="0.00"
                                value={editForm.profit_rate}
                                onChange={(e) => setEditForm(prev => ({ ...prev, profit_rate: e.target.value }))}
                                style={{
                                    width: '100%', padding: '12px 16px',
                                    background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)',
                                    borderRadius: '10px', fontSize: '1.1rem', fontFamily: 'monospace',
                                    color: parseFloat(editForm.profit_rate) > 0 ? '#f87171' : parseFloat(editForm.profit_rate) < 0 ? '#60a5fa' : '#e2e8f0'
                                }}
                            />
                            <span style={{ position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)', color: '#64748b', fontWeight: 'bold' }}>%</span>
                        </div>
                    </div>

                    {/* 전략 */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 'bold', color: '#34d399', marginBottom: '8px' }}>
                            🎯 장전 전략 (Pre-Market Strategy)
                        </label>
                        <textarea
                            placeholder="오늘의 매매 계획, 시나리오, 리스크 관리 방안..."
                            value={editForm.pre_market_strategy}
                            onChange={(e) => setEditForm(prev => ({ ...prev, pre_market_strategy: e.target.value }))}
                            style={{
                                width: '100%', height: '120px', padding: '12px 16px',
                                background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)',
                                borderRadius: '10px', color: '#e2e8f0', resize: 'none', lineHeight: '1.5'
                            }}
                        />
                    </div>

                    {/* 피드백 */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 'bold', color: '#fbbf24', marginBottom: '8px' }}>
                            📝 장후 피드백 (Post-Market Feedback)
                        </label>
                        <textarea
                            placeholder="실제 매매 결과, 심리 복기, 교훈..."
                            value={editForm.post_market_memo}
                            onChange={(e) => setEditForm(prev => ({ ...prev, post_market_memo: e.target.value }))}
                            style={{
                                width: '100%', height: '120px', padding: '12px 16px',
                                background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)',
                                borderRadius: '10px', color: '#e2e8f0', resize: 'none', lineHeight: '1.5'
                            }}
                        />
                    </div>

                    {/* 이미지 업로드 */}
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 'bold', color: '#a78bfa', marginBottom: '8px' }}>
                            🖼 첨부 이미지
                        </label>
                        <label style={{
                            display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px',
                            padding: '16px', cursor: 'pointer',
                            background: 'rgba(15, 23, 42, 0.6)', border: '1px dashed #475569',
                            borderRadius: '10px', color: '#94a3b8', transition: 'all 0.2s'
                        }}>
                            <Upload size={18} /> 이미지 업로드
                            <input type="file" multiple accept="image/*" style={{ display: 'none' }} onChange={handleImageChange} />
                        </label>

                        {/* 이미지 미리보기 */}
                        {(editForm.existing_images.length > 0 || editForm.image_previews.length > 0) && (
                            <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', padding: '12px', marginTop: '12px', background: 'rgba(2, 6, 23, 0.3)', borderRadius: '12px' }}>
                                {editForm.existing_images.map((img, idx) => (
                                    <div key={`exist-${idx}`} style={{ position: 'relative', width: '80px', height: '80px', flexShrink: 0 }}>
                                        <img src={img} alt="첨부" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid #334155' }} />
                                        <button
                                            type="button"
                                            onClick={() => removeExistingImage(idx)}
                                            style={{ position: 'absolute', top: '-6px', right: '-6px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', fontSize: '10px' }}
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))}
                                {editForm.image_previews.map((src, idx) => (
                                    <div key={`new-${idx}`} style={{ position: 'relative', width: '80px', height: '80px', flexShrink: 0 }}>
                                        <img src={src} alt="미리보기" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid #a855f7', opacity: 0.8 }} />
                                        <button
                                            type="button"
                                            onClick={() => removeNewImage(idx)}
                                            style={{ position: 'absolute', top: '-6px', right: '-6px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', fontSize: '10px' }}
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // 메인 렌더
    return (
        <div style={{ minHeight: '100vh', padding: '100px 20px 40px 20px', background: 'var(--bg-primary)' }}>
            <div className="container" style={{ maxWidth: '1400px', margin: '0 auto' }}>
                {/* 페이지 타이틀 */}
                <div style={{ marginBottom: '24px' }}>
                    <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: 'white', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
                        📊 일일 리포트 & 이벤트 관리
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '8px', fontSize: '0.95rem' }}>
                        매일의 매매 전략과 결과를 기록하고, 마켓 이벤트를 관리합니다.
                    </p>
                </div>

                <div className="responsive-grid-1-2">
                    {/* 왼쪽: 캘린더 & 이벤트 목록 */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        <EventCalendar
                            reports={reports}
                            events={events}
                            selectedDate={selectedDate}
                            onDateClick={(d) => {
                                setSelectedDate(d);
                            }}
                            onAddEvent={(date) => {
                                setSelectedDate(date);
                                handleAddEvent();
                            }}
                            onDeleteEvent={handleDeleteEvent}
                        />

                        {/* 이벤트 목록 */}
                        <div className="glass-panel" style={{ padding: '20px', minHeight: '280px', display: 'flex', flexDirection: 'column' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '10px' }}>
                                <h3 style={{ margin: 0, fontWeight: 'bold', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem' }}>
                                    <CalIcon size={18} color="var(--accent-blue)" />
                                    {selectedDate} 이벤트
                                </h3>
                                <button onClick={handleAddEvent} style={{
                                    background: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-blue)',
                                    border: 'none', borderRadius: '8px', padding: '6px 10px', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem'
                                }}>
                                    <Plus size={14} /> 추가
                                </button>
                            </div>
                            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {currentEvents.length === 0 && (
                                    <div style={{ color: 'var(--text-secondary)', textAlign: 'center', margin: '40px 0', fontStyle: 'italic', fontSize: '0.9rem' }}>
                                        예정된 이벤트 없음
                                    </div>
                                )}
                                {currentEvents.map(evt => (
                                    <div key={evt.id} style={{
                                        background: 'rgba(30, 41, 59, 0.4)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)',
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                                    }}>
                                        <div>
                                            <div style={{
                                                fontSize: '0.9rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px',
                                                color: evt.importance === 'HIGH' ? '#f87171' : evt.importance === 'MEDIUM' ? '#fbbf24' : '#60a5fa'
                                            }}>
                                                {evt.event_time && <span style={{ background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8em', color: '#cbd5e1' }}>{evt.event_time.slice(0, 5)}</span>}
                                                {evt.title}
                                            </div>
                                            {evt.description && <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px', whiteSpace: 'pre-wrap' }}>{evt.description}</div>}
                                        </div>
                                        <button onClick={() => handleDeleteEvent(evt.id)} style={{ color: '#64748b', background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}>
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* 오른쪽: 리포트 영역 (리스트 / 뷰어 / 에디터) */}
                    <div style={{ minHeight: '600px' }}>
                        {viewMode === 'list' && renderReportList()}
                        {viewMode === 'view' && renderReportViewer()}
                        {viewMode === 'edit' && renderReportEditor()}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DailyReportPage;
