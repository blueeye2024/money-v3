import React from 'react';

const MarketInsight = ({ market }) => {
    return (
        <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', borderLeft: '4px solid var(--accent-purple)', paddingLeft: '1rem' }}>
                청안의 Market Insight
            </h2>
            <div style={{ lineHeight: 1.8, color: 'var(--text-secondary)', whiteSpace: 'pre-line' }}>
                {market.insight ? (
                    <p>{market.insight}</p>
                ) : (
                    <>
                        <p>
                            <strong>해외 시장 핵심 테마:</strong> 현재 시장 데이터를 분석 중입니다. 잠시 후 업데이트됩니다.
                        </p>
                    </>
                )}
            </div>
        </div>
    );
};

export default MarketInsight;
