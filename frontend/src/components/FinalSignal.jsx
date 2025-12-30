import React, { useMemo } from 'react';

const getScoreInterpretation = (score, position) => {
    const pos = position || '';
    const isSell = pos.includes('매도') || pos.includes('하단');
    if (score >= 80) return isSell ? "🚨 긴급 매도" : "✨ 강력 매수";
    if (score >= 70) return isSell ? "📉 매도" : "🟢 매수";
    if (score >= 50) return isSell ? "⚠ 경계/약세" : "🟡 관망/중립";
    return isSell ? "📉 단기 조정" : "⚪ 관망";
};

const FinalSignal = ({ stocks }) => {
    const topPicks = useMemo(() => {
        if (!stocks || stocks.length === 0) return [];

        // Filter for Actionable Items:
        // 1. Held & Sell Signal (Action: Sell)
        // 2. Not Held & Buy Signal (Action: Buy)
        const actionable = stocks.filter(stock => {
            // Rule 1: Score must be >= 70
            if ((stock.score || 0) < 70) return false;

            const isHeld = stock.is_held;
            const pos = stock.position || "";

            // Check Sell Signal
            const isSellSignal = pos.includes('매도') || pos.includes('하단');
            // Check Buy Signal
            const isBuySignal = pos.includes('매수') || pos.includes('상단');

            if (isHeld && isSellSignal) return true;
            if (!isHeld && isBuySignal) return true;

            return false;
        });

        // Sort by Score Desc
        actionable.sort((a, b) => (b.score || 0) - (a.score || 0));

        return actionable;
    }, [stocks]);

    if (!topPicks || topPicks.length === 0) return null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '3rem' }}>
            <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', letterSpacing: '2px', textAlign: 'center' }}>
                PORTFOLIO LEVEL FINAL DECISION
            </h2>

            <div style={{ display: 'flex', gap: '1.5rem', flexDirection: 'row', flexWrap: 'wrap' }}>
                {topPicks.map((stock, index) => (
                    <PortfolioCard key={stock.ticker} stock={stock} rank={index + 1} />
                ))}
            </div>
        </div>
    );
};

