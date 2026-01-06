{
    (() => {
        const signals = [
            ...(history?.gold_30m || []),
            ...(history?.gold_5m || []),
            ...(history?.dead_5m || [])
        ];

        if (signals.length === 0) {
            return (
                <div style={{ padding: '20px', textAlign: 'center', color: '#666', fontSize: '0.8rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                    Waiting for signals...
                </div>
            );
        }

        return signals.map((sig, idx) => {
            const isGold = sig.type && sig.type.includes('골든');
            return (
                <div key={idx} style={{
                    background: 'rgba(255,255,255,0.03)',
                    padding: '10px',
                    borderRadius: '8px',
                    borderLeft: isGold ? `3px solid ${mainColor}` : '3px solid #777',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: isGold ? mainColor : '#ccc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {isGold ? '⚡ SIGNAL' : '💤 EXIT'} <span style={{ fontSize: '0.8rem', color: '#888' }}>| {sig.type}</span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '3px' }}>
                            {sig.time_ny} (NY) <span style={{ margin: '0 4px' }}>@</span> <b style={{ color: '#fff' }}>${sig.price}</b>
                        </div>
                    </div>
                </div>
            );
        });
    })()
}
