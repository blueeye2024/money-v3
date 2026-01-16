import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

// Toast Mixin
const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer);
        toast.addEventListener('mouseleave', Swal.resumeTimer);
    }
});

const PriceLevelAlerts = ({ ticker }) => {
    const [levels, setLevels] = useState([]);

    // Ticker Code: L or S
    const tCode = ticker === 'SOXL' ? 'L' : 'S';
    const themeColor = ticker === 'SOXL' ? '#38bdf8' : '#c084fc'; // Blue / Purple

    const fetchLevels = async () => {
        try {
            const res = await axios.get(`/api/v2/alerts/${ticker}`);
            if (res.data.status === 'success') {
                setLevels(res.data.data);
            }
        } catch (error) {
            console.error("Fetch Alerts Error:", error);
        }
    };

    useEffect(() => {
        fetchLevels();
        // Poll every 5 seconds to check for triggered status updates
        const interval = setInterval(fetchLevels, 5000);
        return () => clearInterval(interval);
    }, [ticker]);

    const handleUpdate = async (type, stage, price, isActive) => {
        if (!price || price <= 0) {
            Toast.fire({
                icon: 'warning',
                title: '유효한 가격을 입력하세요.'
            });
            return;
        }
        try {
            await axios.post('/api/v2/alerts/update', {
                ticker,
                level_type: type,
                stage,
                price: parseFloat(price),
                is_active: isActive ? 'Y' : 'N'
            });
            if (isActive) {
                Toast.fire({
                    icon: 'success',
                    title: `${type} #${stage} 설정 저장 완료!`
                });
            } else {
                Toast.fire({
                    icon: 'info',
                    title: `${type} #${stage} 설정 OFF`
                });
            }
            fetchLevels();
        } catch (error) {
            Toast.fire({
                icon: 'error',
                title: '저장 실패'
            });
        }
    };

    const handleReset = async (type, stage) => {
        try {
            await axios.post('/api/v2/alerts/reset', {
                ticker,
                level_type: type,
                stage,
                price: 0, // Ignored
                is_active: 'Y' // Ignored
            });
            Toast.fire({
                icon: 'info',
                title: `${type} #${stage} 알림 재설정 (Reset)`
            });
            fetchLevels();
        } catch (error) {
            Toast.fire({
                icon: 'error',
                title: '리셋 실패'
            });
        }
    };

    const renderLevelRow = (type, stage, label) => {
        // Find existing data
        const data = levels.find(l => l.level_type === type && l.stage === stage) || {};
        const isTriggered = data.triggered === 'Y';
        const isActive = data.is_active === 'Y';
        const price = data.price || '';

        // Sound Code Display (e.g. LB1, SS2)
        const typeCode = type === 'BUY' ? 'B' : 'S';
        const soundCode = `${tCode}${typeCode}${stage}`;

        return (
            <div key={`${type}-${stage}`} style={{
                display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px',
                padding: '4px 8px',
                background: isTriggered ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255,255,255,0.03)',
                borderRadius: '6px',
                border: isTriggered ? '1px solid #ef4444' : '1px solid transparent',
                animation: isTriggered ? 'pulse-red 2s infinite' : 'none'
            }}>
                <style>
                    {`
                        @keyframes pulse-red {
                            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                            70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
                            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
                        }
                    `}
                </style>
                <div style={{ flex: 1, minWidth: '0', fontSize: '0.7rem', color: '#94a3b8', lineHeight: '1.2' }}>
                    {label} <span style={{ fontSize: '0.65rem', color: '#64748b' }}>({soundCode})</span>
                </div>

                <input
                    key={`${type}-${stage}-${price}`} // Force re-render when price changes (e.g. Reset)
                    type="number" step="0.01"
                    placeholder="$"
                    defaultValue={price}
                    id={`input-${ticker}-${type}-${stage}`}
                    style={{
                        width: '64px', padding: '2px 4px', background: '#1e293b', border: '1px solid #334155',
                        color: '#fff', borderRadius: '4px', textAlign: 'right', fontSize: '0.75rem', height: '24px' // h-6 equivalent
                    }}
                />

                <button
                    onClick={() => {
                        const val = document.getElementById(`input-${ticker}-${type}-${stage}`).value;
                        handleUpdate(type, stage, val, !isActive);
                    }}
                    style={{
                        padding: '0 6px', height: '24px', fontSize: '0.7rem', borderRadius: '4px', border: 'none', cursor: 'pointer',
                        background: isActive ? (type === 'BUY' ? '#10b981' : '#f87171') : '#475569',
                        color: '#fff', fontWeight: 'bold', display: 'flex', alignItems: 'center'
                    }}
                >
                    {isActive ? 'ON' : 'OFF'}
                </button>

                <button
                    onClick={() => {
                        const val = document.getElementById(`input-${ticker}-${type}-${stage}`).value;
                        handleUpdate(type, stage, val, true);
                    }}
                    style={{
                        padding: '0 6px', height: '24px', fontSize: '0.7rem', borderRadius: '4px', border: 'none', cursor: 'pointer',
                        background: '#3b82f6', color: '#fff', display: 'flex', alignItems: 'center'
                    }}
                >
                    저장
                </button>

                {isTriggered && (
                    <button
                        onClick={() => handleReset(type, stage)}
                        style={{
                            padding: '0 6px', height: '24px', fontSize: '0.7rem', borderRadius: '4px', border: '1px solid #ef4444',
                            background: 'transparent', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center'
                        }}
                    >
                        R
                    </button>
                )}
            </div>
        );
    };

    return (
        <div style={{
            padding: '12px',
            background: 'rgba(30, 41, 59, 0.4)', // Slightly transparent
            borderRadius: '12px',
            marginTop: '0px', // Remove top margin to align with grid
            maxWidth: '100%',
            boxSizing: 'border-box',
            border: `1px solid ${themeColor}22` // Minimal border
        }}>
            <h4 style={{ margin: '0 0 10px 0', color: themeColor, fontSize: '0.85rem', fontWeight: '700', letterSpacing: '0.5px' }}>
                📢 {ticker} Price Alerts
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                {/* BUY Section */}
                <div>
                    <div style={{ fontSize: '0.7rem', color: '#10b981', marginBottom: '4px', fontWeight: 'bold', borderBottom: '1px solid #10b98133', paddingBottom: '2px' }}>
                        📈 매수 (Breakout)
                    </div>
                    {renderLevelRow('BUY', 1, '1차 20%')}
                    {renderLevelRow('BUY', 2, '2차 40%')}
                    {renderLevelRow('BUY', 3, '3차 Max')}
                </div>

                {/* SELL Section */}
                <div>
                    <div style={{ fontSize: '0.7rem', color: '#ef4444', marginBottom: '4px', fontWeight: 'bold', borderBottom: '1px solid #ef444433', paddingBottom: '2px' }}>
                        📉 매도 (Breakdown)
                    </div>
                    {renderLevelRow('SELL', 1, '1차 주의')}
                    {renderLevelRow('SELL', 2, '2차 경고')}
                    {renderLevelRow('SELL', 3, '3차 손절')}
                </div>
            </div>
        </div>
    );
};

export default PriceLevelAlerts;
