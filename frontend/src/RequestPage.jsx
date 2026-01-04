import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, User, Bot, Code } from 'lucide-react';

const RequestItem = ({ req }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div style={{
            background: 'rgba(30, 41, 59, 0.4)', // 더 어두운 반투명 배경
            borderRadius: '12px',
            marginBottom: '0.8rem',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            overflow: 'hidden',
            boxShadow: isExpanded ? '0 4px 20px rgba(0,0,0,0.2)' : 'none',
            transition: 'all 0.2s ease'
        }}>
            {/* Header Line - Always Visible */}
            <div
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                    padding: '1rem 1.5rem',
                    display: 'grid',
                    gridTemplateColumns: 'minmax(140px, auto) 1fr minmax(80px, auto) 30px',
                    alignItems: 'center',
                    gap: '1.5rem',
                    cursor: 'pointer',
                    background: isExpanded ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                    borderBottom: isExpanded ? '1px solid rgba(255, 255, 255, 0.05)' : 'none'
                }}
                className="request-header"
            >
                {/* 1. Time */}
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                    {req.created_at ? req.created_at.replace('T', ' ').substring(0, 16) : '-'}
                </div>

                {/* 2. User Request Summary (One Line) */}
                <div style={{
                    fontSize: '0.95rem',
                    color: isExpanded ? '#60a5fa' : '#e2e8f0',
                    fontWeight: isExpanded ? '600' : '400',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                }}>
                    {req.request_text}
                </div>

                {/* 3. Status Badge */}
                <div style={{ textAlign: 'center' }}>
                    <span style={{
                        fontSize: '0.7rem',
                        fontWeight: '700',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        background: req.status === 'completed' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(251, 191, 36, 0.1)',
                        color: req.status === 'completed' ? '#4ade80' : '#fbbf24',
                        textTransform: 'uppercase',
                        border: req.status === 'completed' ? '1px solid rgba(74, 222, 128, 0.2)' : '1px solid rgba(251, 191, 36, 0.2)'
                    }}>
                        {req.status}
                    </span>
                </div>

                {/* 4. Toggle Icon */}
                <div style={{ color: '#64748b', display: 'flex', justifyContent: 'center' }}>
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </div>
            </div>

            {/* Expanded Body - Accordion */}
            {isExpanded && (
                <div style={{
                    padding: '1.5rem 2rem',
                    background: 'rgba(15, 23, 42, 0.3)',
                    animation: 'fadeIn 0.3s ease'
                }}>
                    <div style={{ display: 'grid', gap: '2rem' }}>

                        {/* Section 1: Full User Request */}
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.8rem', color: '#e2e8f0', fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                <User size={16} color="#94a3b8" /> User Request (Full)
                            </div>
                            <div style={{
                                background: 'rgba(255,255,255,0.03)',
                                padding: '1.25rem',
                                borderRadius: '8px',
                                border: '1px solid rgba(255,255,255,0.05)',
                                color: '#f1f5f9',
                                lineHeight: '1.6',
                                whiteSpace: 'pre-wrap',
                                fontSize: '0.95rem'
                            }}>
                                {req.request_text}
                            </div>
                        </div>

                        {/* Section 2: AI & Implementation Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
                            {/* AI Interpretation */}
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.8rem', color: '#60a5fa', fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                    <Bot size={16} /> AI Interpretation
                                </div>
                                <div style={{
                                    color: '#cbd5e1',
                                    fontSize: '0.9rem',
                                    lineHeight: '1.7',
                                    whiteSpace: 'pre-wrap',
                                    background: 'rgba(59, 130, 246, 0.05)',
                                    padding: '1rem',
                                    borderRadius: '8px',
                                    borderLeft: '3px solid #60a5fa'
                                }}>
                                    {req.ai_interpretation || '분석 내용이 없습니다.'}
                                </div>
                            </div>

                            {/* Implementation Details */}
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.8rem', color: '#4ade80', fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                    <Code size={16} /> Implementation Details
                                </div>
                                <div style={{
                                    color: '#cbd5e1',
                                    fontSize: '0.9rem',
                                    lineHeight: '1.6',
                                    whiteSpace: 'pre-wrap',
                                    fontFamily: 'Consolas, Monaco, "Andale Mono", monospace',
                                    background: 'rgba(0, 0, 0, 0.3)',
                                    padding: '1rem',
                                    borderRadius: '8px',
                                    border: '1px solid rgba(74, 222, 128, 0.2)'
                                }}>
                                    {req.implementation_details || '구현 상세 내용이 없습니다.'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const RequestPage = () => {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/requests')
            .then(res => res.json())
            .then(data => {
                // 최신순 정렬 (ID 내림차순)
                setRequests(data.sort((a, b) => b.id - a.id));
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '10px', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)' }}>📝</span>
                    <span style={{ background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>요청사항 히스토리</span>
                </h2>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                    Total: <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{requests.length}</span>
                </div>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>
                    <div className="loading-spinner" style={{ marginBottom: '1rem' }}>⏳</div>
                    데이터 로딩 중...
                </div>
            ) : requests.length === 0 ? (
                <div style={{ padding: '4rem', textAlign: 'center', background: 'rgba(255,255,255,0.03)', borderRadius: '20px', color: '#64748b', border: '1px dashed rgba(255,255,255,0.1)' }}>
                    아직 기록된 요청사항이 없습니다.
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {/* Header Row (Optional, for column guides) */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(140px, auto) 1fr minmax(80px, auto) 30px', gap: '1.5rem', padding: '0 1.5rem 0.8rem', color: '#64748b', fontSize: '0.8rem', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        <div>Timestamp</div>
                        <div>User Request Summary</div>
                        <div style={{ textAlign: 'center' }}>Status</div>
                        <div></div>
                    </div>

                    {requests.map(req => (
                        <RequestItem key={req.id} req={req} />
                    ))}
                </div>
            )}

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

export default RequestPage;
