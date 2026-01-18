// 차트 섹션만 별도 파일로 작성 - 기존 파일에 삽입할 예정

// 1. Import 추가 필요
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Sector } from 'recharts';
import { useMemo } from 'react';

// 2. State 추가 필요
const [activeIndexGroup, setActiveIndexGroup] = useState(null);
const [activeIndexAsset, setActiveIndexAsset] = useState(null);
const [showDashboard, setShowDashboard] = useState(true);

// 3. holdingsByGroup 계산
const holdingsByGroup = useMemo(() => {
    const groups = {};
    activeHoldings.forEach(h => {
        const group = h.group_name || '기타';
        if (!groups[group]) groups[group] = [];
        groups[group].push(h);
    });
    return groups;
}, [activeHoldings]);

// 4. 차트 렌더링 코드 (Summary Cards 아래에 삽입)
<>
    {/* Charts Section */}
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '2rem', marginBottom: '2rem' }}>
        {/* Chart 1: 그룹별 주식 비중 */}
        <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.1), rgba(59,130,246,0.05))', border: '2px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', color: '#bfdbfe', fontSize: '1.1rem', fontWeight: '700' }}>그룹별 주식 비중 (Stock Allocation)</h3>
            <div style={{ minHeight: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <defs>
                            {(() => {
                                const colors = [
                                    { id: 'grad1', start: '#60a5fa', end: '#2563eb' },
                                    { id: 'grad2', start: '#34d399', end: '#059669' },
                                    { id: 'grad3', start: '#fbbf24', end: '#d97706' },
                                    { id: 'grad4', start: '#f472b6', end: '#db2777' },
                                    { id: 'grad5', start: '#a78bfa', end: '#7c3aed' }
                                ];
                                return colors.map(c => (
                                    <radialGradient key={c.id} id={c.id} cx="30%" cy="30%" r="70%">
                                        <stop offset="0%" stopColor={c.start} stopOpacity="1" />
                                        <stop offset="100%" stopColor={c.end} stopOpacity="0.85" />
                                    </radialGradient>
                                ));
                            })()}
                        </defs>
                        <Pie
                            data={(() => {
                                const chartData = Object.entries(holdingsByGroup).map(([group, items]) => ({
                                    name: group,
                                    value: items.reduce((acc, cur) => acc + cur.currentValue, 0)
                                }));
                                const total = chartData.reduce((s, d) => s + d.value, 0);
                                return chartData.map(d => ({ ...d, percentage: total > 0 ? (d.value / total * 100) : 0 }));
                            })()}
                            cx="50%" cy="50%"
                            innerRadius={65} outerRadius={105}
                            paddingAngle={5}
                            dataKey="value"
                            label={(entry) => entry.percentage > 5 ? `${entry.name}\n${entry.percentage.toFixed(0)}%` : ''}
                            labelLine={false}
                            activeIndex={activeIndexGroup}
                            activeShape={(props) => {
                                const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
                                return (
                                    <Sector
                                        cx={cx} cy={cy}
                                        innerRadius={innerRadius}
                                        outerRadius={outerRadius + 6}
                                        startAngle={startAngle}
                                        endAngle={endAngle}
                                        fill={fill}
                                        style={{ filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.3))' }}
                                    />
                                );
                            }}
                            onMouseEnter={(_, index) => setActiveIndexGroup(index)}
                            onMouseLeave={() => setActiveIndexGroup(null)}
                            animationDuration={800}
                            style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))' }}
                        >
                            {Object.keys(holdingsByGroup).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={`url(#grad${(index % 5) + 1})`} />
                            ))}
                        </Pie>
                        <Tooltip
                            formatter={(val, name, props) => [`$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${props.payload.percentage.toFixed(1)}%)`, name]}
                            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(59,130,246,0.5)', borderRadius: '8px', color: '#ffffff' }}
                            labelStyle={{ color: '#e0e7ff' }}
                            itemStyle={{ color: '#ffffff' }}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </div>
            {/* Neon Table Legend */}
            <div style={{ padding: '1rem', background: 'transparent' }}>
                <table style={{ width: '100%', fontSize: '0.9rem', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.3)' }}>
                            <th style={{ textAlign: 'left', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>그룹</th>
                            <th style={{ textAlign: 'right', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>비율</th>
                            <th style={{ textAlign: 'right', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>금액</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(() => {
                            const chartData = Object.entries(holdingsByGroup).map(([group, items]) => ({
                                name: group,
                                value: items.reduce((acc, cur) => acc + cur.currentValue, 0)
                            }));
                            const total = chartData.reduce((s, d) => s + d.value, 0);
                            const colors = ['#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];
                            return chartData.map((d, idx) => {
                                const pct = total > 0 ? (d.value / total * 100) : 0;
                                return (
                                    <tr key={idx} style={{ borderBottom: '1px solid rgba(71,85,105,0.2)' }}>
                                        <td style={{ padding: '0.7rem 0.4rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                            <span style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: colors[idx % 5], display: 'inline-block', boxShadow: `0 0 10px ${colors[idx % 5]}` }}></span>
                                            <span style={{ fontWeight: '600', color: '#e0e7ff', textShadow: `0 0 8px ${colors[idx % 5]}40` }}>{d.name}</span>
                                        </td>
                                        <td style={{ textAlign: 'right', padding: '0.7rem 0.4rem', fontWeight: '700', color: '#bfdbfe', textShadow: '0 0 6px rgba(191,219,254,0.4)' }}>{pct.toFixed(1)}%</td>
                                        <td style={{ textAlign: 'right', padding: '0.7rem 0.4rem', fontWeight: '700', color: '#e0e7ff', textShadow: '0 0 6px rgba(224,231,255,0.4)' }}>${d.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                    </tr>
                                );
                            });
                        })()}
                    </tbody>
                </table>
            </div>
        </div>

        {/* Chart 2: 전체 자산 구성 */}
        <div style={{ background: 'linear-gradient(135deg, rgba(30,58,138,0.1), rgba(59,130,246,0.05))', border: '2px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', color: '#bfdbfe', fontSize: '1.1rem', fontWeight: '700' }}>전체 자산 구성 (Total Portfolio)</h3>
            <div style={{ minHeight: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <defs>
                            <radialGradient id="stockGrad" cx="30%" cy="30%" r="70%">
                                <stop offset="0%" stopColor="#60a5fa" stopOpacity="1" />
                                <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.85" />
                            </radialGradient>
                            <radialGradient id="cashGrad" cx="30%" cy="30%" r="70%">
                                <stop offset="0%" stopColor="#c084fc" stopOpacity="1" />
                                <stop offset="100%" stopColor="#7c3aed" stopOpacity="0.85" />
                            </radialGradient>
                        </defs>
                        <Pie
                            data={(() => {
                                const stockVal = totalValueUSD;
                                const cashVal = Math.max(0, totalCapitalUSD - totalValueUSD);
                                const total = stockVal + cashVal;
                                return [
                                    { name: '주식', value: stockVal, percentage: total > 0 ? (stockVal / total * 100) : 0 },
                                    { name: '현금', value: cashVal, percentage: total > 0 ? (cashVal / total * 100) : 0 }
                                ];
                            })()}
                            cx="50%" cy="50%"
                            innerRadius={65} outerRadius={105}
                            paddingAngle={5}
                            dataKey="value"
                            label={(entry) => `${entry.name}\n${entry.percentage.toFixed(0)}%`}
                            labelLine={false}
                            activeIndex={activeIndexAsset}
                            activeShape={(props) => {
                                const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
                                return (
                                    <Sector
                                        cx={cx} cy={cy}
                                        innerRadius={innerRadius}
                                        outerRadius={outerRadius + 6}
                                        startAngle={startAngle}
                                        endAngle={endAngle}
                                        fill={fill}
                                        style={{ filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.3))' }}
                                    />
                                );
                            }}
                            onMouseEnter={(_, index) => setActiveIndexAsset(index)}
                            onMouseLeave={() => setActiveIndexAsset(null)}
                            animationDuration={800}
                            style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.15))' }}
                        >
                            <Cell fill="url(#stockGrad)" />
                            <Cell fill="url(#cashGrad)" />
                        </Pie>
                        <Tooltip
                            formatter={(val, name, props) => [`$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${props.payload.percentage.toFixed(1)}%)`, name]}
                            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(59,130,246,0.5)', borderRadius: '8px', color: '#ffffff' }}
                            labelStyle={{ color: '#e0e7ff' }}
                            itemStyle={{ color: '#ffffff' }}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </div>
            {/* Neon Table Legend */}
            <div style={{ padding: '1rem', background: 'transparent' }}>
                <table style={{ width: '100%', fontSize: '0.9rem', borderCollapse: 'collapse' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid rgba(59,130,246,0.3)' }}>
                            <th style={{ textAlign: 'left', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>항목</th>
                            <th style={{ textAlign: 'right', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>비율</th>
                            <th style={{ textAlign: 'right', padding: '0.6rem 0.4rem', color: '#bfdbfe', fontWeight: '700', textShadow: '0 0 10px rgba(59,130,246,0.6)', textTransform: 'uppercase', fontSize: '0.75rem' }}>금액</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(() => {
                            const stockVal = totalValueUSD;
                            const cashVal = Math.max(0, totalCapitalUSD - totalValueUSD);
                            const total = stockVal + cashVal;
                            const data = [
                                { name: '주식 (Stocks)', value: stockVal, color: '#06b6d4' },
                                { name: '현금 (Cash)', value: cashVal, color: '#a855f7' }
                            ];
                            return data.map((d, idx) => {
                                const pct = total > 0 ? (d.value / total * 100) : 0;
                                return (
                                    <tr key={idx} style={{ borderBottom: '1px solid rgba(71,85,105,0.2)' }}>
                                        <td style={{ padding: '0.7rem 0.4rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                            <span style={{ width: '14px', height: '14px', borderRadius: '50%', backgroundColor: d.color, display: 'inline-block', boxShadow: `0 0 10px ${d.color}` }}></span>
                                            <span style={{ fontWeight: '600', color: '#e0e7ff', textShadow: `0 0 8px ${d.color}40` }}>{d.name}</span>
                                        </td>
                                        <td style={{ textAlign: 'right', padding: '0.7rem 0.4rem', fontWeight: '700', color: '#bfdbfe', textShadow: '0 0 6px rgba(191,219,254,0.4)' }}>{pct.toFixed(1)}%</td>
                                        <td style={{ textAlign: 'right', padding: '0.7rem 0.4rem', fontWeight: '700', color: '#e0e7ff', textShadow: '0 0 6px rgba(224,231,255,0.4)' }}>${d.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                                    </tr>
                                );
                            });
                        })()}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</>
