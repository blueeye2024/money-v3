import React from 'react';
import Swal from 'sweetalert2';

const V2SignalStatus = ({ title, buyStatus, sellStatus, renderInfo, isBear = false, onRefresh }) => {
    // Info from V1 status (Price, Change)
    const { current_price, daily_change } = renderInfo || {};

    // Determine Current Mode
    const isHolding = buyStatus?.final_buy_yn === 'Y';
    const isSellFinished = sellStatus?.final_sell_yn === 'Y';

    const mode = (isHolding && !isSellFinished) ? 'SELL' : 'BUY';
    const activeData = mode === 'BUY' ? buyStatus : sellStatus;

    // Colors
    const themeColor = isBear ? '#a855f7' : '#06b6d4';
    const modeColor = mode === 'SELL' ? '#ef4444' : themeColor;

    // State for Modal
    const [modal, setModal] = React.useState({ type: null, isOpen: false, key: null });
    const [formData, setFormData] = React.useState({ price: '', qty: '' });
    const [submitting, setSubmitting] = React.useState(false);

    // Initial Load of Real Data if available
    React.useEffect(() => {
        if (modal.isOpen) {
            // Pre-fill if editing existing Real Buy
            if (modal.type === 'BUY' && buyStatus?.real_buy_yn === 'Y') {
                setFormData({
                    price: buyStatus.real_buy_price || current_price || '',
                    qty: buyStatus.real_buy_qn || ''
                });
            } else {
                setFormData({
                    price: current_price || '',
                    qty: ''
                });
            }
        }
    }, [modal.isOpen, current_price, buyStatus]);

    // --- Audio Alert Logic (Ver 3.9) ---
    const prevBuyRef = React.useRef(null);
    const prevSellRef = React.useRef(null);
    const isFirstLoad = React.useRef(true);

    // Determine Ticker Prefix (C=SOXL, P=SOXS)
    // Derived from title: "SOXL (BULL TOWER)" -> "C", "SOXS (BEAR TOWER)" -> "P"
    const tickerPrefix = title.includes('SOXL') ? 'C' : (title.includes('SOXS') ? 'P' : null);

    const playSound = (filename) => {
        try {
            const audio = new Audio(`/sounds/${filename}`);
            audio.play().catch(e => console.log("Audio Play Error:", e));
        } catch (e) {
            console.error("Audio setup error:", e);
        }
    };

    React.useEffect(() => {
        // Skip audio on first load / mount (prevent symphony on refresh)
        if (isFirstLoad.current) {
            if (buyStatus || sellStatus) {
                prevBuyRef.current = buyStatus;
                prevSellRef.current = sellStatus;
                isFirstLoad.current = false;
            }
            return;
        }

        if (!tickerPrefix) return;

        // Check Buy Signals
        if (buyStatus) {
            const prev = prevBuyRef.current || {};
            if (buyStatus.buy_sig1_yn === 'Y' && prev.buy_sig1_yn !== 'Y') playSound(`${tickerPrefix}B1.mp3`);
            if (buyStatus.buy_sig2_yn === 'Y' && prev.buy_sig2_yn !== 'Y') playSound(`${tickerPrefix}B2.mp3`);
            if (buyStatus.buy_sig3_yn === 'Y' && prev.buy_sig3_yn !== 'Y') playSound(`${tickerPrefix}B3.mp3`);
        }

        // Check Sell Signals
        if (sellStatus) {
            const prev = prevSellRef.current || {};
            if (sellStatus.sell_sig1_yn === 'Y' && prev.sell_sig1_yn !== 'Y') playSound(`${tickerPrefix}S1.mp3`);
            if (sellStatus.sell_sig2_yn === 'Y' && prev.sell_sig2_yn !== 'Y') playSound(`${tickerPrefix}S2.mp3`);
            if (sellStatus.sell_sig3_yn === 'Y' && prev.sell_sig3_yn !== 'Y') playSound(`${tickerPrefix}S3.mp3`);
        }

        // Update Refs
        prevBuyRef.current = buyStatus;
        prevSellRef.current = sellStatus;

    }, [buyStatus, sellStatus, tickerPrefix]);

    const handleConfirm = async () => {
        if (!formData.price) return Swal.fire('Error', "가격을 입력해주세요.", 'error');
        setSubmitting(true);

        let endpoint = '';
        let payload = {};

        if (modal.type === 'MANUAL_SIGNAL') {
            endpoint = '/api/v2/manual-signal';
            payload = {
                manage_id: activeData?.manage_id || title + 'MANUAL',
                signal_key: modal.key,
                price: parseFloat(formData.price),
                status: 'Y'
            };
        } else if (modal.type === 'BUY' || modal.type === 'SELL') {
            if (!formData.qty) { setSubmitting(false); return Swal.fire('Error', "수량을 입력해주세요.", 'error'); }
            endpoint = modal.type === 'BUY' ? '/api/v2/confirm-buy' : '/api/v2/confirm-sell';
            payload = {
                manage_id: activeData?.manage_id,
                price: parseFloat(formData.price),
                qty: parseFloat(formData.qty),
                is_end: !!formData.is_end
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
        // Only for Manual Signal Modal
        if (modal.type !== 'MANUAL_SIGNAL') return;

        setSubmitting(true);
        try {
            const payload = {
                manage_id: activeData?.manage_id || title + 'MANUAL',
                signal_key: modal.key,
                price: parseFloat(formData.price) || 0,
                status: 'N' // Cancel Signal
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
        if (!activeData?.manage_id) return;

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

        let endpoint = `/api/v2/record/${activeData.manage_id}`;
        let successMsg = "전체 기록이 삭제되었습니다.";

        if (result.isDenied) {
            endpoint = `/api/v2/sell-record/${activeData.manage_id}`;
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

    // Steps Configuration Helper
    const getSteps = (type) => type === 'BUY' ? [
        { key: 'buy_sig1_yn', label: '1차: 5분봉 GC', desc: '추세 시작', rawKey: 'buy1' },
        { key: 'buy_sig2_yn', label: '2차: 박스권+2%', desc: '강력 돌파', rawKey: 'buy2' },
        { key: 'buy_sig3_yn', label: '3차: 30분봉 GC', desc: '추세 확정', rawKey: 'buy3' }
    ] : [
        { key: 'sell_sig1_yn', label: '1차: 5분봉 DC', desc: '단기 조정', rawKey: 'sell1' },
        { key: 'sell_sig2_yn', label: '2차: 손절/익절', desc: '리스크 관리', rawKey: 'sell2' },
        { key: 'sell_sig3_yn', label: '3차: 30분봉 DC', desc: '추세 이탈', rawKey: 'sell3' }
    ];

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

                    return (
                        <div key={idx} style={{ zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', flex: 1 }}>
                            <div
                                onClick={() => {
                                    if (!activeData?.manage_id) return Swal.fire('알림', "활성 기록이 없어 수동 신호 등록이 불가능합니다.\n(첫 5분봉 신호는 자동 감지를 기다려주세요)", 'info');
                                    setModal({ type: 'MANUAL_SIGNAL', isOpen: true, key: step.rawKey });
                                }}
                                style={{
                                    width: '40px', height: '40px', borderRadius: '50%',
                                    background: isActive ? localModeColor : '#1e293b',
                                    border: `2px solid ${isActive ? '#fff' : 'rgba(255,255,255,0.1)'}`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    boxShadow: isActive ? `0 0 15px ${localModeColor}66` : 'none',
                                    transition: 'all 0.3s ease',
                                    cursor: 'pointer'
                                }}
                                title="수동 신호 발생 (클릭)"
                            >
                                <span style={{ fontSize: '1rem', color: isActive ? '#fff' : '#64748b', fontWeight: 'bold' }}>
                                    {isActive ? '✓' : idx + 1}
                                </span>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: isActive ? '#f1f5f9' : '#64748b' }}>
                                    {step.label}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: '#475569', marginTop: '2px' }}>
                                    {data?.[step.key + '_date'] ? new Date(data[step.key + '_date']).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : step.desc}
                                </div>
                                {isActive && data?.[step.key + '_price'] && (
                                    <div style={{ fontSize: '0.7rem', color: localModeColor, fontWeight: 'bold', marginTop: '2px' }}>
                                        {formatPrice(data[step.key + '_price'])}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div style={{ width: '100%', flex: 1, minWidth: '280px', background: 'rgba(0,0,0,0.4)', padding: '1.5rem', borderRadius: '16px', border: `1px solid ${mode === 'SELL' ? '#ef4444' : themeColor}33`, position: 'relative', overflow: 'hidden' }}>
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
                    <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '6px' }}>
                        Manage ID: {activeData?.manage_id || '-'}
                    </div>
                    {/* Price Display */}
                    {current_price && (
                        <div style={{ marginTop: '8px', display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                            <span style={{ fontSize: '1.2rem', fontWeight: '900', color: '#fff', letterSpacing: '-0.5px' }}>
                                ${Number(current_price).toFixed(2)}
                            </span>
                            {daily_change != null && (
                                <span style={{
                                    fontSize: '0.75rem', fontWeight: 'bold',
                                    color: daily_change >= 0 ? '#4ade80' : '#f87171'
                                }}>
                                    ({daily_change >= 0 ? '+' : ''}{Number(daily_change).toFixed(2)}%)
                                </span>
                            )}
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
                                ✅ 매수: {Number(buyStatus.real_buy_qn)}개 @ ${formatPrice(buyStatus.real_buy_price)}
                            </div>
                            <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '2px' }}>
                                Total: <span style={{ color: '#fff', fontWeight: 'bold' }}>${(buyStatus.real_buy_qn * buyStatus.real_buy_price).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '4px' }}>
                                    (≈₩{((buyStatus.real_buy_qn * buyStatus.real_buy_price) * 1450).toLocaleString(undefined, { maximumFractionDigits: 0 })})
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
                {isHolding && buyStatus?.real_buy_yn !== 'Y' && (
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
                {activeData?.manage_id && (
                    <span
                        onClick={handleDelete}
                        style={{ fontSize: '0.75rem', color: '#94a3b8', cursor: 'pointer', textDecoration: 'underline' }}
                    >
                        [기록 삭제]
                    </span>
                )}
            </div>

            {/* Modal */}
            {
                modal.isOpen && (
                    <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(0,0,0,0.85)', zIndex: 100,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px'
                    }}>
                        <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', width: '100%', maxWidth: '300px', border: '1px solid #334155' }}>
                            <h5 style={{ margin: '0 0 15px 0', color: '#fff', fontSize: '1.1rem' }}>
                                {modal.type === 'MANUAL_SIGNAL' ? '수동 신호 발생' : (modal.type === 'BUY' ? '실매수 확정' : '종결(청산) 처리')}
                            </h5>

                            <div style={{ marginBottom: '10px' }}>
                                <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>
                                    {modal.type === 'MANUAL_SIGNAL' ? '신호 발생 가격 ($)' : '실행 가격 ($)'}
                                </label>
                                <input
                                    type="number" step="0.01"
                                    value={formData.price} onChange={e => setFormData({ ...formData, price: e.target.value })}
                                    style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #334155', color: '#fff', borderRadius: '8px', fontSize: '1rem', fontWeight: 'bold' }}
                                    placeholder="실 매도 가격 (Average)"
                                />
                            </div>

                            {modal.type !== 'MANUAL_SIGNAL' && (
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

                                    {/* Termination Checkbox (SELL ONLY) */}
                                    {modal.type === 'SELL' && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)', marginBottom: '15px' }}>
                                            <input
                                                type="checkbox"
                                                id="chk_terminate"
                                                checked={formData.is_end || false}
                                                onChange={(e) => setFormData({ ...formData, is_end: e.target.checked })}
                                                style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#ef4444' }}
                                            />
                                            <label htmlFor="chk_terminate" style={{ cursor: 'pointer', flex: 1, color: '#ef4444', fontWeight: 'bold', fontSize: '0.9rem' }}>
                                                종결/청산 확정
                                            </label>
                                        </div>
                                    )}
                                </>
                            )}

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                                <button
                                    onClick={() => handleConfirm(formData.is_end)}
                                    style={{ padding: '12px', background: modal.type === 'BUY' ? '#10b981' : '#ef4444', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer' }}
                                >
                                    {formData.is_end ? '최종 종결 (End)' : '저장 (Save)'}
                                </button>

                                {/* Cancel Signal Button (Only Manual) */}
                                {modal.type === 'MANUAL_SIGNAL' && (
                                    <button
                                        onClick={handleCancelSignal} disabled={submitting}
                                        style={{ padding: '10px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.8rem' }}
                                    >
                                        신호 취소
                                    </button>
                                )}

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
        </div >
    );
};

export default V2SignalStatus;
