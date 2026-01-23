import React from 'react';

/**
 * ScoreProgressBar - 보유 매력도 점수를 세그먼트 프로그레스 바로 시각화
 * 
 * @param {number} score - 현재 점수 (-72 ~ +92)
 * @param {string} ticker - 종목명 (SOXL, SOXS)
 * @param {boolean} compact - 컴팩트 모드 (기본: false)
 */
const ScoreProgressBar = ({ score = 0, ticker = '', compact = false }) => {
    // 점수 범위: -72 ~ +92 (총 164점)
    const MIN_SCORE = -72;
    const MAX_SCORE = 92;

    // 점수 → 위치 (0~100%) 변환
    const scoreToPosition = (s) => {
        const position = ((s - MIN_SCORE) / (MAX_SCORE - MIN_SCORE)) * 100;
        return Math.max(0, Math.min(100, position));
    };

    // 등급 정의 (6단계)
    const grades = [
        { min: -Infinity, max: 0, label: 'Danger', color: '#ef4444', emoji: '🔴', guide: '즉시 청산' },
        { min: 0, max: 20, label: 'Warning', color: '#f97316', emoji: '🟠', guide: '청산 준비' },
        { min: 20, max: 40, label: 'Caution', color: '#eab308', emoji: '🟡', guide: '익절 검토' },
        { min: 40, max: 60, label: 'Neutral', color: '#6b7280', emoji: '⚪', guide: '관망' },
        { min: 60, max: 80, label: 'Good', color: '#3b82f6', emoji: '🔵', guide: '보유 유지' },
        { min: 80, max: Infinity, label: 'Prime', color: '#22c55e', emoji: '🟢', guide: '최적' },
    ];

    // 현재 등급 찾기
    const currentGrade = grades.find(g => score >= g.min && score < g.max) || grades[0];
    const indicatorPos = scoreToPosition(score);

    // 세그먼트 너비 (균등 분할)
    const segmentWidths = [
        { start: 0, end: scoreToPosition(0) },                          // Danger: -72 ~ 0
        { start: scoreToPosition(0), end: scoreToPosition(20) },        // Warning: 0 ~ 20
        { start: scoreToPosition(20), end: scoreToPosition(40) },       // Caution: 20 ~ 40
        { start: scoreToPosition(40), end: scoreToPosition(60) },       // Neutral: 40 ~ 60
        { start: scoreToPosition(60), end: scoreToPosition(80) },       // Good: 60 ~ 80
        { start: scoreToPosition(80), end: 100 },                       // Prime: 80+
    ];

    return (
        <div className="score-progress-container" style={{ marginTop: compact ? '8px' : '12px' }}>
            {/* 헤더 (컴팩트 모드가 아닐 때만) */}
            {!compact && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>보유 매력도</span>
                    <span style={{
                        fontSize: '0.8rem',
                        fontWeight: 'bold',
                        color: currentGrade.color,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                    }}>
                        {currentGrade.emoji} {currentGrade.label}
                    </span>
                </div>
            )}

            {/* 세그먼트 프로그레스 바 */}
            <div style={{
                position: 'relative',
                height: compact ? '16px' : '24px',
                borderRadius: '12px',
                overflow: 'visible',
                display: 'flex',
                background: 'rgba(0,0,0,0.3)',
            }}>
                {grades.map((grade, idx) => {
                    const isActive = grade.label === currentGrade.label;
                    const width = segmentWidths[idx].end - segmentWidths[idx].start;

                    return (
                        <div
                            key={grade.label}
                            style={{
                                width: `${width}%`,
                                height: '100%',
                                background: isActive
                                    ? grade.color
                                    : `${grade.color}33`,
                                borderLeft: idx > 0 ? '1px solid rgba(0,0,0,0.3)' : 'none',
                                transition: 'all 0.3s ease',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: isActive ? `0 0 12px ${grade.color}66` : 'none',
                            }}
                            title={`${grade.label}: ${grade.guide}`}
                        >
                            {!compact && width > 12 && (
                                <span style={{
                                    fontSize: '0.6rem',
                                    color: isActive ? '#fff' : '#666',
                                    fontWeight: isActive ? 'bold' : 'normal',
                                    textShadow: isActive ? '0 1px 2px rgba(0,0,0,0.5)' : 'none',
                                }}>
                                    {grade.label}
                                </span>
                            )}
                        </div>
                    );
                })}

                {/* 현재 위치 인디케이터 */}
                <div style={{
                    position: 'absolute',
                    left: `calc(${indicatorPos}% - 2px)`,
                    top: '-4px',
                    bottom: '-4px',
                    width: '4px',
                    background: '#fff',
                    borderRadius: '2px',
                    boxShadow: `0 0 10px #fff, 0 0 20px ${currentGrade.color}`,
                    transition: 'left 0.5s ease',
                    zIndex: 10,
                }} />

                {/* 점수 말풍선 */}
                <div style={{
                    position: 'absolute',
                    left: `${indicatorPos}%`,
                    top: compact ? '-22px' : '-28px',
                    transform: 'translateX(-50%)',
                    background: currentGrade.color,
                    color: '#fff',
                    padding: compact ? '2px 6px' : '3px 8px',
                    borderRadius: '6px',
                    fontSize: compact ? '0.65rem' : '0.75rem',
                    fontWeight: 'bold',
                    boxShadow: `0 2px 8px ${currentGrade.color}66`,
                    whiteSpace: 'nowrap',
                    transition: 'left 0.5s ease',
                    zIndex: 11,
                }}>
                    {score}점
                </div>
            </div>

            {/* 하단 가이드 텍스트 (컴팩트 모드가 아닐 때만) */}
            {!compact && (
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: '6px',
                    fontSize: '0.6rem',
                    color: '#64748b'
                }}>
                    <span>-72</span>
                    <span style={{ color: currentGrade.color, fontWeight: 'bold' }}>
                        {currentGrade.guide}
                    </span>
                    <span>+92</span>
                </div>
            )}
        </div>
    );
};

export default ScoreProgressBar;
