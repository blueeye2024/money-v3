import React from 'react';

const TripleFilterStatus = ({ title, status, isBear = false }) => {
    const conditions = [
        { key: 'step1', label: '30분봉 추세 전환', desc: status?.step_details?.step1 || '추세 확인' },
        { key: 'step2', label: '박스권 돌파 (+2%)', desc: status?.step_details?.step2 || '상승 돌파' },
        { key: 'step3', label: '5분봉 진입 신호', desc: status?.step_details?.step3 || '타이밍 포착' }
    ];

    // Blue tones for entry complete (not warning)
    // Unified Style (Strict Request: SOXL Style == SOXS Style)
    // Both Purple/Violet regardless of Bull/Bear
    const activeColor = '#8b5cf6';
    const finalColor = '#7c3aed';

    const conditionsMet = [status?.step1, status?.step2, status?.step3].filter(Boolean).length;

    // Helper for US/KR Time
    const formatDualTime = (timeStr) => {
        if (!timeStr) return '-';

        // Handle pre-formatted backend string (e.g. "2026-01-01 12:00 (US) / ...")
        if (typeof timeStr === 'string' && timeStr.includes(' / ') && timeStr.includes('(KR)')) {
            try {
                const parts = timeStr.split(' / ');
                if (parts.length === 2) {
                    return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                            <div>🇺🇸 {parts[0].replace('(US)', '').trim()} (NY)</div>
                            <div>🇰🇷 {parts[1].replace('(KR)', '').trim()} (KR)</div>
                        </div>
                    );
                }
            } catch (e) { return timeStr; }
        }

        try {
            // Assume input is KST or ISO. parsed correctly by new Date() if ISO. 
            // If it's a simple string like 'YYYY-MM-DD HH:MM:SS', new Date() usually parses it in local time or UTC depending on browser.
            // Given the server is KST, we should treat it carefully.
            // Let's assume the string is parseable.
            const date = new Date(timeStr);
            if (isNaN(date.getTime())) return timeStr;

            const format = (d, tz) => {
                const parts = new Intl.DateTimeFormat('en-CA', {
                    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: false
                }).formatToParts(d);

                // en-CA gives YYYY-MM-DD. standard
                const get = (type) => parts.find(p => p.type === type).value;
                return `${get('year')}.${get('month')}.${get('day')} ${get('hour')}:${get('minute')}`;
            };

            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                    <div>🇺🇸 {format(date, 'America/New_York')} (NY)</div>
                    <div>🇰🇷 {format(date, 'Asia/Seoul')} (KR)</div>
                </div>
            );
        } catch (e) {
            return timeStr;
        }
    };

    return (
        <div style={{ flex: 1, minWidth: '320px', background: 'rgba(0,0,0,0.4)', padding: '1.5rem', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
                        <h4 style={{ margin: 0, fontSize: '1.1rem', color: status?.final ? (isBear ? '#a78bfa' : '#60a5fa') : '#666', fontWeight: '800' }}>{title}</h4>

                        {/* Current Price & Daily Change */}
                        {status?.current_price > 0 && (
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', fontSize: '0.85rem' }}>
                                <span style={{ color: '#aaa', fontWeight: 'bold' }}>
                                    ${status.current_price.toFixed(2)}
                                </span>
                                {status?.daily_change != null && (
                                    <span style={{
                                        color: status.daily_change >= 0 ? '#10b981' : '#ef4444',
                                        fontWeight: 'bold',
                                        fontSize: '0.75rem'
                                    }}>
                                        ({status.daily_change >= 0 ? '+' : ''}{status.daily_change.toFixed(2)}%)
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '4px' }}>
                        {status?.final ? (
                            <span style={{
                                color: finalColor, fontWeight: '900', fontSize: '0.9rem',
                                textShadow: `0 0 10px ${finalColor}44`,
                                animation: 'pulse 1.5s infinite'
                            }}>
                                🚀 강력 매수 진입 (ENTRY)
                            </span>
                        ) : (
                            `${conditionsMet} / 3 조건 완료`
                        )}
                    </div>
                </div>
                {status?.final ? (
                    <div style={{ textAlign: 'right' }}>
                        <span style={{
                            padding: '0.4rem 1rem', background: finalColor, color: 'white', borderRadius: '30px', fontSize: '0.75rem', fontWeight: 'bold',
                            animation: 'pulse 1.5s infinite', boxShadow: `0 0 20px ${finalColor}66`, display: 'inline-block'
                        }}>
                            진입 조건 완성
                        </span>
                    </div>
                ) : (
                    <div style={{ fontSize: '0.7rem', color: '#444', background: 'rgba(0,0,0,0.2)', padding: '4px 10px', borderRadius: '20px', border: '1px solid #333' }}>
                        조건 대기 중...
                    </div>
                )}
            </div>

            {/* Horizontal Condition Bar */}
            <div style={{ position: 'relative', height: '60px', marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 10px' }}>
                <div style={{ position: 'absolute', top: '50%', left: '10%', right: '10%', height: '4px', background: 'rgba(255,255,255,0.02)', transform: 'translateY(-50%)', zIndex: 1, borderRadius: '2px' }} />

                {conditions.map((cond, idx) => {
                    const isMet = status ? status[cond.key] : false;
                    const backendColor = status ? status[`${cond.key}_color`] : null;
                    const isFinalEntry = status?.final; // 진입조건 완성 확인

                    // Default OFF State
                    let dotBg = '#0f0f0f'; // Very dark
                    let dotBorder = 'rgba(255,255,255,0.1)';
                    let dotColor = '#333';
                    let shadow = 'none';
                    let scale = 1;

                    // Priority: Warning Colors > Final Entry (Green) > Normal Active
                    // 모든 경보는 붉은색 + 불빛
                    if (backendColor === 'red' || backendColor === 'orange' || backendColor === 'yellow') {
                        dotBg = '#ef4444';  // 모든 경보 붉은색 통일
                        dotBorder = 'rgba(255,255,255,0.5)';
                        dotColor = 'white';
                        shadow = '0 0 20px #ef4444';  // 불빛 켜기
                        scale = 1.15;  // 크기 강조
                    } else if (isFinalEntry && isMet) {
                        // 진입조건 완성: 보라색 계열 (SOXS 스타일 통일)
                        dotBg = activeColor; // Purple
                        dotBorder = 'white';
                        dotColor = 'white';
                        shadow = `0 0 20px ${activeColor}88`;
                        scale = 1.15;
                    } else if (isMet) {
                        dotBg = activeColor;
                        dotBorder = 'white';
                        dotColor = 'white';
                        shadow = `0 0 12px ${activeColor}66`;
                        scale = 1.05;
                    } else {
                        dotBg = 'rgba(255,255,255,0.05)';
                        dotBorder = 'rgba(255,255,255,0.1)';
                        dotColor = '#333';
                    }

                    return (
                        <div key={idx} style={{ zIndex: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                            <div style={{
                                width: '32px', height: '32px', borderRadius: '50%',
                                background: dotBg, border: `2px solid ${dotBorder}`,
                                boxShadow: shadow,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: dotColor, fontWeight: 'bold', fontSize: '1rem',
                                transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                                transform: `scale(${scale})`
                            }}>
                                {'✓'}
                            </div>
                            <div style={{ textAlign: 'center', opacity: isMet ? 1 : 0.5, transition: 'opacity 0.3s' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: '700', color: isMet ? '#fff' : '#444' }}>{cond.label}</div>
                                <div style={{
                                    fontSize: '0.65rem',
                                    color: backendColor === 'red' ? '#ef4444' : backendColor === 'yellow' ? '#eab308' : (isMet ? '#aaa' : '#333'),
                                    fontWeight: backendColor ? 'bold' : 'normal'
                                }}>
                                    {status?.[`${cond.key}_status`] || cond.desc}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Recent Signal Info */}
            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {status?.warning_5m && (
                    <div style={{
                        background: 'rgba(234, 179, 8, 0.1)', color: '#eab308', padding: '8px 12px', borderRadius: '8px',
                        fontSize: '0.75rem', fontWeight: 'bold', border: '1px solid rgba(234, 179, 8, 0.3)',
                        animation: 'pulse 1s infinite'
                    }}>
                        ⚠️ 주의: 5분봉 데드크로스 발생 (단기 조정 가능성)
                    </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '4px 0' }}>
                    {conditions.map(c => (
                        status?.step_details?.[c.key] && (
                            <div key={c.key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#888' }}>
                                <span>• {c.label}</span>
                                <span style={{ color: '#aaa', fontWeight: 'bold' }}>{status.step_details[c.key]}</span>
                            </div>
                        )
                    ))}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderTop: '1px dashed rgba(255,255,255,0.05)', paddingTop: '8px', gap: '12px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#555', flex: 1 }}>
                        {formatDualTime(status?.signal_time || status?.timestamp)}
                    </div>

                    {/* Entry Price and Current Price Display */}
                    {status?.final && status?.entry_price && (
                        <div style={{ fontSize: '0.7rem', textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            <div style={{ color: '#777' }}>
                                진입: <span style={{ color: '#aaa', fontWeight: 'bold' }}>${status.entry_price?.toFixed(2) || '-'}</span>
                            </div>
                            <div style={{ color: '#777' }}>
                                현재: <span style={{ color: activeColor, fontWeight: 'bold' }}>${status.current_price?.toFixed(2) || '-'}</span>
                                {status.entry_price && status.current_price && (
                                    <span style={{
                                        marginLeft: '6px',
                                        color: status.current_price >= status.entry_price ? '#10b981' : '#ef4444',
                                        fontWeight: 'bold',
                                        fontSize: '0.65rem'
                                    }}>
                                        ({(((status.current_price - status.entry_price) / status.entry_price) * 100).toFixed(1)}%)
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {status?.data_time && (
                    <div style={{
                        fontSize: '0.6rem', color: '#555', textAlign: 'right',
                        marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '4px'
                    }}>
                        Data: {status.data_time} (NY)
                    </div>
                )}
            </div>
        </div>
    );
};

const MarketInsight = ({ market, stocks, signalHistory }) => {
    if (!market) return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>데이터 로딩 중...</div>;

    const { market_regime } = market;
    const regimeDetails = market_regime?.details;

    const activeStocks = stocks && Array.isArray(stocks)
        ? [...stocks].sort((a, b) => (b.current_ratio || 0) - (a.current_ratio || 0))
        : [];

    // Helper function for dual time formatting
    const formatDualTime = (timeStr) => {
        if (!timeStr) return '-';

        // Handle pre-formatted backend string (e.g. "2026-01-01 12:00 (US) / ...")
        if (typeof timeStr === 'string' && timeStr.includes(' / ') && timeStr.includes('(KR)')) {
            try {
                const parts = timeStr.split(' / ');
                if (parts.length === 2) {
                    return (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                            <div>🇺🇸 {parts[0].replace('(US)', '').trim()} (NY)</div>
                            <div>🇰🇷 {parts[1].replace('(KR)', '').trim()} (KR)</div>
                        </div>
                    );
                }
            } catch (e) { return timeStr; }
        }

        try {
            const date = new Date(timeStr);
            if (isNaN(date.getTime())) return timeStr;

            const format = (d, tz) => {
                const parts = new Intl.DateTimeFormat('en-CA', {
                    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: false
                }).formatToParts(d);

                const get = (type) => parts.find(p => p.type === type).value;
                return `${get('year')}.${get('month')}.${get('day')} ${get('hour')}:${get('minute')}`;
            };

            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.65rem', color: '#888' }}>
                    <div>🇺🇸 {format(date, 'America/New_York')} (NY)</div>
                    <div>🇰🇷 {format(date, 'Asia/Seoul')} (KR)</div>
                </div>
            );
        } catch (e) {
            return timeStr;
        }
    };

    return (
        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '3rem', display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>

            {/* 1. MASTER CONTROL TOWER (V2.3) */}
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ width: '48px', height: '48px', background: 'rgba(212, 175, 55, 0.1)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem' }}>🛰️</div>
                        <h3 style={{ margin: 0, fontSize: '1.4rem', color: 'var(--accent-gold)', letterSpacing: '1px', fontWeight: '900' }}>MASTER CONTROL TOWER</h3>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{
                            background: market_regime?.regime?.includes('Bull') ? 'rgba(74, 222, 128, 0.1)' : market_regime?.regime?.includes('Bear') ? 'rgba(248, 113, 113, 0.1)' : 'rgba(255,255,255,0.05)',
                            padding: '0.5rem 1rem', borderRadius: '10px', border: `1px solid ${market_regime?.regime?.includes('Bull') ? '#4ade8055' : market_regime?.regime?.includes('Bear') ? '#f8717155' : '#ffffff22'}`,
                        }}>
                            <span style={{ color: market_regime?.regime?.includes('Bull') ? '#4ade80' : market_regime?.regime?.includes('Bear') ? '#f87171' : '#ccc', fontWeight: '900', fontSize: '1.1rem' }}>
                                {regimeDetails?.reason || market_regime?.regime}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Insight Comment Box */}
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1.2rem', borderRadius: '16px', marginBottom: '2rem', borderLeft: '5px solid var(--accent-gold)' }}>
                    <p style={{ margin: 0, color: '#bbb', fontSize: '0.95rem', lineHeight: '1.6', fontWeight: '500' }}>
                        {regimeDetails?.comment || "시장 상황을 실시간 분석 중입니다."}
                    </p>
                </div>

                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '2.5rem' }}>
                    <TripleFilterStatus title="SOXL (BULL TOWER)" status={regimeDetails?.soxl} isBear={false} />
                    <TripleFilterStatus title="SOXS (BEAR TOWER)" status={regimeDetails?.soxs} isBear={true} />
                </div>

                {/* Detailed Strategy Guide */}
                <div style={{ background: 'linear-gradient(145deg, rgba(30,41,59,0.5), rgba(15,23,42,0.6))', padding: '1.5rem', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', marginBottom: '1.5rem' }}>
                        <div style={{ width: '36px', height: '36px', background: 'rgba(96, 165, 250, 0.2)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>📋</div>
                        <h4 style={{ margin: 0, fontSize: '1.2rem', color: '#60a5fa', fontWeight: '800' }}>종합 매매 실천 계획 & 상세 전략 가이드</h4>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.2rem', borderRadius: '16px' }}>
                            <div style={{ color: 'var(--accent-gold)', fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <div style={{ width: '6px', height: '6px', background: 'var(--accent-gold)', borderRadius: '50%' }} /> HISTORY (신호 발생 기록)
                            </div>
                            <div style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.7', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {signalHistory && Array.isArray(signalHistory) && signalHistory.length > 0 ? (
                                    signalHistory.map(sig => {
                                        // 한국시간만 표시
                                        const kstTime = sig.time_kst || (sig.signal_time || '').split('(')[0].trim();

                                        // BUY/SELL 한글 변환
                                        const signalType = sig.signal_type || '';
                                        let actionText = '';
                                        let actionColor = '#888';

                                        if (signalType.includes('BUY')) {
                                            actionText = '매수';
                                            actionColor = '#ef4444';  // 붉은색
                                        } else if (signalType.includes('SELL')) {
                                            actionText = '매도';
                                            actionColor = '#3b82f6';  // 파란색
                                        } else if (signalType.includes('WARNING')) {
                                            actionText = '경보';
                                            actionColor = '#eab308';  // 노란색
                                        }

                                        // 신호 이유
                                        const reason = sig.signal_reason || '';

                                        return (
                                            <div key={sig.id} style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                borderBottom: '1px dashed rgba(255,255,255,0.1)',
                                                paddingBottom: '8px',
                                                gap: '4px'
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ fontSize: '0.75rem', color: '#888' }}>
                                                        {kstTime}
                                                    </span>
                                                    <span style={{ color: actionColor, fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                                                        {sig.ticker} {actionText}
                                                    </span>
                                                </div>
                                                {reason && (
                                                    <div style={{ fontSize: '0.7rem', color: '#666', paddingLeft: '4px' }}>
                                                        {reason}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })
                                ) : (
                                    <div style={{ color: '#666' }}>최근 발생한 신호가 없습니다.</div>
                                )}
                            </div>
                        </div>

                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.2rem', borderRadius: '16px', border: '1px solid rgba(56, 189, 248, 0.3)', boxShadow: '0 4px 20px rgba(0,0,0,0.3)' }}>
                            <div style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
                                <div style={{ color: '#38bdf8', fontWeight: 'bold', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <div style={{ width: '8px', height: '8px', background: '#38bdf8', borderRadius: '50%', boxShadow: '0 0 10px #38bdf8' }} />
                                    청안 Prime Guide : Action Plan
                                </div>
                                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>최종 결론 및 행동 지침 (Score 기반)</div>
                            </div>

                            {/* Score Bars */}
                            <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
                                {['SOXL', 'SOXS'].map(ticker => {
                                    const guide = regimeDetails?.prime_guide;
                                    const score = guide?.[ticker.toLowerCase() + '_score']?.score || 0;
                                    const color = ticker === 'SOXL' ? '#06b6d4' : '#a855f7';
                                    return (
                                        <div key={ticker} style={{ flex: 1, background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '12px', border: `1px solid ${color}33` }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', marginBottom: '8px' }}>
                                                <span style={{ color: color, fontWeight: 'bold' }}>{ticker} 매수 준비율</span>
                                                <span style={{ color: 'white', fontWeight: '900', fontSize: '1.1rem' }}>{score}%</span>
                                            </div>
                                            <div style={{ width: '100%', height: '8px', background: '#333', borderRadius: '4px' }}>
                                                <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: '4px', transition: 'width 0.5s', boxShadow: `0 0 12px ${color}55` }} />
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                            {/* Main Guide Deep Dive */}
                            <div style={{
                                background: 'rgba(15, 23, 42, 0.6)',
                                padding: '16px',
                                borderRadius: '12px',
                                marginBottom: '0',
                                borderLeft: '4px solid #38bdf8'
                            }}>
                                <h5 style={{ margin: '0 0 10px 0', color: '#38bdf8', fontSize: '0.9rem' }}>🎯 종합 매매 실천 계획 & 상세 전략 가이드</h5>
                                <div style={{ color: '#f1f5f9', fontSize: '0.9rem', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontFamily: "'Noto Sans KR', sans-serif" }}>
                                    {regimeDetails?.prime_guide?.main_guide || "전략 생성 중..."}
                                </div>
                            </div>
                        </div>

                        {/* --- New Section: Market Intelligence Center --- */}
                        <div style={{ marginTop: '24px', background: 'rgba(0,0,0,0.2)', padding: '1.2rem', borderRadius: '16px' }}>
                            <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                🌐 Market Intelligence Center (심층 분석)
                            </h4>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>

                                {/* 1. Technical Detail Panel */}
                                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '12px' }}>
                                    <h5 style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '0.8rem' }}>📊 SOXL/SOXS 상세 분석</h5>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                        {['SOXL', 'SOXS'].map(ticker => {
                                            const guide = regimeDetails?.prime_guide;
                                            const rsi = guide?.tech_summary?.[ticker.toLowerCase() + '_rsi'] || '-';
                                            const macd = guide?.tech_summary?.[ticker.toLowerCase() + '_macd'] || '-';
                                            const color = ticker === 'SOXL' ? '#06b6d4' : '#a855f7';
                                            return (
                                                <div key={ticker} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>
                                                    <span style={{ color: color, fontWeight: 'bold' }}>{ticker}</span>
                                                    <span style={{ color: '#ccc' }}>RSI: <b style={{ color: Number(rsi) > 70 ? '#f87171' : (Number(rsi) < 30 ? '#4ade80' : 'white') }}>{rsi}</b></span>
                                                    <span style={{ color: '#ccc' }}>MACD: <b>{macd}</b></span>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* 2. Global News Panel */}
                                <div style={{ gridColumn: 'span 2', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '12px' }}>
                                    <h5 style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between' }}>
                                        <span>📰 주요 증시 뉴스 (Global)</span>
                                        <span style={{ fontSize: '0.7rem', color: '#666' }}>실시간 업데이트</span>
                                    </h5>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                        {(regimeDetails?.prime_guide?.news || []).slice(0, 4).map((n, i) => (
                                            n.url ? (
                                                <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
                                                    <div style={{
                                                        padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px',
                                                        border: '1px solid rgba(255,255,255,0.05)', height: '100%',
                                                        cursor: 'pointer', transition: 'background 0.2s'
                                                    }}
                                                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                                                        onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.2)'}
                                                    >
                                                        <div style={{ fontSize: '0.8rem', color: '#e2e8f0', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n.title}</div>
                                                        <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{n.publisher} • {n.time}</div>
                                                    </div>
                                                </a>
                                            ) : null
                                        ))}
                                        {(!regimeDetails?.prime_guide?.news || regimeDetails.prime_guide.news.length === 0) && (
                                            <div style={{ padding: '20px', textAlign: 'center', fontSize: '0.8rem', color: '#666', gridColumn: 'span 2' }}>분석 중이거나 뉴스가 없습니다.</div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.05); opacity: 0.9; }
                    100% { transform: scale(1); opacity: 1; }
                }
                @keyframes flash {
                    0% { opacity: 1; }
                    50% { opacity: 0.3; }
                    100% { opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default MarketInsight;
