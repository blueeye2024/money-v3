import React from 'react';

const MarketInsight = ({ market }) => {
    return (
        <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', borderLeft: '4px solid var(--accent-purple)', paddingLeft: '1rem' }}>
                청안의 Market Insight
            </h2>
            <div style={{ lineHeight: 1.8, color: 'var(--text-secondary)' }}>
                <p>
                    <strong>해외 시장 핵심 테마:</strong> 현재 시장은 {market.S_P500 > 4500 ? '강세' : '조정'} 국면을 보이고 있습니다.
                    주요 거시 경제 지표와 기업 실적 발표에 따라 변동성이 확대될 수 있으며,
                    안전 자산(금)과 기술주(나스닥) 간의 자금 이동을 주시해야 합니다.
                </p>
                <p>
                    <strong>단기 방향성 및 리스크:</strong> 원/달러 환율 및 국채 금리 추이를 모니터링하며,
                    기술적 저항선 돌파 여부에 따라 대응 전략을 수립하는 것이 좋습니다.
                </p>
            </div>
        </div>
    );
};

export default MarketInsight;
