import React, { useState, useEffect } from 'react';

const BacktestPage = () => {
    return (
        <div className="container" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <h1 style={{ fontSize: '2.5rem', marginBottom: '2rem' }}>📈 백테스트 리포트 (Backtest)</h1>

            <div className="glass-panel" style={{ padding: '3rem', maxWidth: '600px', margin: '0 auto' }}>
                <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🏗️</div>
                <h2 style={{ color: 'var(--accent-blue)', marginBottom: '1rem' }}>시스템 구축 중</h2>
                <p style={{ lineHeight: '1.6', color: '#ccc', marginBottom: '2rem' }}>
                    현재 <strong>Cheongan 2.0 공식</strong>에 기반한 백테스팅 엔진을 서버에 통합하고 있습니다.<br />
                    매일 20시에 지난 1년 데이터를 기반으로 검증된 최적화 리포트가 이곳에 표시됩니다.
                </p>

                <div style={{ textAlign: 'left', background: 'rgba(0,0,0,0.3)', padding: '1.5rem', borderRadius: '12px', fontSize: '0.9rem' }}>
                    <div style={{ marginBottom: '0.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>[예상 리포트 항목]</div>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#aaa', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <li>전략별 누적 수익률 (CAGR) 및 MDD 분석</li>
                        <li>시장 국면(Bull/Bear)별 승률 비교 시뮬레이션</li>
                        <li>최적 파라미터(ATR 배수, 이평선 기간) 자동 추천</li>
                        <li>종목별 가상 매매 로그 (Virtual Trade Log)</li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default BacktestPage;
