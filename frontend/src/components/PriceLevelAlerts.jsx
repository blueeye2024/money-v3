import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import Swal from 'sweetalert2';

// ═══════════════════════════════════════════════════════════════════
// [Ver 5.8.4] PriceLevelAlerts - 사용자 지정가 알림 컴포넌트
// ═══════════════════════════════════════════════════════════════════
// 동작 원리:
//   BUY: 현재가 >= 지정가 → 신호 ON + 음성
//   SELL: 현재가 <= 지정가 → 신호 ON + 음성
//   조건 해제 시: 신호 자동 OFF (백엔드에서 처리)
// ═══════════════════════════════════════════════════════════════════

// Constants
const THEME_COLORS = {
    SOXL: '#38bdf8',  // Blue (Cyan)
    SOXS: '#c084fc'   // Purple
};

const LABELS = {
    BUY: ['1차 알림', '2차 알림', '3차 알림'],
    SELL: ['1차 알림', '2차 알림', '3차 알림']
};

// Toast Mixin
const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: 2500,
    timerProgressBar: true
});

// Styles (외부 정의로 리렌더링 방지)
const styles = {
    container: {
        padding: '12px',
        background: 'rgba(30, 41, 59, 0.4)',
        borderRadius: '12px',
        maxWidth: '100%',
        boxSizing: 'border-box'
    },
    header: {
        margin: '0 0 10px 0',
        fontSize: '0.85rem',
        fontWeight: '700',
        letterSpacing: '0.5px'
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '8px'
    },
    sectionHeader: (color) => ({
        fontSize: '0.7rem',
        color: color,
        marginBottom: '4px',
        fontWeight: 'bold',
        borderBottom: `1px solid ${color}33`,
        paddingBottom: '2px'
    }),
    row: (isTriggered) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginBottom: '4px',
        padding: '4px 8px',
        background: isTriggered ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255,255,255,0.03)',
        borderRadius: '6px',
        border: isTriggered ? '1px solid #ef4444' : '1px solid transparent',
        animation: isTriggered ? 'pulse-red 2s infinite' : 'none'
    }),
    label: {
        flex: 1,
        minWidth: '0',
        fontSize: '0.7rem',
        color: '#94a3b8',
        lineHeight: '1.2'
    },
    soundCode: {
        fontSize: '0.65rem',
        color: '#64748b'
    },
    input: {
        width: '64px',
        padding: '2px 4px',
        background: '#1e293b',
        border: '1px solid #334155',
        color: '#fff',
        borderRadius: '4px',
        textAlign: 'right',
        fontSize: '0.75rem',
        height: '24px'
    },
    button: (bg) => ({
        padding: '0 6px',
        height: '24px',
        fontSize: '0.7rem',
        borderRadius: '4px',
        border: 'none',
        cursor: 'pointer',
        background: bg,
        color: '#fff',
        fontWeight: 'bold',
        display: 'flex',
        alignItems: 'center'
    }),
    resetButton: {
        padding: '0 6px',
        height: '24px',
        fontSize: '0.7rem',
        borderRadius: '4px',
        border: '1px solid #ef4444',
        background: 'transparent',
        color: '#ef4444',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center'
    }
};

// CSS 애니메이션 (전역)
const cssAnimation = `
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
`;

