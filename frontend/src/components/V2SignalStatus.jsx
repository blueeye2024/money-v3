import React, { useState, useEffect, useMemo } from 'react';
import Swal from 'sweetalert2';
import { ComposedChart, AreaChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from 'recharts';

// Constants
const KRW_EXCHANGE_RATE = 1450;

// Helper: Extract clean ticker from title
const getCleanTicker = (title) => {
    if (title.toUpperCase().includes('SOXL')) return 'SOXL';
    if (title.toUpperCase().includes('SOXS')) return 'SOXS';
    return title.split(' ')[0].toUpperCase();
};

const V2SignalStatus = ({ title, buyStatus, sellStatus, renderInfo, metrics: propMetrics, isBear = false, onRefresh }) => {
    // Derived values
    const { current_price, daily_change, change_pct } = renderInfo || {};
    const displayChange = change_pct ?? daily_change;
    const cleanTicker = useMemo(() => getCleanTicker(title), [title]);

    // [Ver 5.9.2] Mini Chart Data (5m + 30m with MA)
    const [chartData5m, setChartData5m] = useState([]);
    const [chartData30m, setChartData30m] = useState([]);
    const [alertLevels, setAlertLevels] = useState([]);
    const [showMaChart, setShowMaChart] = useState(false);

    useEffect(() => {
        const fetchChart = async () => {
            try {
                const res = await fetch(`/api/v2/chart/${cleanTicker}?limit=40`);
                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    setChartData5m(json.data.candles_5m || []);
                    setChartData30m(json.data.candles_30m || []);
                }
            } catch (e) {
                console.error('Chart fetch error:', e);
            }
        };

        const fetchAlerts = async () => {
            try {
                const res = await fetch(`/api/v2/alerts/${cleanTicker}`);
                const json = await res.json();
                if (json.status === 'success' && json.data) {
                    setAlertLevels(json.data.filter(a => a.is_active === 'Y' && a.price > 0));
                }
            } catch (e) {
                console.error('Alert fetch error:', e);
            }
        };

        fetchChart();
        fetchAlerts();
        const chartInterval = setInterval(fetchChart, 60000);
        const alertInterval = setInterval(fetchAlerts, 10000);
        return () => {
            clearInterval(chartInterval);
            clearInterval(alertInterval);
        };
    }, [cleanTicker]);

    // Mode determination
    const isHolding = buyStatus?.final_buy_yn === 'Y';
    const mode = isHolding ? 'SELL' : 'BUY';
    const activeData = mode === 'BUY' ? buyStatus : sellStatus;

    // Theme colors
    const themeColor = isBear ? '#a855f7' : '#06b6d4';

    // State
    const [modal, setModal] = React.useState({ type: null, isOpen: false, key: null, isActive: false });
    const [formData, setFormData] = React.useState({ price: '', qty: '' });
    const [submitting, setSubmitting] = React.useState(false);
    const [isUpdating, setIsUpdating] = React.useState(false);

    // Update indicator effect
    React.useEffect(() => {
        if (renderInfo) {
            setIsUpdating(true);
            const timer = setTimeout(() => setIsUpdating(false), 2000);
            return () => clearTimeout(timer);
        }
    }, [renderInfo]);

    // Modal form initialization
    React.useEffect(() => {
        if (modal.isOpen) {
            let initialPrice = current_price || '';
            let initialQty = '';

            if (modal.type === 'MANUAL_SIGNAL') {
                const stepIdx = modal.key?.slice(-1);
                const targetKey = `manual_target_${modal.key?.startsWith('sell') ? 'sell' : 'buy'}${stepIdx}`;
                if (activeData?.[targetKey] > 0) initialPrice = activeData[targetKey];
            } else if (modal.type === 'BUY' && buyStatus?.real_buy_yn === 'Y') {
                initialPrice = buyStatus.real_buy_price || current_price || '';
                initialQty = buyStatus.real_buy_qn || '';
            } else if (modal.type === 'SELL') {
                initialQty = buyStatus?.real_buy_qn || '';
            }

            setFormData({ price: initialPrice, qty: initialQty });
        }
    }, [modal.isOpen]);

    const handleUpdateTarget = async () => {
        const type = modal.key === 'buy_sig2_yn' ? 'box' : 'stop';
        const price = formData.price;

        if (!price || price <= 0) return Swal.fire('Error', "유효한 가격을 입력해주세요.", 'error');

        setSubmitting(true);
        try {
            const res = await fetch('/api/v2/update-target', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: cleanTicker, target_type: type, price: parseFloat(price) })
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                Swal.fire({
                    title: '완료',
                    text: `목표가가 $${price}로 설정되었습니다.`,
                    icon: 'success',
                    timer: 1500,
                    showConfirmButton: false
                });
                setModal({ type: null, isOpen: false, key: null });
                if (onRefresh) onRefresh();
            } else {
                Swal.fire('Error', data.message || "설정 실패", 'error');
            }
        } catch (e) {
            console.error("Update Target Error:", e);
            Swal.fire('Error', "서버 통신 오류", 'error');
        } finally {
            setSubmitting(false);
        }
    };

    const handleConfirm = async (isEnd = false) => {
        if (!formData.price) return Swal.fire('Error', "가격을 입력해주세요.", 'error');
        setSubmitting(true);

        let endpoint = '';
        let payload = {};


        if (modal.type === 'MANUAL_SIGNAL') {
            endpoint = '/api/v2/manual-signal';
            const now = new Date();
            const newId = `${cleanTicker}${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

            payload = {
                manage_id: activeData?.manage_id || newId,
                ticker: cleanTicker,
                signal_key: modal.key,
                price: parseFloat(formData.price),
                status: modal.signalType === 'SELL' ? 'SET_TARGET' : 'Y'
            };
        } else if (modal.type === 'BUY' || modal.type === 'SELL') {
            if (modal.type === 'BUY' && !formData.qty) {
                setSubmitting(false);
                return Swal.fire('Error', "수량을 입력해주세요.", 'error');
            }
            endpoint = modal.type === 'BUY' ? '/api/v2/confirm-buy' : '/api/v2/confirm-sell';
            const autoQty = modal.type === 'SELL' ? (buyStatus?.real_buy_qn || formData.qty || 0) : formData.qty;
            payload = {
                ticker: cleanTicker,
                price: parseFloat(formData.price),
                qty: parseFloat(autoQty),
                is_end: isEnd
            };
        }



        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const json = await res.json();
            if (json.status === 'success') {
                Swal.fire({
                    icon: 'success',
                    title: '완료',
                    text: json.message,
                    timer: 2000,
                    showConfirmButton: false
                });
                setModal({ type: null, isOpen: false, key: null });
                if (onRefresh) onRefresh();
            } else {
                Swal.fire('Error', json.message, 'error');
            }
        } catch (e) {
            Swal.fire('Error', "Network Error", 'error');
        } finally {
            setSubmitting(false);
        }
    };

    const handleCancelSignal = async () => {
        if (modal.type !== 'MANUAL_SIGNAL') return;

        setSubmitting(true);
        try {

            const payload = {
                ticker: cleanTicker,
                signal_key: modal.key,
                price: parseFloat(formData.price) || 0,
                status: 'N'
            };

            const res = await fetch('/api/v2/manual-signal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const json = await res.json();
            if (json.status === 'success') {
                Swal.fire({
                    icon: 'success',
                    title: '취소 완료',
                    text: '신호가 취소되었습니다.',
                    timer: 2000,
                    showConfirmButton: false
                });
                setModal({ type: null, isOpen: false, key: null });
                if (onRefresh) onRefresh();
            } else {
                Swal.fire('Error', json.message, 'error');
            }
        } catch (e) {
            Swal.fire('Error', "Network Error", 'error');
        } finally {
            setSubmitting(false);
        }
    }

    const handleDelete = async () => {
        if (!cleanTicker) return;

        // SweetAlert with options
        const result = await Swal.fire({
            title: '기록 삭제',
            text: "어떤 기록을 삭제하시겠습니까?",
            icon: 'warning',
            showCancelButton: true,
            showDenyButton: true,
            confirmButtonColor: '#d33',
            denyButtonColor: '#f59e0b',
            cancelButtonColor: '#3085d6',
            confirmButtonText: '전체 삭제 (매수+매도)',
            denyButtonText: '매도 기록만 삭제',
            cancelButtonText: '취소'
        });

        if (result.isDismissed) return;

        let endpoint = `/api/v2/record/${cleanTicker}`;
        let successMsg = "전체 기록이 삭제되었습니다.";

        if (result.isDenied) {
            endpoint = `/api/v2/sell-record/${cleanTicker}`;
            successMsg = "매도 기록만 삭제되었습니다.";
        }

        try {
            const res = await fetch(endpoint, { method: 'DELETE' });
            const json = await res.json();
            if (json.status === 'success') {
                Swal.fire({
                    icon: 'success',
                    title: '삭제 완료',
                    text: successMsg,
                    timer: 2000,
                    showConfirmButton: false
                });
                if (onRefresh) onRefresh();
            } else {
                Swal.fire('Error', json.message, 'error');
            }
        } catch (e) {
            Swal.fire('Error', "Network Error", 'error');
        }
    };

    // Format Price
    const formatPrice = (p) => p ? `$${Number(p).toFixed(2)}` : '-';

    // Steps Configuration - 신호 단계 정의
    // BUY: 매수 신호 (1차: 5분봉 GC, 2차: +1% 상승, 3차: 30분봉 GC)
    // SELL: 매도 신호 (1차: 5분봉 DC, 2차: Trailing Stop, 3차: 30분봉 DC)
    const getSteps = (type) => type === 'BUY' ? [
        { key: 'buy_sig1_yn', label: '1차: 5분봉 GC', desc: '추세 시작', rawKey: 'buy1' },
        { key: 'buy_sig2_yn', label: '2차: 상승 지속(+1%)', desc: '모멘텀 확인', rawKey: 'buy2' },
        { key: 'buy_sig3_yn', label: '3차: 30분봉 GC', desc: '추세 확정', rawKey: 'buy3' }
    ] : [
        { key: 'sell_sig1_yn', label: '1차: 5분봉 DC', desc: '단기 조정', rawKey: 'sell1' },
        { key: 'sell_sig2_yn', label: '2차: Trailing Stop', desc: '리스크 관리', rawKey: 'sell2' },
        { key: 'sell_sig3_yn', label: '3차: 30분봉 DC', desc: '추세 이탈', rawKey: 'sell3' }
    ];

    // --- Ver 3.0 Market Intelligence Metrics ---
    const metrics = propMetrics || renderInfo?.new_metrics || {};
    const signals = metrics.signals || {};

    const renderSteps = (stepType, data, isActiveMode) => {
        const stepList = getSteps(stepType);

        // Debug Info
        const manageId = data?.manage_id || '-';
        let localModeColor = isActiveMode ? (mode === 'SELL' ? '#ef4444' : themeColor) : '#10b981';
        if (stepType === 'BUY' && isHolding) localModeColor = '#10b981';

        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', marginTop: '1rem', padding: '0 10px' }}>
                {/* Connecting Line */}
                <div style={{ position: 'absolute', top: '20px', left: '15%', right: '15%', height: '2px', background: 'rgba(255,255,255,0.1)', zIndex: 0 }} />

                {/* Manage ID Display */}
                {isActiveMode && (
                    <div style={{ position: 'absolute', top: '-25px', right: '0', fontSize: '0.65rem', color: '#475569' }}>
                        ID: {manageId}
                    </div>
                )}

                {stepList.map((step, idx) => {
                    const isActive = data?.[step.key] === 'Y';

                    // Determine Manual Flag
                    // buy_sig1_yn -> is_manual_buy1
                    // sell_sig1_yn -> is_manual_sell1
                    // Logic: replace '_sig' with '' (buy_sig1_yn -> buy1_yn) -> no..
                    // DB keys: is_manual_buy1, is_manual_sell1.
                    // step.key is 'buy_sig1_yn' or 'sell_sig1_yn'.
                    // Mapping:
                    let manualKey = null;
                    if (step.key.includes('buy_sig')) {
                        manualKey = `is_manual_buy${step.key.charAt(7)}`; // buy_sig1_yn -> charAt(7) is '1'
                    } else if (step.key.includes('sell_sig')) {
                        manualKey = `is_manual_sell${step.key.charAt(8)}`; // sell_sig1_yn -> charAt(8) is '1'
                    }
                    const isManual = manualKey && data?.[manualKey] === 'Y';

                    // Price
                    const priceKey = step.key.replace('_yn', '_price');
                    const signalPrice = data?.[priceKey];

                    // [FIX] Define manualTarget for display
                    const stepIdx = idx + 1;
                    const targetKey = `manual_target_${stepType === 'SELL' ? 'sell' : 'buy'}${stepIdx}`;
                    const manualTarget = data?.[targetKey] > 0 ? data[targetKey] : null;

                    // Ver 3.0 Signal Time Logic
                    let signalTimeDisplay = null;
                    if (step.key === 'buy_sig1_yn') signalTimeDisplay = signals.gold_5m; // 1차 매수 (5분 골든)
                    if (step.key === 'buy_sig3_yn') signalTimeDisplay = signals.gold_30m; // 3차 매수 (30분 골든)
                    if (step.key === 'sell_sig1_yn') signalTimeDisplay = signals.dead_5m; // 1차 매도 (5분 데드)
                    if (step.key === 'sell_sig3_yn') signalTimeDisplay = signals.dead_30m; // 3차 매도 (30분 데드)

                    // Clean Time String
                    if (signalTimeDisplay && signalTimeDisplay !== 'N' && typeof signalTimeDisplay === 'string') {
                        try {
                            const timePart = signalTimeDisplay.split(' ')[1]?.substring(0, 5);
                            if (timePart) signalTimeDisplay = timePart;
                        } catch (e) { }
                    } else {
                        signalTimeDisplay = null;
                    }

                    return (
                        <div key={idx} style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', flex: 1 }}>
                            <div
                                onClick={() => {
                                    if (isActiveMode) {
                                        setModal({ type: 'MANUAL_SIGNAL', signalType: stepType, isOpen: true, key: step.rawKey, isActive: isActive });
                                    }
                                }}
                                style={{
                                    width: '40px', height: '40px', borderRadius: '50%',
                                    background: isActive ? localModeColor : '#1e293b',
                                    border: `2px solid ${isActive ? '#fff' : 'rgba(255,255,255,0.1)'}`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    boxShadow: isActive ? `0 0 15px ${localModeColor}66` : 'none',
                                    transition: 'all 0.3s ease',
                                    cursor: isActiveMode ? 'pointer' : 'default', // Disable cursor if not active
                                    opacity: isActiveMode ? 1 : 0.8
                                }}
                                title={isActiveMode ? (isManual ? "사용자 수동 확정" : (signalTimeDisplay ? `신호 발생: ${signals.gold_5m || 'N/A'}` : "수동 신호 발생 (클릭)")) : "진입 신호 (수정 불가)"}
                            >
                                <span style={{ fontSize: '1rem', color: isActive ? '#fff' : '#64748b', fontWeight: 'bold' }}>
                                    {isActive ? (isManual ? '🧑‍💻' : '✓') : idx + 1}
                                </span>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: isActive ? '#f1f5f9' : '#64748b', whiteSpace: 'nowrap' }}>
                                    {step.label}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: '#475569', marginTop: '2px' }}>
                                    {isActive ? (
                                        // Active: Show Price (+ Manual Badge)
                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                            <span style={{ color: '#fbbf24', fontWeight: 'bold', fontSize: '0.8rem' }}>
                                                {formatPrice(signalPrice)}
                                            </span>
                                            {isManual && <span style={{ fontSize: '0.6rem', color: '#38bdf8' }}>USER</span>}
                                        </div>
                                    ) : (
                                        // Inactive: Show Description or Manual Target
                                        manualTarget ? (
                                            <span style={{ color: '#fbbf24', fontWeight: 'bold', fontSize: '0.8rem' }}>🎯 ${Number(manualTarget).toFixed(2)}</span>
                                        ) : (
                                            signalTimeDisplay ? <span style={{ color: '#64748b' }}>({signalTimeDisplay})</span> : step.desc
                                        )
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div style={{ width: '100%', flex: 1, minWidth: '280px', background: 'rgba(0,0,0,0.4)', padding: '1.5rem', borderRadius: '16px', border: `1px solid ${mode === 'SELL' ? '#ef4444' : themeColor}33`, position: 'relative' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h4 style={{ margin: 0, fontSize: '1.2rem', color: themeColor, fontWeight: '800' }}>{title}</h4>
                        <span style={{
                            fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px', fontWeight: 'bold',
                            background: mode === 'SELL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(6, 182, 212, 0.1)',
                            color: mode === 'SELL' ? '#ef4444' : themeColor
                        }}>
                            {mode === 'SELL' ? '매도 감시 (HOLDING)' : '매수 대기 (WATCHING)'}
                        </span>
                    </div>
                    {/* Price Display */}
                    {current_price && (
                        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                            <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff', letterSpacing: '-0.5px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                                ${Number(current_price).toFixed(2)}
                            </span>
                            {displayChange != null && (
                                <span style={{
                                    fontSize: '0.75rem', fontWeight: 'bold',
                                    color: displayChange >= 0 ? '#4ade80' : '#f87171'
                                }}>
                                    ({displayChange >= 0 ? '+' : ''}{Number(displayChange).toFixed(2)}%)
                                </span>
                            )}
                            {isUpdating && (
                                <span style={{ color: '#fbbf24', fontSize: '1rem', animation: 'pulse 0.5s infinite' }}>⚡</span>
                            )}
                        </div>
                    )}

                    {/* [Ver 5.7.3] Day High Display - Visible in both BUY/SELL modes */}
                    {(activeData?.day_high_price > 0 || renderInfo?.day_high > 0) && (
                        <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ color: '#f472b6' }}>High: ${Number(activeData?.day_high_price || renderInfo?.day_high).toFixed(2)}</span>
                            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>(-1.5% Stop: ${(Number(activeData?.day_high_price || renderInfo?.day_high) * 0.985).toFixed(2)})</span>
                        </div>
                    )}
                </div>

                {/* Visual Badge - Real Buy Info */}
                <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>

                    {!isHolding && activeData?.buy_sig1_yn === 'Y' && (
                        <div style={{ fontSize: '0.8rem', color: themeColor, animation: 'pulse 1.5s infinite', fontWeight: 'bold' }}>
                            Signal Active!
                        </div>
                    )}

                    {isHolding && buyStatus?.real_buy_yn === 'Y' && (
                        <div
                            onClick={() => setModal({ type: 'BUY', isOpen: true })}
                            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', cursor: 'pointer' }}
                            title="클릭하여 실매수 가격/수량 수정"
                        >
                            <div style={{ fontSize: '0.9rem', color: '#10b981', fontWeight: 'bold' }}>
                                ✅ 매수: {Number(buyStatus.real_buy_qn)}개 @ {formatPrice(buyStatus.real_buy_price)}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '2px' }}>
                                Total: <span style={{ color: '#fff', fontWeight: 'bold' }}>${(buyStatus.real_buy_qn * buyStatus.real_buy_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '4px' }}>
                                    (≈₩{((buyStatus.real_buy_qn * buyStatus.real_buy_price) * KRW_EXCHANGE_RATE).toLocaleString(undefined, { maximumFractionDigits: 0 })})
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Hold - Buy Steps */}
            {
                isHolding && (
                    <div style={{ marginBottom: '1.5rem', opacity: 0.8, filter: 'grayscale(0.3)' }}>
                        <div style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>✅ 진입 신호 (완료)</span>
                            <div style={{ height: '1px', flex: 1, background: '#10b981', opacity: 0.3 }}></div>
                        </div>
                        {renderSteps('BUY', buyStatus, false)}
                    </div>
                )
            }

            {/* Active Steps */}
            <div>
                {isHolding && (
                    <div style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>👁️ 매도 감시 중</span>
                        <div style={{ height: '1px', flex: 1, background: '#ef4444', opacity: 0.3 }}></div>
                    </div>
                )}
                {renderSteps(mode, mode === 'BUY' ? buyStatus : sellStatus, true)}
            </div>

            {/* Footer Actions */}
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '12px', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px' }}>
                <span
                    onClick={() => setShowMaChart(!showMaChart)}
                    style={{ fontSize: '0.75rem', color: showMaChart ? '#fbbf24' : '#64748b', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    [{showMaChart ? '보조 차트 닫기' : '보조 차트 보기'}]
                </span>
                {buyStatus?.real_buy_yn !== 'Y' && (
                    <span
                        onClick={() => setModal({ type: 'BUY', isOpen: true })}
                        style={{ fontSize: '0.75rem', color: '#10b981', cursor: 'pointer', fontWeight: 'bold', textDecoration: 'underline' }}
                    >
                        [실매수 확정]
                    </span>
                )}
                {isHolding && (
                    <span
                        onClick={() => setModal({ type: 'SELL', isOpen: true })}
                        style={{ fontSize: '0.75rem', color: '#ef4444', cursor: 'pointer', fontWeight: 'bold', textDecoration: 'underline' }}
                    >
                        [종결/청산]
                    </span>
                )}
                <span
                    onClick={handleDelete}
                    style={{ fontSize: '0.75rem', color: '#94a3b8', cursor: 'pointer', textDecoration: 'underline' }}
                >
                    [기록 삭제]
                </span>
            </div>

            {/* Modal */}
            {
                modal.isOpen && (
                    <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.85)', zIndex: 9999,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
                    }}>
                        <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', width: '100%', maxWidth: '300px', border: '1px solid #334155' }}>
                            <h5 style={{ margin: '0 0 15px 0', color: '#fff', fontSize: '1.1rem' }}>
                                {modal.type === 'MANUAL_SIGNAL' ? (
                                    modal.signalType === 'SELL' ? '매도 설정' : '진입 신호 발생 (매수)'
                                ) : (
                                    modal.type === 'SET_TARGET' ? '2차 목표가 설정' : (
                                        modal.type === 'BUY' ? '실매수 확정' : '종결처리'
                                    )
                                )}
                            </h5>

                            <div style={{ marginBottom: '10px' }}>
                                <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>
                                    {modal.type === 'MANUAL_SIGNAL' ? '신호 발생 가격 ($)' : (modal.type === 'SET_TARGET' ? '설정 목표가 ($)' : '실행 가격 ($)')}
                                </label>
                                <input
                                    type="number" step="0.01"
                                    value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })}
                                    style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: '8px', fontSize: '1rem', fontWeight: 'bold' }}
                                    placeholder={
                                        modal.type === 'SET_TARGET'
                                            ? (modal.key === 'buy_sig2_yn' ? "돌파 목표가 ($)" : "하향 이탈가/손절가 ($)")
                                            : "가격 입력 ($)"
                                    }
                                />
                            </div>

                            {modal.type !== 'MANUAL_SIGNAL' && modal.type !== 'SELL' && modal.type !== 'SET_TARGET' && (
                                <>
                                    <div style={{ marginBottom: '15px' }}>
                                        <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>총 수량 (개)</label>
                                        <input
                                            type="number" step="1"
                                            value={formData.qty} onChange={e => setFormData({ ...formData, qty: e.target.value })}
                                            style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: '8px', fontSize: '1rem', fontWeight: 'bold' }}
                                            placeholder="누적 매도 수량 (Total)"
                                        />
                                    </div>

                                    {/* Total Amount Display */}
                                    <div style={{ background: '#1e293b', padding: '10px', borderRadius: '8px', textAlign: 'center', marginBottom: '15px', border: '1px solid #334155' }}>
                                        <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>총 매도 금액 (예상)</div>
                                        <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#ef4444' }}>
                                            ${(parseFloat(formData.price || 0) * parseFloat(formData.qty || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                        </div>
                                    </div>
                                </>
                            )}

                            {/* Action Buttons */}
                            <div style={{ display: 'grid', gridTemplateColumns: (modal.type === 'MANUAL_SIGNAL') ? '1fr 1fr 1fr' : (modal.type === 'SELL' || modal.type === 'SET_TARGET') ? '1fr 1fr' : '1fr 1fr', gap: '8px' }}>
                                {/* Left Button: Save or Confirm (Hide during Manual Signal or Sell or SetTarget) */}
                                {modal.type !== 'MANUAL_SIGNAL' && modal.type !== 'SELL' && modal.type !== 'SET_TARGET' && (
                                    <button
                                        onClick={() => handleConfirm(false)}
                                        style={{ padding: '12px', background: modal.type === 'BUY' ? '#10b981' : '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer' }}
                                    >
                                        {modal.type === 'BUY' ? '실매수 확정' : '중간 저장 (Save)'}
                                    </button>
                                )}

                                {/* Save Target Button */}
                                {modal.type === 'SET_TARGET' && (
                                    <button
                                        onClick={handleUpdateTarget}
                                        style={{ padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '0.9rem', cursor: 'pointer' }}
                                    >
                                        저장 (Save)
                                    </button>
                                )}

                                {/* Manual Signal Confirm Button (Show only if NOT Active) */}
                                {modal.type === 'MANUAL_SIGNAL' && !modal.isActive && (
                                    <button
                                        type="button"
                                        onClick={() => handleConfirm(false)}
                                        style={{ padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '0.9rem', cursor: 'pointer' }}
                                    >
                                        {modal.signalType === 'SELL' ? '저장' : '신호 발생 (ON)'}
                                    </button>
                                )}

                                {/* Middle Button: Terminate (Sell Only - Main Action) */}
                                {modal.type === 'SELL' && (
                                    <button
                                        onClick={() => handleConfirm(true)}
                                        style={{ padding: '12px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '0.9rem', cursor: 'pointer' }}
                                    >
                                        최종 종결
                                    </button>
                                )}

                                {/* Cancel Signal Button (Show only if Active) */}
                                {modal.type === 'MANUAL_SIGNAL' && modal.isActive && (
                                    <button
                                        type="button"
                                        onClick={handleCancelSignal} disabled={submitting}
                                        style={{ padding: '12px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.9rem' }}
                                    >
                                        신호 취소 (OFF)
                                    </button>
                                )}

                                {/* Close Button */}
                                <button
                                    onClick={() => setModal({ type: null, isOpen: false, key: null })}
                                    style={{ padding: '10px', background: '#334155', color: '#cbd5e1', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}
                                >
                                    닫기
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            <style>{`
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.6; }
                    100% { opacity: 1; }
                }
            `}</style>

            {/* [Ver 5.9.6] Enhanced Alert Levels Reference Chart */}
            {chartData5m.length > 0 && (() => {
                // 최근 30분 데이터 (6개 캔들) + 현재가 포인트
                const baseData = chartData5m.slice(-6);
                const now = new Date();
                const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
                const recentData = current_price
                    ? [...baseData, { time: currentTime, price: current_price }]
                    : baseData;

                const prices = recentData.map(d => d.price);
                const alertPrices = alertLevels.map(a => parseFloat(a.price));
                const allPrices = [...prices, ...alertPrices, current_price || 0].filter(p => p > 0);
                const minY = Math.min(...allPrices) - 0.1;
                const maxY = Math.max(...allPrices) + 0.1;

                const lastPrice = current_price || recentData[recentData.length - 1]?.price || 0;
                const touchedAlerts = alertLevels.filter(a => {
                    const alertPrice = parseFloat(a.price);
                    return Math.abs(lastPrice - alertPrice) < 0.05;
                });

                return (
                    <div style={{
                        marginTop: '12px',
                        background: 'rgba(0,0,0,0.3)',
                        borderRadius: '8px',
                        padding: '12px',
                        border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>🎯 가격 알림 기준선 (최근 30분)</span>
                            <span style={{ fontSize: '0.7rem' }}>
                                {alertLevels.filter(a => a.level_type === 'BUY').length > 0 && <span style={{ color: '#f87171', marginRight: '8px' }}>● 매수 {alertLevels.filter(a => a.level_type === 'BUY').length}개</span>}
                                {alertLevels.filter(a => a.level_type === 'SELL').length > 0 && <span style={{ color: '#c084fc' }}>● 매도 {alertLevels.filter(a => a.level_type === 'SELL').length}개</span>}
                                {touchedAlerts.length > 0 && <span style={{ color: '#fbbf24', marginLeft: '8px', animation: 'pulse 1s infinite' }}>⚠️ 근접!</span>}
                            </span>
                        </div>
                        <ResponsiveContainer width="100%" height={240}>
                            <ComposedChart data={recentData} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                                <defs>
                                    <linearGradient id={`gradAlert-${cleanTicker}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.05} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={{ stroke: '#334155' }} tickLine={false} />
                                <YAxis
                                    domain={[minY, maxY]}
                                    tick={{ fill: '#94a3b8', fontSize: 9 }}
                                    axisLine={{ stroke: '#334155' }}
                                    tickLine={false}
                                    tickFormatter={(val) => `$${val.toFixed(2)}`}
                                    width={45}
                                />
                                <Tooltip
                                    contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid #334155', borderRadius: '6px', fontSize: '0.75rem' }}
                                    labelStyle={{ color: '#94a3b8' }}
                                    formatter={(val, name) => {
                                        if (name === 'price') {
                                            const nearestBuy = alertLevels.filter(a => a.level_type === 'BUY').map(a => parseFloat(a.price)).sort((a, b) => Math.abs(a - val) - Math.abs(b - val))[0];
                                            const nearestSell = alertLevels.filter(a => a.level_type === 'SELL').map(a => parseFloat(a.price)).sort((a, b) => Math.abs(a - val) - Math.abs(b - val))[0];
                                            let info = [`$${val?.toFixed(2)}`];
                                            if (nearestBuy) info.push(`매수선: $${(val - nearestBuy).toFixed(2)}`);
                                            if (nearestSell) info.push(`매도선: $${(nearestSell - val).toFixed(2)}`);
                                            return [info.join(' | '), '현재가'];
                                        }
                                        return [val, name];
                                    }}
                                />
                                {/* Price Line */}
                                <Area type="monotone" dataKey="price" stroke="#38bdf8" strokeWidth={2.5} fill={`url(#gradAlert-${cleanTicker})`} />
                                {/* Current Price Dot */}
                                {current_price && (
                                    <ReferenceDot
                                        x={currentTime}
                                        y={current_price}
                                        r={5}
                                        fill="#38bdf8"
                                        stroke="#fff"
                                        strokeWidth={2}
                                    />
                                )}
                                {/* Alert Level Lines - BUY: Red, SELL: Purple */}
                                {alertLevels.map((alert, i) => {
                                    const aPrice = parseFloat(alert.price);
                                    const isTouched = Math.abs(lastPrice - aPrice) < 0.05;
                                    const isBuy = alert.level_type === 'BUY';
                                    return (
                                        <ReferenceLine
                                            key={`alert-${i}`}
                                            y={aPrice}
                                            stroke={isBuy ? 'rgba(248, 113, 113, 0.5)' : 'rgba(192, 132, 252, 0.5)'}
                                            strokeWidth={isTouched ? 2 : 1}
                                            strokeDasharray="4 2"
                                        />
                                    );
                                })}
                                {/* Touch Indicators */}
                                {touchedAlerts.map((alert, i) => (
                                    <ReferenceDot
                                        key={`touch-${i}`}
                                        x={currentTime}
                                        y={parseFloat(alert.price)}
                                        r={6}
                                        fill={alert.level_type === 'BUY' ? '#f87171' : '#c084fc'}
                                        stroke="#fff"
                                        strokeWidth={2}
                                    />
                                ))}
                            </ComposedChart>
                        </ResponsiveContainer>
                        {/* Alert Level Labels below chart */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px', fontSize: '0.7rem' }}>
                            {alertLevels.map((alert, i) => (
                                <span key={`label-${i}`} style={{
                                    color: alert.level_type === 'BUY' ? '#f87171' : '#c084fc',
                                    background: 'rgba(255,255,255,0.05)',
                                    padding: '2px 6px',
                                    borderRadius: '4px'
                                }}>
                                    {alert.stage}차 ${parseFloat(alert.price).toFixed(2)}
                                </span>
                            ))}
                        </div>
                    </div>
                );
            })()}

            {/* [Ver 5.9.2] Enhanced Mini Price Charts with MA10/MA30 - Toggle Controlled */}
            {showMaChart && (chartData5m.length > 0 || chartData30m.length > 0) && (
                <div style={{
                    marginTop: '8px',
                    background: 'rgba(0,0,0,0.3)',
                    borderRadius: '8px',
                    padding: '10px',
                    border: '1px solid rgba(255,255,255,0.05)'
                }}>
                    {/* 5분봄 차트 */}
                    {chartData5m.length > 0 && (
                        <>
                            <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span>📈 5분봄 (MA10<span style={{ color: '#f87171' }}>●</span> / MA30<span style={{ color: '#60a5fa' }}>●</span>)</span>
                                <span style={{ display: 'flex', gap: '6px', fontSize: '0.65rem' }}>
                                    {chartData5m.some(d => d.cross === 'golden') && <span style={{ color: '#22c55e' }}>🟢 GC</span>}
                                    {chartData5m.some(d => d.cross === 'dead') && <span style={{ color: '#ef4444' }}>🔴 DC</span>}
                                </span>
                            </div>
                            <ResponsiveContainer width="100%" height={90}>
                                <ComposedChart data={chartData5m} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id={`grad5m-${cleanTicker}`} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="time" tick={false} axisLine={false} />
                                    <YAxis domain={['dataMin', 'dataMax']} hide />
                                    <Tooltip
                                        contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid #334155', borderRadius: '6px', fontSize: '0.7rem' }}
                                        labelStyle={{ color: '#94a3b8' }}
                                        formatter={(val, name) => {
                                            if (name === 'price') return [`$${val?.toFixed(2)}`, '가격'];
                                            if (name === 'ma10') return [`$${val?.toFixed(2)}`, 'MA10'];
                                            if (name === 'ma30') return [`$${val?.toFixed(2)}`, 'MA30'];
                                            return [val, name];
                                        }}
                                    />
                                    <Area type="monotone" dataKey="price" stroke="#22c55e" strokeWidth={2.5} fill={`url(#grad5m-${cleanTicker})`} />
                                    <Line type="monotone" dataKey="ma10" stroke="#f87171" strokeWidth={1} dot={false} />
                                    <Line type="monotone" dataKey="ma30" stroke="#60a5fa" strokeWidth={1} dot={false} />
                                    {chartData5m.map((d, i) => d.cross === 'golden' && (
                                        <ReferenceDot key={`gc5-${i}`} x={d.time} y={d.price} r={4} fill="#22c55e" stroke="#fff" strokeWidth={1} />
                                    ))}
                                    {chartData5m.map((d, i) => d.cross === 'dead' && (
                                        <ReferenceDot key={`dc5-${i}`} x={d.time} y={d.price} r={4} fill="#ef4444" stroke="#fff" strokeWidth={1} />
                                    ))}
                                </ComposedChart>
                            </ResponsiveContainer>
                        </>
                    )}

                    {/* 30분봄 차트 */}
                    {chartData30m.length > 0 && (
                        <>
                            <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '8px', marginBottom: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                                <span>📈 30분봄 (MA10<span style={{ color: '#f87171' }}>●</span> / MA30<span style={{ color: '#60a5fa' }}>●</span>)</span>
                                <span style={{ display: 'flex', gap: '6px', fontSize: '0.65rem' }}>
                                    {chartData30m.some(d => d.cross === 'golden') && <span style={{ color: '#22c55e' }}>🟢 GC</span>}
                                    {chartData30m.some(d => d.cross === 'dead') && <span style={{ color: '#ef4444' }}>🔴 DC</span>}
                                </span>
                            </div>
                            <ResponsiveContainer width="100%" height={90}>
                                <ComposedChart data={chartData30m} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id={`grad30m-${cleanTicker}`} x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="time" tick={false} axisLine={false} />
                                    <YAxis domain={['dataMin', 'dataMax']} hide />
                                    <Tooltip
                                        contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid #334155', borderRadius: '6px', fontSize: '0.7rem' }}
                                        labelStyle={{ color: '#94a3b8' }}
                                        formatter={(val, name) => {
                                            if (name === 'price') return [`$${val?.toFixed(2)}`, '가격'];
                                            if (name === 'ma10') return [`$${val?.toFixed(2)}`, 'MA10'];
                                            if (name === 'ma30') return [`$${val?.toFixed(2)}`, 'MA30'];
                                            return [val, name];
                                        }}
                                    />
                                    <Area type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2.5} fill={`url(#grad30m-${cleanTicker})`} />
                                    <Line type="monotone" dataKey="ma10" stroke="#f87171" strokeWidth={1} dot={false} />
                                    <Line type="monotone" dataKey="ma30" stroke="#60a5fa" strokeWidth={1} dot={false} />
                                    {chartData30m.map((d, i) => d.cross === 'golden' && (
                                        <ReferenceDot key={`gc30-${i}`} x={d.time} y={d.price} r={4} fill="#22c55e" stroke="#fff" strokeWidth={1} />
                                    ))}
                                    {chartData30m.map((d, i) => d.cross === 'dead' && (
                                        <ReferenceDot key={`dc30-${i}`} x={d.time} y={d.price} r={4} fill="#ef4444" stroke="#fff" strokeWidth={1} />
                                    ))}
                                </ComposedChart>
                            </ResponsiveContainer>
                        </>
                    )}
                </div>
            )}
        </div >
    );
};

export default V2SignalStatus;
