import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const EventCalendar = ({ reports, events, selectedDate, onDateClick, onAddEvent, onDeleteEvent, onMonthChange }) => {
    const [viewDate, setViewDate] = useState(new Date());

    const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
    const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

    const currentYear = viewDate.getFullYear();
    const currentMonth = viewDate.getMonth();
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);

    const prevMonth = () => {
        const newDate = new Date(currentYear, currentMonth - 1, 1);
        setViewDate(newDate);
        if (onMonthChange) onMonthChange(newDate.getFullYear(), newDate.getMonth());
    };
    const nextMonth = () => {
        const newDate = new Date(currentYear, currentMonth + 1, 1);
        setViewDate(newDate);
        if (onMonthChange) onMonthChange(newDate.getFullYear(), newDate.getMonth());
    };

    const formatDate = (year, month, day) => `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    // [Ver 6.1.1] 날짜 클릭 시 팝업 제거 - 단순히 날짜 선택만
    const handleDayClick = (dateStr) => {
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
                    onClick={() => handleDayClick(dateStr)}
                    style={{
                        minHeight: '80px', padding: '8px', cursor: 'pointer', position: 'relative',
                        background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.4)',
                        border: isSelected ? '1px solid rgba(56, 189, 248, 0.5)' : '1px solid rgba(148, 163, 184, 0.1)',
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

    return (
        <div className="glass-panel" style={{ padding: '0', overflow: 'visible', position: 'relative' }}>
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


        </div>
    );
};

export default EventCalendar;
