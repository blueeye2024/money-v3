import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, X, Trash2, Plus } from 'lucide-react';

const EventCalendar = ({ reports, events, selectedDate, onDateClick, onAddEvent, onDeleteEvent }) => {
    const [viewDate, setViewDate] = useState(new Date());
    const [expandedDate, setExpandedDate] = useState(null);
    const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0 });
    const calendarRef = useRef(null);

    const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
    const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

    const currentYear = viewDate.getFullYear();
    const currentMonth = viewDate.getMonth();
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

    const prevMonth = () => setViewDate(new Date(currentYear, currentMonth - 1, 1));
    const nextMonth = () => setViewDate(new Date(currentYear, currentMonth + 1, 1));

    const formatDate = (year, month, day) => `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    // 외부 클릭 시 패널 닫기
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (calendarRef.current && !calendarRef.current.contains(e.target)) {
                setExpandedDate(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // 날짜 클릭 핸들러
    const handleDayClick = (dateStr, e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const calendarRect = calendarRef.current?.getBoundingClientRect();

        if (calendarRect) {
            setPanelPosition({
                top: rect.bottom - calendarRect.top + 4,
                left: Math.min(rect.left - calendarRect.left, calendarRect.width - 280)
            });
        }

        if (expandedDate === dateStr) {
            setExpandedDate(null);
        } else {
            setExpandedDate(dateStr);
        }
        onDateClick(dateStr);
    };

    const renderDays = () => {
        const days = [];
        // Empty slots
        for (let i = 0; i < firstDay; i++) {
            days.push(<div key={`empty-${i}`} style={{ height: '80px', background: 'rgba(15, 23, 42, 0.3)', border: '1px solid rgba(148, 163, 184, 0.05)' }}></div>);
        }

        // Days
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = formatDate(currentYear, currentMonth, d);
            const isSelected = selectedDate === dateStr;
            const isExpanded = expandedDate === dateStr;
            const today = new Date();
            const isToday = dateStr === formatDate(today.getFullYear(), today.getMonth(), today.getDate());

            const hasReport = reports.find(r => r.report_date === dateStr);
            const dayEvents = events.filter(e => e.event_date === dateStr);

            // Dot Logic
            let eventColor = null;
            if (dayEvents.length > 0) {
                if (dayEvents.some(e => e.importance === 'HIGH')) eventColor = '#ef4444'; // red
                else if (dayEvents.some(e => e.importance === 'MEDIUM')) eventColor = '#f97316'; // orange
                else eventColor = '#3b82f6'; // blue
            }

            days.push(
                <div
                    key={d}
                    onClick={(e) => handleDayClick(dateStr, e)}
                    style={{
                        minHeight: '80px', padding: '8px', cursor: 'pointer', position: 'relative',
                        background: isExpanded ? 'rgba(56, 189, 248, 0.25)' : isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                        border: isExpanded ? '1px solid #38bdf8' : isSelected ? '1px solid rgba(56, 189, 248, 0.5)' : '1px solid rgba(148, 163, 184, 0.1)',
                        transition: 'all 0.2s'
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                        <span style={{
                            fontSize: '0.85rem', fontWeight: 'bold', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%',
                            background: isToday ? '#2563eb' : 'transparent', color: isToday ? '#fff' : '#94a3b8'
                        }}>
                            {d}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                            {hasReport && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 5px rgba(16,185,129,0.5)' }} title="Report Written" />}
                            {eventColor && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: eventColor, boxShadow: `0 0 5px ${eventColor}` }} title="Events" />}
                            {dayEvents.length > 0 && (
                                <span style={{ fontSize: '0.6rem', color: '#64748b', fontWeight: 'bold' }}>
                                    {dayEvents.length}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* 이벤트 표시: flex-wrap으로 여러 줄 */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px' }}>
                        {dayEvents.map((e, idx) => (
                            <div key={idx} style={{
                                fontSize: '0.6rem', padding: '1px 4px', borderRadius: '3px',
                                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                                maxWidth: '100%',
                                background: e.importance === 'HIGH' ? 'rgba(239, 68, 68, 0.2)' : e.importance === 'MEDIUM' ? 'rgba(249, 115, 22, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                color: e.importance === 'HIGH' ? '#fca5a5' : e.importance === 'MEDIUM' ? '#fdba74' : '#93c5fd',
                                borderLeft: `2px solid ${e.importance === 'HIGH' ? '#ef4444' : e.importance === 'MEDIUM' ? '#f97316' : '#3b82f6'}`
                            }}>
                                {e.title.length > 8 ? e.title.slice(0, 8) + '..' : e.title}
                            </div>
                        ))}
                    </div>
                </div>
            );
        }
        return days;
    };

    // 확장된 날짜의 이벤트들
    const expandedEvents = expandedDate ? events.filter(e => e.event_date === expandedDate) : [];
    const expandedReport = expandedDate ? reports.find(r => r.report_date === expandedDate) : null;

    return (
        <div className="glass-panel" style={{ padding: '0', overflow: 'visible', position: 'relative' }} ref={calendarRef}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderBottom: '1px solid var(--glass-border)', background: 'rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button onClick={prevMonth} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><ChevronLeft size={20} /></button>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fff' }}>
                        {viewDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </div>
                    <button onClick={nextMonth} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><ChevronRight size={20} /></button>
                </div>
                <button onClick={() => { const t = new Date(); setViewDate(t); onDateClick(formatDate(t.getFullYear(), t.getMonth(), t.getDate())); }}
                    style={{ fontSize: '0.8rem', padding: '4px 12px', borderRadius: '20px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', cursor: 'pointer' }}>
                    Today
                </button>
            </div>

            {/* Days Header */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', padding: '10px 0', borderBottom: '1px solid var(--glass-border)', background: 'rgba(15, 23, 42, 1)', textAlign: 'center', fontSize: '0.8rem', fontWeight: '600', color: '#64748b' }}>
                <div style={{ color: '#ef4444' }}>Sun</div>
                <div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div>
                <div style={{ color: '#3b82f6' }}>Sat</div>
            </div>

            {/* Calendar Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', background: 'rgba(15, 23, 42, 0.5)' }}>
                {renderDays()}
            </div>

            {/* 확장 패널: 클릭한 날짜 바로 아래에 표시 */}
            {expandedDate && (
                <div style={{
                    position: 'absolute',
                    top: panelPosition.top,
                    left: Math.max(0, panelPosition.left),
                    width: '280px',
                    maxHeight: '300px',
                    background: 'rgba(15, 23, 42, 0.98)',
                    border: '1px solid #38bdf8',
                    borderRadius: '12px',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(56, 189, 248, 0.3)',
                    zIndex: 100,
                    overflow: 'hidden',
                    animation: 'fadeIn 0.15s ease-out'
                }}>
                    {/* 패널 헤더 */}
                    <div style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.1)',
                        background: 'rgba(56, 189, 248, 0.1)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#fff' }}>
                                📅 {expandedDate}
                            </span>
                            {expandedReport && (
                                <span style={{ fontSize: '0.65rem', background: '#10b981', color: '#fff', padding: '2px 6px', borderRadius: '10px' }}>
                                    리포트
                                </span>
                            )}
                        </div>
                        <button
                            onClick={(e) => { e.stopPropagation(); setExpandedDate(null); }}
                            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px' }}
                        >
                            <X size={16} />
                        </button>
                    </div>

                    {/* 패널 내용 */}
                    <div style={{ padding: '12px', maxHeight: '220px', overflowY: 'auto' }}>
                        {expandedEvents.length === 0 ? (
                            <div style={{ color: '#64748b', textAlign: 'center', padding: '20px 0', fontSize: '0.85rem' }}>
                                예정된 이벤트 없음
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {expandedEvents.map((evt, idx) => (
                                    <div key={idx} style={{
                                        background: 'rgba(30, 41, 59, 0.6)',
                                        padding: '10px 12px',
                                        borderRadius: '8px',
                                        borderLeft: `3px solid ${evt.importance === 'HIGH' ? '#ef4444' : evt.importance === 'MEDIUM' ? '#f97316' : '#3b82f6'}`
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <div style={{ flex: 1 }}>
                                                <div style={{
                                                    fontSize: '0.85rem', fontWeight: 'bold',
                                                    color: evt.importance === 'HIGH' ? '#fca5a5' : evt.importance === 'MEDIUM' ? '#fdba74' : '#93c5fd',
                                                    marginBottom: '4px'
                                                }}>
                                                    {evt.event_time && (
                                                        <span style={{
                                                            background: 'rgba(255,255,255,0.1)',
                                                            padding: '2px 6px', borderRadius: '4px',
                                                            fontSize: '0.75rem', marginRight: '6px', color: '#cbd5e1'
                                                        }}>
                                                            {evt.event_time.slice(0, 5)}
                                                        </span>
                                                    )}
                                                    {evt.title}
                                                </div>
                                                {evt.description && (
                                                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', lineHeight: 1.4 }}>
                                                        {evt.description}
                                                    </div>
                                                )}
                                            </div>
                                            {onDeleteEvent && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); onDeleteEvent(evt.id); }}
                                                    style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: '2px', marginLeft: '8px' }}
                                                >
                                                    <Trash2 size={12} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* 이벤트 추가 버튼 */}
                        {onAddEvent && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onAddEvent(expandedDate); }}
                                style={{
                                    width: '100%', marginTop: '10px',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                    padding: '8px', borderRadius: '8px',
                                    background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8',
                                    border: '1px dashed rgba(56, 189, 248, 0.4)',
                                    cursor: 'pointer', fontSize: '0.8rem'
                                }}
                            >
                                <Plus size={14} /> 이벤트 추가
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* CSS 애니메이션 */}
            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default EventCalendar;
