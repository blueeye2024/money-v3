import React from 'react';

const getScoreInterpretation = (score, position) => {
    const pos = position || '';
    const isSell = pos.includes('매도') || pos.includes('하단');
    if (score >= 80) return isSell ? "🚨 긴급 매도" : "✨ 강력 매수";
    if (score >= 70) return isSell ? "📉 매도" : "🟢 매수";
    if (score >= 50) return isSell ? "⚠ 경계/약세" : "🟡 관망/중립";
    return isSell ? "📉 단기 조정" : "⚪ 관망";
};

const StockCard = ({ data }) => {
    const {
        ticker, current_price, change_pct, position,
        signal_time, is_box, box_high, box_low,
        rsi, macd, macd_sig, score, score_details
    } = data;

    const isBuy = (position || '').includes('매수') || (position || '').includes('상단');
    const isSell = (position || '').includes('매도') || (position || '').includes('하단');

    // Safety check for score details
    const details = score_details || { base: 0, trend: 0, reliability: 0, breakout: 0 };

    if (data.error) {
        return (
            <div className="glass-panel" style={{ padding: '1.5rem', borderLeft: `4px solid var(--accent-red)` }}>
                <h3 style={{ margin: 0 }}>{ticker}</h3>
                <p style={{ color: 'var(--accent-red)' }}>Error: {data.error}</p>
            </div>
        );
    }

    let borderColor = 'var(--glass-border)';
    let cardBg = 'rgba(255, 255, 255, 0.03)';

    if (isBuy) {
        borderColor = 'var(--accent-red)';
        cardBg = 'linear-gradient(135deg, rgba(40, 20, 20, 0.4), rgba(15, 10, 10, 0.6))';
    }
    if (isSell) {
        borderColor = 'var(--accent-blue)';
        cardBg = 'linear-gradient(135deg, rgba(20, 30, 50, 0.4), rgba(10, 15, 30, 0.6))';
    }

    return (
        <div className="glass-panel" style={{ padding: '1.5rem', borderLeft: `4px solid ${borderColor}`, position: 'relative', background: cardBg }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>{ticker}</h3>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {data.name || ticker}
                    </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>${current_price ? current_price.toFixed(2) : '0.00'}</div>
                    <div style={{
                        color: change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                        fontSize: '0.9rem'
                    }}>
                        {change_pct >= 0 ? '+' : ''}{change_pct ? change_pct.toFixed(2) : '0.00'}%
                    </div>
                </div>
            </div>



            <div style={{ marginBottom: '1rem' }}>
                <span style={{
                    padding: '6px 14px',
                    borderRadius: '99px',
                    backgroundColor: isBuy ? 'rgba(248, 113, 113, 0.2)' : isSell ? 'rgba(59, 130, 246, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                    color: isBuy ? 'var(--accent-red)' : isSell ? 'var(--accent-blue)' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: 'clamp(0.75rem, 2.5vw, 0.9rem)',
                    display: 'inline-flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap'
                }}>
                    <span style={{ whiteSpace: 'nowrap' }}>{(position || '').includes('매수') ? (position || '').replace('🔵', '🔴') : position}</span>
                    <span style={{ fontSize: '0.85em', color: 'rgba(255,255,255,0.8)', fontWeight: 'normal', whiteSpace: 'nowrap' }}>
                        Score: <strong>{score}</strong> ({getScoreInterpretation(score, position)})
                    </span>
                </span>
            </div>


            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                <strong>최근 신호:</strong> {signal_time}
            </div>

            {is_box && (
                <div style={{ marginBottom: '0.5rem', fontSize: '0.9rem', background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '8px' }}>
                    <div>📦 <strong>박스권 횡보</strong></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                        <span>H: ${box_high?.toFixed(2)}</span>
                        <span>L: ${box_low?.toFixed(2)}</span>
                    </div>
                </div>
            )}

            {/* Strategy Diagnosis Section (Replaces generic News) */}
            <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.9rem', marginBottom: '8px', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '1.1rem' }}>🔬</span> <strong>전략 진단 (Strategy Diagnosis)</strong>
                </div>

                {/* 1. Target Strategy Text */}
                <div style={{ marginBottom: '8px', fontSize: '0.8rem', color: '#aaa', fontStyle: 'italic', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    🎯 [전략] {data.strategy_text || "기본 전략 (Standard)"}
                </div>

                {/* 2. Diagnosis Logic Check */}
                <div style={{ fontSize: '0.85rem', color: '#ccc', fontFamily: 'monospace' }}>
                    {data.strategy_result ? (
                        data.strategy_result.split(', ').map((log, idx) => {
                            const isPass = log.includes('OK') || log.includes('Pass');
                            const isFail = log.includes('Fail');
                            const color = isPass ? 'var(--accent-green)' : isFail ? 'var(--accent-red)' : '#ccc';
                            return (
                                <div key={idx} style={{ marginBottom: '4px' }}>
                                    <span style={{ color: color, marginRight: '6px' }}>{isPass ? '✔' : isFail ? '✖' : '•'}</span>
                                    {log}
                                </div>
                            )
                        })
                    ) : (
                        <div style={{ color: '#888' }}>전략 데이터 분석 대기중...</div>
                    )}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem', marginTop: '1rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                <div>
                    <span style={{ color: 'var(--text-secondary)' }}>RSI(14)</span>
                    <br />
                    <span style={{ color: rsi > 70 ? 'var(--accent-red)' : rsi < 30 ? 'var(--accent-green)' : 'inherit' }}>
                        {rsi?.toFixed(1)}
                    </span>
                </div>
                <div>
                    <span style={{ color: 'var(--text-secondary)' }}>MACD</span>
                    <br />
                    <span style={{ color: macd > macd_sig ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {macd?.toFixed(3)}
                    </span>
                </div>
            </div>

            <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>📰 관련 종목 뉴스</div>
                <ul style={{ margin: 0, paddingLeft: '1rem', fontSize: '0.8rem', color: '#e2e8f0', lineHeight: 1.4 }}>
                    {data.news_items && data.news_items.length > 0 ? (
                        data.news_items.map((item, i) => (
                            <li key={i}>{item}</li>
                        ))
                    ) : (
                        <li>특이사항 없음</li>
                    )}
                </ul>
            </div>

            {/* Detailed Score Breakdown */}
            <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px dashed rgba(255,255,255,0.1)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.6rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>📊 세부 점수 분석</span>
                    <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>Max Score 100</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '6px', fontSize: '0.75rem', color: '#ccc' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', background: 'rgba(0,0,0,0.15)', padding: '6px', borderRadius: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-gold)', fontWeight: 600 }}>
                            <span>기술적 기본 점수:</span> <strong>{details.base}점</strong>
                        </div>
                        {details.base_details && (
                            <div style={{ fontSize: '0.7rem', color: '#999', paddingLeft: '4px' }}>
                                - 추세/{details.base_details.confluence > 0 ? '정합' : '역행'}({details.base_details.confluence}), 지표가산(+{details.base_details.rsi + details.base_details.macd + details.base_details.bb + details.base_details.cross})
                                <br />
                                <span style={{ fontStyle: 'italic', fontSize: '0.65rem' }}>* 모든 단기/중기 지표 일치 시 기본 80점 부여</span>
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '4px 8px', borderRadius: '4px' }}>추세가산: <strong>+{details.trend}</strong></div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '4px 8px', borderRadius: '4px' }}>신뢰/돌파: <strong>+{(details.reliability || 0) + (details.breakout || 0)}</strong></div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 4px' }}>
                        <span>시장환경 및 방어:</span> <strong style={{ color: details.market < 0 ? 'var(--accent-red)' : 'inherit' }}>{details.market || 0}점</strong>
                    </div>

                    {details.pnl_adj !== 0 && (
                        <div style={{
                            padding: '6px',
                            borderRadius: '6px',
                            background: details.pnl_adj > 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            border: `1px solid ${details.pnl_adj > 0 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)'}`,
                            color: details.pnl_adj > 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                            <strong>수익/손절 보정: {details.pnl_adj > 0 ? '+' : ''}{details.pnl_adj}점</strong>
                            <div style={{ fontSize: '0.65rem', marginTop: '2px', color: '#bbb' }}>
                                {details.pnl_adj > 0 ? "수익 보존 권고 가산" : "리스크 관리(손절) 권고 가산"}
                            </div>
                        </div>
                    )}
                </div>
            </div>


        </div>
    );
};

export default StockCard;
