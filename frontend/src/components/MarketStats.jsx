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
            {Object.entries(market).map(([key, value]) => (
                <div key={key} style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '4px' }}>{key}</div>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                        {typeof value === 'number' ? value.toLocaleString() : value}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default MarketStats;
