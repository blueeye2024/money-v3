import React, { useEffect, useState } from 'react';

const RequestPage = () => {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/requests')
            .then(res => res.json())
            .then(data => {
                setRequests(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
            <h2 style={{ fontSize: '1.8rem', fontWeight: 'bold', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ background: 'rgba(59, 130, 246, 0.2)', padding: '8px', borderRadius: '12px' }}>📝</span>
                요청사항 기록 (User Requests)
            </h2>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#888' }}>로딩 중...</div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {requests.length === 0 ? (
                        <div style={{ padding: '3rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', color: '#666' }}>
                            아직 기록된 요청사항이 없습니다.
                        </div>
                    ) : (
                        requests.map(req => (
                            <div key={req.id} className="glass-panel" style={{ padding: '1.5rem', borderRadius: '16px', borderLeft: '4px solid #3b82f6' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'flex-start' }}>
                                    <div style={{ fontSize: '0.85rem', color: '#666', background: 'rgba(0,0,0,0.2)', padding: '4px 10px', borderRadius: '20px' }}>
                                        #{req.id} • {req.created_at ? req.created_at.replace('T', ' ').substring(0, 16) : '-'}
                                    </div>
                                    <div style={{
                                        color: req.status === 'completed' ? '#4ade80' : '#fbbf24',
                                        fontWeight: 'bold', fontSize: '0.8rem', textTransform: 'uppercase',
                                        background: req.status === 'completed' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(251, 191, 36, 0.1)',
                                        padding: '4px 12px', borderRadius: '8px'
                                    }}>
                                        {req.status}
                                    </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem' }}>
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'bold', marginBottom: '0.5rem', textTransform: 'uppercase' }}>User Request</div>
                                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#e2e8f0', background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '12px' }}>
                                            {req.request_text}
                                        </div>
                                    </div>

                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                        <div>
                                            <div style={{ fontSize: '0.8rem', color: '#60a5fa', fontWeight: 'bold', marginBottom: '0.5rem', textTransform: 'uppercase' }}>AI Interpretation</div>
                                            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5', fontSize: '0.9rem', color: '#cbd5e1' }}>
                                                {req.ai_interpretation}
                                            </div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.8rem', color: '#4ade80', fontWeight: 'bold', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Implementation Details</div>
                                            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5', fontSize: '0.9rem', color: '#cbd5e1' }}>
                                                {req.implementation_details}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
};

export default RequestPage;
