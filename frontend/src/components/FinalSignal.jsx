import React, { useMemo } from 'react';

const KRW_RATE = 1460; // Hardcoded for now, or could come from API

const FinalSignal = ({ stocks, total_assets }) => {

    // 1. Prepare Portfolio Data
    const portfolio = useMemo(() => {
        if (!stocks || stocks.length === 0) return [];

        const categorized = stocks.map(stock => {
            // Basic fields
            const isHeld = stock.is_held || false;
            const target = stock.target_ratio || 0;
            const currentRatio = stock.current_ratio || 0;
            const actionQty = stock.action_qty || 0;
            const heldQty = stock.held_qty || 0;
            const price = stock.current_price || 0;
            const currentValue = heldQty * price; // Value of holding

            // Name Fallback
            const displayName = stock.name && stock.name !== stock.ticker ? stock.name : stock.ticker;

            // Signal Logic
            let type = "WATCH";
            let action = "관망";

            if (actionQty > 0) {
                type = "BUY";
                action = `${actionQty}주 매수`;
            } else if (actionQty < 0) {
                type = "SELL";
                action = `${Math.abs(actionQty)}주 매도`;
            } else if (heldQty > 0) {
                type = "HOLD";
                action = "유지";
            }

            return {
                ...stock,
                type, action, target, currentRatio, actionQty, heldQty, displayName, currentValue
            };
        });

        // Filter: Strategy Targets OR Held Stocks
        const filtered = categorized.filter(s => s.target > 0 || s.is_held);

        // Sort: Target Ratio Descending
        filtered.sort((a, b) => b.target - a.target);

        return filtered;
    }, [stocks]);

    if (!portfolio || portfolio.length === 0) return null;

    // 2. Cash & Totals Calculation
    const cashUsd = total_assets?.cash_usd || 0;
    const cashKrw = total_assets?.cash_krw || 0;

    // Grand Total (Backend Truth)
    const grandTotalUsd = total_assets?.usd || 0;
    const grandTotalKrw = total_assets?.krw || 0;

    // Target Cash % = 100% - Sum(Stock Targets)
    const totalStockTarget = portfolio.reduce((sum, s) => sum + s.target, 0);
    const cashTargetRatio = Math.max(0, 100 - totalStockTarget);

    // Target Cash Amount (New)
    const targetCashUsd = (grandTotalUsd * cashTargetRatio) / 100;
    const targetCashKrw = targetCashUsd * KRW_RATE;

    // List Sum (Shown Stocks Value + Cash)
    const stockTotalValue = portfolio.reduce((sum, s) => sum + s.currentValue, 0);
    const listTotalUsd = stockTotalValue + cashUsd;
    const listTotalKrw = listTotalUsd * KRW_RATE;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '0.25rem', letterSpacing: '1px', textAlign: 'center' }}>
                ⭐ 리밸런싱 포트폴리오
            </h2>

            <div className="glass-panel" style={{ padding: '0', overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                        <tr style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontSize: '0.75rem' }}>#</th>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'left', fontSize: '0.75rem' }}>Stock</th>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontSize: '0.75rem' }}>Type</th>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center', fontSize: '0.75rem' }}>목표</th>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'left', fontSize: '0.75rem' }}>Action</th>
                            <th className="hide-mobile" style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontSize: '0.75rem' }}>Cost</th>
                            <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontSize: '0.75rem' }}>Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {/* STOCK ROWS */}
                        {portfolio.map((stock, index) => {
                            const isBuy = stock.type === 'BUY';
                            const isSell = stock.type === 'SELL';
                            const rowBg = index % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent';

                            const estCostUsd = stock.actionQty * (stock.current_price || 0);
                            const estCostKrw = estCostUsd * KRW_RATE;

                            const priceUsd = stock.current_price || 0;
                            const priceKrw = priceUsd * KRW_RATE;

                            return (
                                <tr key={stock.ticker} style={{ background: rowBg, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '0.5rem', textAlign: 'center', fontWeight: 'bold', color: index === 0 ? 'var(--accent-gold)' : '#ccc', fontSize: '0.8rem' }}>
                                        {index + 1}
                                    </td>
                                    <td style={{ padding: '0.5rem', fontWeight: 'bold', fontSize: '0.9rem' }}>
                                        {stock.ticker}
                                        <div style={{
                                            fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 'normal',
                                            maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                                            lineHeight: '1.2'
                                        }} title={stock.name}>
                                            {stock.displayName}
                                        </div>
                                    </td>
                                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                                        <span style={{
                                            padding: '2px 6px', borderRadius: '4px', fontWeight: 'bold', fontSize: '0.7rem',
                                            background: isBuy ? 'rgba(34, 197, 94, 0.2)' : isSell ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                            color: isBuy ? '#4ade80' : isSell ? '#f87171' : '#ccc'
                                        }}>
                                            {stock.type}
                                        </span>
                                    </td>
                                    <td style={{ padding: '0.5rem', textAlign: 'center', fontWeight: 'bold', color: '#fff', fontSize: '0.85rem' }}>
                                        {stock.target}%
                                    </td>
                                    <td style={{ padding: '0.5rem', color: isBuy ? '#4ade80' : isSell ? '#f87171' : '#ddd', fontWeight: 'bold', fontSize: '0.8rem' }}>
                                        {stock.action}
                                    </td>
                                    <td className="hide-mobile" style={{ padding: '0.5rem', textAlign: 'right' }}>
                                        {estCostUsd !== 0 ? (
                                            <>
                                                <div style={{ fontWeight: 'bold', color: estCostUsd > 0 ? '#4ade80' : estCostUsd < 0 ? '#f87171' : '#ccc', fontSize: '0.8rem' }}>
                                                    ${Math.abs(estCostUsd).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                                </div>
                                                <div style={{ fontSize: '0.65rem', color: '#888' }}>
                                                    ₩ {(Math.abs(estCostKrw) / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 })}만
                                                </div>
                                            </>
                                        ) : '-'}
                                    </td>
                                    <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                                        <div style={{ color: '#fff', fontSize: '0.85rem' }}>${priceUsd.toFixed(2)}</div>
                                        <div style={{ fontSize: '0.65rem', color: '#666' }}>₩ {(priceKrw).toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                                    </td>
                                </tr>
                            );
                        })}

                        {/* CASH ROW (With Target %) */}
                        <tr style={{ borderTop: '2px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)' }}>
                            <td colSpan="2" style={{ padding: '1rem', fontWeight: 'bold', fontSize: '1.2rem' }}>
                                💵 CASH (현금)
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'center' }}>
                                <span style={{ padding: '4px 10px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', color: '#ccc', fontWeight: 'bold', fontSize: '0.8rem' }}>HOLD</span>
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'center', fontWeight: 'bold', color: 'var(--accent-gold)' }}>
                                {cashTargetRatio.toFixed(0)}%
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'left', color: '#ccc' }}>
                                -
                            </td>
                            {/* Target Cash Amount */}
                            <td style={{ padding: '1rem', textAlign: 'right' }}>
                                <div style={{ fontWeight: 'bold', color: 'var(--accent-gold)' }}>Target: ${targetCashUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: '0.75rem', color: '#888' }}>₩ {(targetCashKrw / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 })}만</div>
                            </td>
                            {/* Current Cash Amount */}
                            <td style={{ textAlign: 'right', padding: '1rem' }}>
                                <div style={{ fontWeight: 'bold', color: '#fff' }}>Cur: ${cashUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: '0.75rem', color: '#888' }}>₩ {(cashKrw / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 })}만</div>
                            </td>
                        </tr>

                        {/* LIST TOTAL ROW */}
                        <tr style={{ background: 'rgba(255,255,255,0.05)', borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                            <td colSpan="2" style={{ padding: '1rem', fontWeight: '800', fontSize: '1.1rem', color: '#ccc' }}>
                                TABLE TOTAL (LIST)
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'center' }}>-</td>
                            <td style={{ padding: '1rem', textAlign: 'center', fontWeight: 'bold', color: '#fff' }}>
                                100%
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'left', color: '#ccc' }}>
                                리스트 합계
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'right' }}>
                                <div style={{ fontWeight: 'bold', color: '#fff', fontSize: '1.1rem' }}>${listTotalUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: '0.85rem', color: '#aaa' }}>₩ {(listTotalKrw / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 })}만</div>
                            </td>
                            <td style={{ textAlign: 'right', padding: '1rem' }}>-</td>
                        </tr>

                        {/* GRAND TOTAL ROW */}
                        <tr style={{ background: 'linear-gradient(90deg, rgba(255,255,255,0.05), rgba(16, 185, 129, 0.1))', borderTop: '2px solid var(--accent-gold)' }}>
                            <td colSpan="2" style={{ padding: '1.2rem 1rem', fontWeight: '800', fontSize: '1.3rem', color: 'var(--accent-gold)' }}>
                                TOTAL NET ASSETS (총자산)
                            </td>
                            <td colSpan="3" style={{ padding: '1rem', textAlign: 'right', color: '#ccc', verticalAlign: 'middle' }}>
                                <span style={{ marginRight: '1rem', fontSize: '0.9rem' }}>환율(USD/KRW): <strong style={{ color: '#fff' }}>{KRW_RATE}</strong></span>
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'right' }}>
                                <div style={{ fontWeight: '800', color: 'var(--accent-gold)', fontSize: '1.4rem' }}>${grandTotalUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                                <div style={{ fontSize: '1rem', color: '#ddd' }}>₩ {(grandTotalKrw / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 })}만</div>
                            </td>
                            <td style={{ textAlign: 'right', padding: '1rem' }}>-</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default FinalSignal;