const PortfolioCard = ({ stock, rank }) => {
    const isBuy = (stock.position || '').includes('매수') || (stock.position || '').includes('상단');
    const isSell = (stock.position || '').includes('매도') || (stock.position || '').includes('하단');
    const isRank1 = rank === 1;

    let borderColor = 'var(--accent-blue)';
    let shadowColor = 'rgba(56, 189, 248, 0.2)';
    let signalColor = 'var(--text-primary)';

    if (isBuy) {
        borderColor = 'var(--accent-red)';
        shadowColor = 'rgba(248, 113, 113, 0.3)';
        signalColor = 'var(--accent-red)';
    } else if (isSell) {
        borderColor = 'var(--accent-blue)';
        shadowColor = 'rgba(59, 130, 246, 0.3)';
        signalColor = 'var(--accent-blue)';
    }

    const details = stock.score_details || {};

    return (
        <div className="glass-panel" style={{
            flex: 1, // Fix: Equal Width
            minWidth: '300px',
            padding: '2rem',
            textAlign: 'center',
            background: isBuy
                ? 'linear-gradient(135deg, rgba(40, 20, 20, 0.9), rgba(15, 10, 10, 0.95))'
                : isSell
                    ? 'linear-gradient(135deg, rgba(20, 30, 50, 0.9), rgba(10, 15, 30, 0.95))'
                    : 'linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95))',
            border: `2px solid ${borderColor}`,
            boxShadow: isRank1 ? `0 0 40px ${shadowColor}` : `0 0 20px ${shadowColor}`,
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* Rank Badge */}
            <div style={{
                position: 'absolute', top: 0, left: 0,
                background: 'rgba(0,0,0,0.6)',
                color: isRank1 ? 'var(--accent-gold)' : '#E2E8F0',
                fontWeight: 'bold', padding: '0.4rem 1rem',
                borderBottomRightRadius: '12px', fontSize: '1.1rem',
                boxShadow: '2px 2px 10px rgba(0,0,0,0.5)',
                borderRight: isRank1 ? '1px solid var(--accent-gold)' : '1px solid #E2E8F0',
                borderBottom: isRank1 ? '1px solid var(--accent-gold)' : '1px solid #E2E8F0'
            }}>
                {isRank1 ? '👑 1st Pick' : '🥈 2nd Pick'}
            </div>



            {/* Ticker - Ensure Yellow for Rank 1 */}
            <div style={{
                fontSize: isRank1 ? '4rem' : '3rem',
                fontWeight: 800,
                margin: '2rem 0 0.5rem 0',
                color: isRank1 ? 'var(--accent-gold)' : 'white'
            }}>
                {stock.ticker}
            </div>

            <div style={{ fontSize: '1.0rem', color: '#ccc', marginBottom: '0.5rem' }}>{stock.name}</div>

            <div style={{ fontSize: '1.2rem', marginBottom: '0.5rem', fontWeight: 600 }}>
                현재가: <span style={{ color: 'white' }}>${stock.current_price ? stock.current_price.toFixed(2) : '-'}</span>
            </div>

            {stock.signal_time && (
                <div style={{ fontSize: '0.85rem', color: '#888', marginBottom: '1.5rem' }}>
                    🕒 신호 시간: {stock.signal_time}
                </div>
            )}

            <div style={{
                fontSize: '1.6rem', fontWeight: 700, marginBottom: '2rem',
                color: signalColor,
                textShadow: `0 0 10px ${shadowColor}`
            }}>
                {stock.position}
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1.2rem', borderRadius: '12px', textAlign: 'left', border: '1px solid rgba(255,255,255,0.1)' }}>
                <h3 style={{ fontSize: '0.9rem', marginBottom: '0.8rem', color: 'var(--accent-gold)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>
                    📊 상세 점수 분석 (Score Details)
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    {/* Left: Total Score */}
                    <div style={{ paddingRight: '1rem', borderRight: '1px solid rgba(255,255,255,0.2)', textAlign: 'center', minWidth: '80px' }}>
                        <div style={{ fontSize: '0.8rem', color: '#aaa', marginBottom: '0.2rem' }}>총점</div>
                        <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-gold)' }}>{stock.score}</div>
                        <div style={{ fontSize: '0.7rem', color: stock.score >= 80 ? 'var(--accent-gold)' : '#ccc', marginTop: '0.2rem', whiteSpace: 'nowrap' }}>
                            {getScoreInterpretation(stock.score, stock.position)}
                        </div>
                    </div>

                    {/* Right: Criteria List */}
                    <div style={{ fontSize: '0.8rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.6rem', flex: 1 }}>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-gold)', fontWeight: 600, marginBottom: '0.2rem' }}>
                                <span>• 기술적 기본 점수 (Base):</span> <strong>{details.base || 0}점</strong>
                            </div>
                            {details.base_details && (
                                <div style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', fontSize: '0.72rem', color: '#bbb', display: 'flex', flexDirection: 'column', gap: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>기초 분석점수 (Entry/Hold):</span> <span style={{ color: 'white' }}>+{details.base_details.main}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>30분/5분 추세 정합성:</span> <span style={{ color: details.base_details.confluence > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{details.base_details.confluence > 0 ? '+' : ''}{details.base_details.confluence}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>보조지표 (RSI & MACD):</span> <span style={{ color: 'var(--accent-green)' }}>+{details.base_details.rsi + details.base_details.macd}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span>가격위치 및 신호강도:</span> <span style={{ color: 'var(--accent-green)' }}>+{details.base_details.bb + details.base_details.cross}</span>
                                    </div>
                                    <div style={{ marginTop: '2px', fontSize: '0.65rem', color: '#888', fontStyle: 'italic', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '2px' }}>
                                        ※ 모든 중장기/단기 지표가 정배열일 때 최대 80점이 부여됩니다.
                                    </div>
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span title="신호 발생 후 가격 흐름 반영">• 추가 추세 가산:</span> <strong>+{details.trend || 0}점</strong>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span title="신호 신뢰도 및 전고점 돌파 여부">• 신뢰 및 돌파 점수:</span> <strong>+{(details.reliability || 0) + (details.breakout || 0)}점</strong>
                        </div>

                        {details.pnl_adj !== 0 && (
                            <div style={{ padding: '8px', background: details.pnl_adj > 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: `1px solid ${details.pnl_adj > 0 ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)'}` }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', color: details.pnl_adj > 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 600 }}>
                                    <span>• 수익/손절 관리 가산:</span> <strong>{details.pnl_adj > 0 ? '+' : ''}{details.pnl_adj}점</strong>
                                </div>
                                <div style={{ fontSize: '0.7rem', color: '#ccc', marginTop: '4px' }}>
                                    {details.pnl_adj > 0
                                        ? "현재 수익권으로, 수익 보존 및 차익 실현 가능성이 높아 점수가 가산되었습니다."
                                        : "현재 손실권으로, 리스크 관리 및 손절 권고 기준에 따라 점수가 가산되었습니다."}
                                </div>
                            </div>
                        )}

                        <div style={{ display: 'flex', justifyContent: 'space-between', color: details.market < 0 ? 'var(--accent-red)' : '#e2e8f0' }}>
                            <span>• 시장 환경 및 방어 (Market):</span> <strong>{details.market || 0}점</strong>
                        </div>
                    </div>
                </div>



                {/* Comprehensive Analysis */}
                <div style={{ paddingTop: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '0.9rem', color: '#ddd', textAlign: 'left' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '0.3rem', color: 'var(--text-primary)' }}>📝 종합 분석 내용</div>
                    <div style={{ marginBottom: '0.5rem', lineHeight: '1.4' }}>{stock.position_desc}</div>
                    {stock.news_items && stock.news_items.length > 0 && (
                        <div style={{ fontStyle: 'italic', color: '#aaa', fontSize: '0.85rem' }}>
                            관련 이슈: "{stock.news_items[0]}"
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};


export default FinalSignal;
