/**
 * TodayEventsWidget.jsx
 * 대시보드 상단 - 오늘의 이벤트 & 최근 Daily Report 위젯
 * Ver 5.8.2 - 다중 줄 지원 및 인라인 상세 패널로 개선
 */
import React, { useState, useEffect } from 'react';
import { Calendar, AlertCircle, FileText, TrendingUp, TrendingDown, X, Edit3, Clock, Image, ChevronDown, ChevronUp } from 'lucide-react';
import '../index.css';

const TodayEventsWidget = () => {
    const [events, setEvents] = useState([]);
    const [recentReport, setRecentReport] = useState(null);
    const [loading, setLoading] = useState(true);

    // 인라인 상세 패널 상태
    const [expandedEvent, setExpandedEvent] = useState(null);
    const [expandedReport, setExpandedReport] = useState(false);

    // 데이터 로드
    const fetchData = async () => {
        try {
            const evtRes = await fetch('/api/market-events/today');
            if (evtRes.ok) setEvents(await evtRes.json());

            const repRes = await fetch('/api/daily-reports?limit=5');
            if (repRes.ok) {
                const reports = await repRes.json();
                if (reports.length > 0) {
                    const today = new Date().toISOString().split('T')[0];
                    const todayReport = reports.find(r => r.report_date === today);
                    setRecentReport(todayReport || reports[0]);
                }
            }
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    // 이벤트 토글
    const toggleEvent = (eventId) => {
        setExpandedEvent(expandedEvent === eventId ? null : eventId);
        setExpandedReport(false); // 리포트 패널 닫기
    };

    // 리포트 토글
    const toggleReport = () => {
        setExpandedReport(!expandedReport);
        setExpandedEvent(null); // 이벤트 패널 닫기
    };

    // 수익률 색상
    const getProfitColor = (rate) => {
        const num = parseFloat(rate || 0);
        if (num > 0) return '#f87171';
        if (num < 0) return '#60a5fa';
        return '#94a3b8';
    };

    // 중요도 스타일
    const getImportanceStyle = (importance) => {
        const styles = {
            HIGH: { bg: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.3)', label: '🔴 높음' },
            MEDIUM: { bg: 'rgba(249, 115, 22, 0.15)', color: '#fdba74', border: '1px solid rgba(249, 115, 22, 0.3)', label: '🟠 보통' },
            LOW: { bg: 'rgba(59, 130, 246, 0.15)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.3)', label: '🔵 낮음' }
        };
        return styles[importance] || styles.LOW;
    };

    if (loading) return null;
    if (events.length === 0 && !recentReport) return null;

    const profitRate = parseFloat(recentReport?.profit_rate || 0);
    const selectedEvent = events.find(e => e.id === expandedEvent);

    return (
        <div style={{ position: 'relative', zIndex: 20 }}>
            {/* 메인 위젯 바 */}
            <div style={{
                background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                padding: '12px 20px',
                backdropFilter: 'blur(10px)'
            }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
                    {/* 이벤트 섹션 */}
                    {events.length > 0 && (
                        <div style={{ flex: 1, minWidth: '300px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                <AlertCircle size={14} color="#f87171" />
                                <span style={{ fontSize: '0.8rem', color: '#f87171', fontWeight: 'bold' }}>오늘 이벤트 ({events.length})</span>
                            </div>
                            {/* 이벤트 배지들 - 여러 줄 허용 */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {events.map((evt) => {
                                    const style = getImportanceStyle(evt.importance);
                                    const isExpanded = expandedEvent === evt.id;
                                    return (
                                        <div
                                            key={evt.id}
                                            onClick={() => toggleEvent(evt.id)}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: '6px',
                                                padding: '5px 12px', borderRadius: '16px',
                                                fontSize: '0.8rem', fontWeight: '500',
                                                background: isExpanded ? style.color : style.bg,
                                                color: isExpanded ? '#0f172a' : style.color,
                                                border: style.border,
                                                cursor: 'pointer', transition: 'all 0.2s',
                                                boxShadow: isExpanded ? '0 2px 8px rgba(0,0,0,0.3)' : 'none'
                                            }}
                                        >
                                            {evt.event_time && <span style={{ opacity: 0.8, fontSize: '0.75rem' }}>{evt.event_time.slice(0, 5)}</span>}
                                            <span>{evt.title}</span>
                                            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* 리포트 섹션 */}
                    {recentReport && (
                        <div
                            onClick={toggleReport}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '10px',
                                padding: '8px 14px', borderRadius: '12px',
                                background: expandedReport ? 'rgba(99, 102, 241, 0.3)' : 'rgba(99, 102, 241, 0.1)',
                                border: '1px solid rgba(99, 102, 241, 0.3)',
                                cursor: 'pointer', transition: 'all 0.2s'
                            }}
                        >
                            <FileText size={14} color="#a5b4fc" />
                            <span style={{ fontSize: '0.8rem', color: '#a5b4fc', fontWeight: '600' }}>
                                {recentReport.report_date === new Date().toISOString().split('T')[0] ? '오늘' : recentReport.report_date.slice(5)}
                            </span>
                            <span style={{ fontSize: '0.95rem', fontWeight: 'bold', color: getProfitColor(profitRate), fontFamily: 'monospace' }}>
                                {profitRate > 0 ? '+' : ''}{profitRate.toFixed(2)}%
                            </span>
                            {expandedReport ? <ChevronUp size={12} color="#a5b4fc" /> : <ChevronDown size={12} color="#a5b4fc" />}
                        </div>
                    )}

                    {/* 전체 보기 링크 */}
                    <a href="/daily-reports" style={{
                        display: 'flex', alignItems: 'center', gap: '4px',
                        fontSize: '0.75rem', color: '#64748b', textDecoration: 'none',
                        padding: '8px 12px', borderRadius: '8px',
                        background: 'rgba(255,255,255,0.03)'
                    }}>
                        <Calendar size={12} /> 전체
                    </a>
                </div>
            </div>

            {/* 인라인 상세 패널 - 이벤트 */}
            {selectedEvent && (
                <div style={{
                    background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '16px 20px',
                    animation: 'slideDown 0.2s ease-out'
                }}>
                    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <span style={{
                                    padding: '3px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 'bold',
                                    background: getImportanceStyle(selectedEvent.importance).bg,
                                    color: getImportanceStyle(selectedEvent.importance).color,
                                    border: getImportanceStyle(selectedEvent.importance).border
                                }}>
                                    {getImportanceStyle(selectedEvent.importance).label}
                                </span>
                                {selectedEvent.event_time && (
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#94a3b8', fontSize: '0.85rem' }}>
                                        <Clock size={12} /> {selectedEvent.event_time.slice(0, 5)}
                                    </span>
                                )}
                                <span style={{ color: '#64748b', fontSize: '0.8rem' }}>📅 {selectedEvent.event_date}</span>
                            </div>
                            <button onClick={() => setExpandedEvent(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}>
                                <X size={16} />
                            </button>
                        </div>
                        <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', fontWeight: 'bold', color: 'white' }}>{selectedEvent.title}</h4>
                        {selectedEvent.description && (
                            <p style={{ margin: 0, fontSize: '0.9rem', color: '#cbd5e1', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                                {selectedEvent.description}
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* 인라인 상세 패널 - 리포트 */}
            {expandedReport && recentReport && (
                <div style={{
                    background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '16px 20px',
                    animation: 'slideDown 0.2s ease-out'
                }}>
                    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: '#a5b4fc' }}>📅 {recentReport.report_date}</span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 10px', borderRadius: '8px', background: 'rgba(15, 23, 42, 0.6)' }}>
                                    {profitRate > 0 ? <TrendingUp size={14} color="#f87171" /> : profitRate < 0 ? <TrendingDown size={14} color="#60a5fa" /> : null}
                                    <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: getProfitColor(profitRate), fontFamily: 'monospace' }}>
                                        {profitRate > 0 ? '+' : ''}{profitRate.toFixed(2)}%
                                    </span>
                                </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <a href="/daily-reports" style={{
                                    display: 'flex', alignItems: 'center', gap: '4px',
                                    fontSize: '0.8rem', color: '#a5b4fc', textDecoration: 'none',
                                    padding: '4px 10px', borderRadius: '6px',
                                    background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.2)'
                                }}>
                                    <Edit3 size={12} /> 수정
                                </a>
                                <button onClick={() => setExpandedReport(false)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}>
                                    <X size={16} />
                                </button>
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                            {/* 장전 전략 */}
                            <div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#34d399', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }}></span>
                                    🎯 장전 전략
                                </div>
                                <div style={{
                                    background: 'rgba(15, 23, 42, 0.5)', padding: '10px 12px', borderRadius: '8px',
                                    color: '#e2e8f0', fontSize: '0.85rem', lineHeight: '1.5', whiteSpace: 'pre-wrap',
                                    borderLeft: '2px solid #10b981', maxHeight: '100px', overflowY: 'auto'
                                }}>
                                    {recentReport.pre_market_strategy || '(미입력)'}
                                </div>
                            </div>

                            {/* 장후 피드백 */}
                            <div>
                                <div style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#fbbf24', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#f59e0b' }}></span>
                                    📝 장후 피드백
                                </div>
                                <div style={{
                                    background: 'rgba(15, 23, 42, 0.5)', padding: '10px 12px', borderRadius: '8px',
                                    color: '#e2e8f0', fontSize: '0.85rem', lineHeight: '1.5', whiteSpace: 'pre-wrap',
                                    borderLeft: '2px solid #f59e0b', maxHeight: '100px', overflowY: 'auto'
                                }}>
                                    {recentReport.post_market_memo || '(미입력)'}
                                </div>
                            </div>
                        </div>

                        {/* 첨부 이미지 */}
                        {recentReport.image_paths && recentReport.image_paths.length > 0 && (
                            <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Image size={12} color="#a78bfa" />
                                <span style={{ fontSize: '0.75rem', color: '#a78bfa' }}>첨부 {recentReport.image_paths.length}개</span>
                                <div style={{ display: 'flex', gap: '6px' }}>
                                    {recentReport.image_paths.slice(0, 4).map((img, idx) => (
                                        <img
                                            key={idx}
                                            src={img}
                                            alt={`첨부 ${idx + 1}`}
                                            style={{ width: '40px', height: '40px', objectFit: 'cover', borderRadius: '4px', cursor: 'pointer', border: '1px solid #334155' }}
                                            onClick={() => window.open(img, '_blank')}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 애니메이션 CSS */}
            <style>{`
                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default TodayEventsWidget;
