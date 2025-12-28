import React from 'react';

const MarketStats = ({ market }) => {
    return (
        <div className="glass-panel" style={{
            display: 'flex',
            justifyContent: 'space-around',
            padding: '1rem',
            marginBottom: '2rem',
            flexWrap: 'wrap',
            gap: '1rem'
        }}>
            {Object.entries(market).map(([key, data]) => {
                const value = data.value !== undefined ? data.value : data;
                const change = data.change !== undefined ? data.change : 0;
                const isUp = change >= 0;

                return (
                    <div key={key} style={{ textAlign: 'center' }}>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '4px' }}>{key}</div>
                        <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                            {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}
                        </div>
                        {data.change !== undefined && (
                            <div style={{
                                fontSize: '0.85rem',
                                color: isUp ? 'var(--accent-red)' : 'var(--accent-blue)',
                                marginTop: '2px'
                            }}>
                                {isUp ? '+' : ''}{change.toFixed(2)}%
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

export default MarketStats;