const PriceLevelAlerts = ({ ticker, currentPrice }) => {
    // State
    const [levels, setLevels] = useState([]);
    const [priceInputs, setPriceInputs] = useState({});  // Controlled inputs

    // Derived
    const themeColor = THEME_COLORS[ticker] || '#38bdf8';
    const tickerCode = ticker === 'SOXL' ? 'L' : 'S';

    // [Fix Ver 6.4.4] Input Focus Tracking
    const focusedInputRef = useRef(null);

    // Fetch levels from API
    const fetchLevels = useCallback(async () => {
        try {
            const res = await axios.get(`/api/v2/alerts/${ticker}`);
            if (res.data.status === 'success') {
                const data = res.data.data || [];
                setLevels(data);

                // Initialize inputs from fetched data
                const inputs = {};
                data.forEach(lvl => {
                    const key = `${lvl.level_type}-${lvl.stage}`;
                    inputs[key] = lvl.price || '';
                });

                setPriceInputs(prev => {
                    const next = { ...prev, ...inputs };
                    if (focusedInputRef.current) {
                        next[focusedInputRef.current] = prev[focusedInputRef.current];
                    }
                    return next;
                });
            }
        } catch (error) {
            console.error("Fetch Alerts Error:", error);
        }
    }, [ticker]);

    // Initial fetch + polling
    useEffect(() => {
        fetchLevels();
        const interval = setInterval(fetchLevels, 5000);
        return () => clearInterval(interval);
    }, [fetchLevels]);

    // Handle price input change
    const handleInputChange = (key, value) => {
        setPriceInputs(prev => ({ ...prev, [key]: value }));
    };

    // Update alert
    const handleUpdate = async (type, stage, isActive) => {
        const key = `${type}-${stage}`;
        const price = priceInputs[key];

        if (!price || parseFloat(price) <= 0) {
            Toast.fire({ icon: 'warning', title: '유효한 가격을 입력하세요.' });
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

            Toast.fire({
                icon: isActive ? 'success' : 'info',
                title: isActive ? `${type} #${stage} 설정 완료!` : `${type} #${stage} OFF`
            });

            fetchLevels();
        } catch (error) {
            Toast.fire({ icon: 'error', title: '저장 실패' });
        }
    };

    // Reset alert (clear all)
    const handleReset = async (type, stage) => {
        try {
            await axios.post('/api/v2/alerts/reset', {
                ticker,
                level_type: type,
                stage,
                price: 0,
                is_active: 'Y'
            });

            Toast.fire({ icon: 'info', title: `${type} #${stage} 초기화` });
            fetchLevels();
        } catch (error) {
            Toast.fire({ icon: 'error', title: '리셋 실패' });
        }
    };

    // Render single row
    const renderRow = (type, stage) => {
        const key = `${type}-${stage}`;
        const data = levels.find(l => l.level_type === type && l.stage === stage) || {};
        const alertPrice = parseFloat(data.price) || 0;
        const isActive = data.is_active === 'Y';

        // [Ver 6.0.1] Real-time validation of trigger state using currentPrice
        // BUY: currentPrice >= alertPrice, SELL: currentPrice <= alertPrice
        let isTriggered = false;
        if (isActive && alertPrice > 0 && currentPrice > 0) {
            if (type === 'BUY') {
                isTriggered = currentPrice >= alertPrice;
            } else if (type === 'SELL') {
                isTriggered = currentPrice <= alertPrice;
            }
        }

        const label = LABELS[type][stage - 1];
        const typeCode = type === 'BUY' ? 'B' : 'S';
        const soundCode = `U${tickerCode}${typeCode}${stage}`;

        return (
            <div key={key} style={styles.row(isTriggered)}>
                {/* Label */}
                <div style={styles.label}>
                    {label} <span style={styles.soundCode}>({soundCode})</span>
                </div>

                {/* Price Input (Controlled) */}
                <input
                    type="number"
                    step="0.01"
                    placeholder="$"
                    value={priceInputs[key] || ''}
                    onChange={(e) => handleInputChange(key, e.target.value)}
                    onFocus={() => { focusedInputRef.current = key; }}
                    onBlur={() => { focusedInputRef.current = null; }}
                    style={styles.input}
                />

                {/* Toggle Button */}
                <button
                    onClick={() => handleUpdate(type, stage, !isActive)}
                    style={styles.button(isActive ? (type === 'BUY' ? '#10b981' : '#f87171') : '#475569')}
                >
                    {isActive ? 'ON' : 'OFF'}
                </button>

                {/* Save Button */}
                <button
                    onClick={() => handleUpdate(type, stage, true)}
                    style={styles.button('#3b82f6')}
                >
                    저장
                </button>

                {/* Reset Button (only when triggered) */}
                {isTriggered && (
                    <button onClick={() => handleReset(type, stage)} style={styles.resetButton}>
                        R
                    </button>
                )}
            </div>
        );
    };

    return (
        <div style={{ ...styles.container, border: `1px solid ${themeColor}22` }}>
            <style>{cssAnimation}</style>

            <h4 style={{ ...styles.header, color: themeColor }}>
                📢 {ticker} Price Alerts
            </h4>

            <div style={styles.grid}>
                {/* BUY Section */}
                <div>
                    <div style={styles.sectionHeader('#10b981')}>📈 매수 (Breakout)</div>
                    {[1, 2, 3].map(stage => renderRow('BUY', stage))}
                </div>

                {/* SELL Section */}
                <div>
                    <div style={styles.sectionHeader('#ef4444')}>📉 매도 (Breakdown)</div>
                    {[1, 2, 3].map(stage => renderRow('SELL', stage))}
                </div>
            </div>
        </div>
    );
};

export default PriceLevelAlerts;
