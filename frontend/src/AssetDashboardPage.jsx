import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend, Area, ComposedChart, BarChart, Bar, Cell, PieChart, Pie } from 'recharts';
import './AssetDashboardPage.css';

const AssetDashboardPage = () => {
    const [assets, setAssets] = useState([]);
    const [summary, setSummary] = useState({});
    const [goals, setGoals] = useState([]);
    const [strategies, setStrategies] = useState([]);
    const [loading, setLoading] = useState(true);

    // 전략 분석 모달
    const [selectedStrategy, setSelectedStrategy] = useState(null);
    const [strategyPerformance, setStrategyPerformance] = useState(null);
    const [loadingPerformance, setLoadingPerformance] = useState(false);

    // 전략 수정 모달
    const [editingStrategy, setEditingStrategy] = useState(null);

    // 자산 수정/삭제
    const [editingAsset, setEditingAsset] = useState(null);
    const [showAssetList, setShowAssetList] = useState(false);

    // 입력 폼 상태
    const [showAssetForm, setShowAssetForm] = useState(false);

    const [showGoalForm, setShowGoalForm] = useState(false);
    const [showGoalList, setShowGoalList] = useState(false);
    const [showStrategyForm, setShowStrategyForm] = useState(false);


    const [assetForm, setAssetForm] = useState({
        record_date: new Date().toISOString().split('T')[0],
        total_assets: '',
        daily_return_pct: '',
        daily_pnl: '',
        note: ''
    });

    const [goalForm, setGoalForm] = useState({
        goal_name: '',
        target_amount: '',
        target_date: ''
    });

    const [strategyForm, setStrategyForm] = useState({
        strategy_name: '',
        description: '',
        start_date: new Date().toISOString().split('T')[0],
        end_date: '',
        initial_assets: '',
        target_assets: '',
        target_return_pct: ''
    });

    // 목표 수익률 자동 계산
    useEffect(() => {
        const initial = parseFloat(strategyForm.initial_assets);
        const target = parseFloat(strategyForm.target_assets);
        if (initial > 0 && target > 0) {
            const pct = ((target - initial) / initial * 100).toFixed(2);
            setStrategyForm(prev => ({ ...prev, target_return_pct: pct }));
        }
    }, [strategyForm.initial_assets, strategyForm.target_assets]);

    useEffect(() => {
        fetchAll();

    }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [assetsRes, summaryRes, goalsRes, strategiesRes] = await Promise.all([
                axios.get('/api/assets?limit=90'),
                axios.get('/api/assets/summary'),
                axios.get('/api/goals'),
                axios.get('/api/strategies')
            ]);
            setAssets(assetsRes.data || []);
            setSummary(summaryRes.data || {});
            setGoals(goalsRes.data || []);
            setStrategies(strategiesRes.data || []);
        } catch (e) {
            console.error('Fetch error:', e);
        }
        setLoading(false);
    };

    // 전략 성과 분석 로드
    const loadStrategyPerformance = async (strategyId) => {
        setLoadingPerformance(true);
        try {
            const res = await axios.get(`/api/strategies/${strategyId}/performance`);
            setStrategyPerformance(res.data);
        } catch (e) {
            console.error('Performance fetch error:', e);
            setStrategyPerformance(null);
        }
        setLoadingPerformance(false);
    };

    const handleOpenAnalysis = async (strategy) => {
        setSelectedStrategy(strategy);
        await loadStrategyPerformance(strategy.id);
    };

    const handleCloseAnalysis = () => {
        setSelectedStrategy(null);
        setStrategyPerformance(null);
    };

    // 전략 수정 모달 열기
    const handleOpenEdit = (strategy) => {
        setEditingStrategy(strategy);
        setStrategyForm({
            strategy_name: strategy.strategy_name || '',
            description: strategy.description || '',
            start_date: strategy.start_date?.slice(0, 10) || '',
            end_date: strategy.end_date?.slice(0, 10) || '',
            initial_assets: strategy.initial_assets || '',
            target_assets: strategy.target_assets || '',
            target_return_pct: strategy.target_return_pct || ''
        });
    };

    const handleCloseEdit = () => {
        setEditingStrategy(null);
        setStrategyForm({
            strategy_name: '', description: '', start_date: new Date().toISOString().split('T')[0],
            end_date: '', initial_assets: '', target_assets: '', target_return_pct: ''
        });
    };

    // 전략 상태 변경 (완료 처리)
    const handleCompleteStrategy = async (strategyId) => {
        if (!window.confirm('이 전략을 완료 처리하시겠습니까?')) return;
        try {
            await axios.put(`/api/strategies/${strategyId}`, {
                status: 'COMPLETED',
                end_date: new Date().toISOString().split('T')[0]
            });
            fetchAll();
            handleCloseAnalysis();
        } catch (e) {
            alert('상태 변경 실패');
        }
    };

    // 전략 삭제
    const handleDeleteStrategy = async (strategyId) => {
        if (!window.confirm('이 전략을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return;
        try {
            await axios.delete(`/api/strategies/${strategyId}`);
            fetchAll();
            handleCloseAnalysis();
            handleCloseEdit();
        } catch (e) {
            alert('삭제 실패');
        }
    };

    // 전략 수정 저장
    const handleUpdateStrategy = async (e) => {
        e.preventDefault();
        if (!editingStrategy) return;
        try {
            await axios.put(`/api/strategies/${editingStrategy.id}`, {
                ...strategyForm,
                initial_assets: parseFloat(strategyForm.initial_assets) || null,
                target_assets: parseFloat(strategyForm.target_assets) || null,
                target_return_pct: parseFloat(strategyForm.target_return_pct) || null,
                end_date: strategyForm.end_date || null
            });
            handleCloseEdit();
            fetchAll();
        } catch (e) {
            alert('수정 실패: ' + (e.response?.data?.message || e.message));
        }
    };

    const handleAssetSubmit = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/assets', {
                ...assetForm,
                total_assets: parseFloat(assetForm.total_assets) || 0,
                daily_return_pct: parseFloat(assetForm.daily_return_pct) || null,
                daily_pnl: parseFloat(assetForm.daily_pnl) || null
            });
            setShowAssetForm(false);
            setAssetForm({ record_date: new Date().toISOString().split('T')[0], total_assets: '', daily_return_pct: '', daily_pnl: '', note: '' });
            fetchAll();
        } catch (e) {
            alert('저장 실패: ' + (e.response?.data?.message || e.message));
        }
    };

    // 자산 수정 시작
    const handleEditAsset = (asset) => {
        setEditingAsset(asset);
        setAssetForm({
            record_date: asset.record_date,
            total_assets: asset.total_assets || '',
            daily_return_pct: asset.daily_return_pct || '',
            daily_pnl: asset.daily_pnl || '',
            note: asset.note || ''
        });
        setShowAssetForm(true);
    };

    // 자산 삭제
    const handleDeleteAsset = async (record_date) => {
        if (!window.confirm(`${record_date} 자산 데이터를 삭제하시겠습니까?`)) return;
        try {
            await axios.delete(`/api/assets/${record_date}`);
            fetchAll();
        } catch (e) {
            alert('삭제 실패');
        }
    };

    // 자산 폼 닫기
    const handleCloseAssetForm = () => {
        setShowAssetForm(false);
        setEditingAsset(null);
        setAssetForm({ record_date: new Date().toISOString().split('T')[0], total_assets: '', daily_return_pct: '', daily_pnl: '', note: '' });
    };

    const handleGoalSubmit = async (e) => {

        e.preventDefault();
        try {
            await axios.post('/api/goals', {
                ...goalForm,
                target_amount: parseFloat(goalForm.target_amount) || 0
            });
            setShowGoalForm(false);
            setGoalForm({ goal_name: '', target_amount: '', target_date: '' });
            fetchAll();
        } catch (e) {
            alert('저장 실패: ' + (e.response?.data?.message || e.message));
        }
    };

    // 목표 수정 시작
    const [editingGoal, setEditingGoal] = useState(null);

    const handleEditGoal = (goal) => {
        setEditingGoal(goal);
        setGoalForm({
            goal_name: goal.goal_name || '',
            target_amount: goal.target_amount || '',
            target_date: goal.target_date || ''
        });
        setShowGoalForm(true);
    };

    const handleUpdateGoal = async (e) => {
        e.preventDefault();
        try {
            await axios.put(`/api/goals/${editingGoal.id}`, {
                ...goalForm,
                target_amount: parseFloat(goalForm.target_amount) || 0
            });
            setShowGoalForm(false);
            setEditingGoal(null);
            setGoalForm({ goal_name: '', target_amount: '', target_date: '' });
            fetchAll();
        } catch (e) {
            alert('수정 실패: ' + (e.response?.data?.message || e.message));
        }
    };

    const handleDeleteGoal = async (goalId) => {
        if (!window.confirm('이 목표를 삭제하시겠습니까?')) return;
        try {
            await axios.delete(`/api/goals/${goalId}`);
            fetchAll();
        } catch (e) {
            alert('삭제 실패');
        }
    };

    const handleSetActiveGoal = async (goalId) => {
        try {
            await axios.put(`/api/goals/${goalId}`, { is_active: true });
            fetchAll();
        } catch (e) {
            alert('활성화 실패');
        }
    };

    const handleStrategySubmit = async (e) => {

        e.preventDefault();
        try {
            await axios.post('/api/strategies', {
                ...strategyForm,
                initial_assets: parseFloat(strategyForm.initial_assets) || null,
                target_assets: parseFloat(strategyForm.target_assets) || null,
                target_return_pct: parseFloat(strategyForm.target_return_pct) || null,
                end_date: strategyForm.end_date || null
            });
            setShowStrategyForm(false);
            setStrategyForm({ strategy_name: '', description: '', start_date: new Date().toISOString().split('T')[0], end_date: '', initial_assets: '', target_assets: '', target_return_pct: '' });
            fetchAll();
        } catch (e) {
            alert('저장 실패: ' + (e.response?.data?.message || e.message));
        }
    };

    // 차트 데이터 준비
    const chartData = [...assets].reverse().map(a => ({
        date: a.record_date,
        displayDate: a.record_date?.slice(5),
        total: parseFloat(a.total_assets) || 0,
        change: parseFloat(a.daily_change) || 0,
        changePct: parseFloat(a.daily_change_pct) || 0
    }));

    const activeGoal = summary.active_goal;
    const latestAsset = summary.latest;
    const targetAmount = activeGoal ? parseFloat(activeGoal.target_amount) : null;
    const remainingToGoal = latestAsset && targetAmount ? targetAmount - parseFloat(latestAsset.total_assets) : null;
    const goalProgress = latestAsset && targetAmount && targetAmount > 0 ? (parseFloat(latestAsset.total_assets) / targetAmount) * 100 : 0;

    // 원화 포맷
    const formatKRW = (amount) => {
        if (!amount && amount !== 0) return '-';
        return new Intl.NumberFormat('ko-KR').format(Math.round(amount)) + '원';
    };

    // 성과 분석용 파이 차트 데이터
    const getPieData = () => {
        if (!strategyPerformance) return [];
        return [
            { name: '수익', value: strategyPerformance.wins || 0, color: '#22c55e' },
            { name: '손실', value: strategyPerformance.losses || 0, color: '#ef4444' }
        ].filter(d => d.value > 0);
    };

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center', color: '#fff' }}>Loading...</div>;

    return (
        <div className="dashboard-container">
            <div className="dashboard-glass-panel">
                {/* Header */}
                <div className="dashboard-header">
                    <h1 className="dashboard-title">💰 자산 현황</h1>
                    <p className="dashboard-subtitle">일별 자산 추이 및 목표 관리 (원화 기준)</p>
                </div>

                {/* Summary Cards */}
                <div className="dashboard-summary-grid">
                    <div className="dashboard-card" style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)' }}>
                        <div className="dashboard-card-label" style={{ color: 'rgba(255,255,255,0.8)' }}>현재 자산</div>
                        <div className="dashboard-card-value">{latestAsset ? formatKRW(latestAsset.total_assets) : '0원'}</div>
                        <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                            <span style={{ color: (summary.monthly_change_pct || 0) >= 0 ? '#4ade80' : '#ef4444', fontWeight: 'bold' }}>
                                {(summary.monthly_change_pct || 0) >= 0 ? '▲' : '▼'} {Math.abs(summary.monthly_change_pct || 0).toFixed(2)}%
                            </span>
                            <span style={{ color: 'rgba(255,255,255,0.6)' }}>(월간 수익)</span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.2rem' }}>
                            {formatKRW(summary.monthly_change || 0)} 변동
                        </div>
                    </div>

                    <div className="dashboard-card" style={{ background: activeGoal ? 'linear-gradient(135deg, #d4af37 0%, #a67c00 100%)' : 'linear-gradient(135deg, #64748b 0%, #475569 100%)' }}>
                        <div className="dashboard-card-label">목표 금액</div>
                        <div className="dashboard-card-value">{activeGoal ? formatKRW(activeGoal.target_amount) : '미설정'}</div>
                        {activeGoal && <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.8)' }}>{activeGoal.goal_name}</div>}
                        {activeGoal?.target_date && <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', marginTop: '0.25rem' }}>📅 목표일: {activeGoal.target_date}</div>}
                    </div>

                    <div className="dashboard-card" style={{ background: remainingToGoal !== null && remainingToGoal <= 0 ? 'linear-gradient(135deg, #059669 0%, #047857 100%)' : 'linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%)' }}>
                        <div className="dashboard-card-label">목표까지</div>
                        <div className="dashboard-card-value">{remainingToGoal !== null ? (remainingToGoal <= 0 ? '🎉 달성!' : formatKRW(remainingToGoal)) : '-'}</div>
                        {goalProgress > 0 && (
                            <div style={{ marginTop: '0.5rem' }}>
                                <div style={{ background: 'rgba(255,255,255,0.3)', borderRadius: '10px', height: '8px', overflow: 'hidden' }}>
                                    <div style={{ background: 'white', height: '100%', width: `${Math.min(goalProgress, 100)}%`, borderRadius: '10px', transition: 'width 0.5s ease' }} />
                                </div>
                                <div style={{ fontSize: '0.8rem', marginTop: '0.25rem', color: 'rgba(255,255,255,0.8)' }}>{goalProgress.toFixed(1)}% 달성</div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="dashboard-actions">
                    <button className="dashboard-btn-primary" onClick={() => { setShowAssetForm(!showAssetForm); if (showAssetForm) handleCloseAssetForm(); }}>{showAssetForm ? '닫기' : '📝 자산 입력'}</button>
                    <button className="dashboard-btn-secondary" onClick={() => setShowAssetList(!showAssetList)}>{showAssetList ? '목록 닫기' : '📋 자산 내역'}</button>
                    <button className="dashboard-btn-secondary" onClick={() => setShowGoalForm(!showGoalForm)}>{showGoalForm ? '닫기' : '🎯 목표 설정'}</button>
                    <button className="dashboard-btn-secondary" onClick={() => setShowGoalList && setShowGoalList(!showGoalList)}>{showGoalList ? '목표 닫기' : '📋 목표 내역'}</button>
                    <button className="dashboard-btn-secondary" onClick={() => setShowStrategyForm(!showStrategyForm)}>{showStrategyForm ? '닫기' : '📋 전략 등록'}</button>
                </div>


                {/* Asset List - 수정/삭제 가능 */}
                {showAssetList && (
                    <div className="dashboard-section-panel">
                        <h3 className="dashboard-section-title">📋 자산 내역 (최근 30일)</h3>
                        <div className="dashboard-table-container">
                            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '600px' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: '#94a3b8', fontSize: '0.85rem' }}>날짜</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'right', color: '#94a3b8', fontSize: '0.85rem' }}>총 자산</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'right', color: '#94a3b8', fontSize: '0.85rem' }}>수익률</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'right', color: '#94a3b8', fontSize: '0.85rem' }}>손익</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left', color: '#94a3b8', fontSize: '0.85rem' }}>메모</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>관리</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {assets.slice(0, 30).map(a => (
                                        <tr key={a.record_date} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                            <td style={{ padding: '0.75rem', color: 'white' }}>{a.record_date}</td>
                                            <td style={{ padding: '0.75rem', textAlign: 'right', color: 'white' }}>{formatKRW(a.total_assets)}</td>
                                            <td style={{ padding: '0.75rem', textAlign: 'right', color: (a.daily_change_pct || 0) >= 0 ? '#22c55e' : '#ef4444' }}>{(a.daily_change_pct || 0) >= 0 ? '+' : ''}{(a.daily_change_pct || 0).toFixed(2)}%</td>
                                            <td style={{ padding: '0.75rem', textAlign: 'right', color: (a.daily_change || 0) >= 0 ? '#22c55e' : '#ef4444' }}>{(a.daily_change || 0) >= 0 ? '+' : ''}{formatKRW(a.daily_change || 0)}</td>
                                            <td style={{ padding: '0.75rem', color: '#94a3b8', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.note || '-'}</td>
                                            <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                                                <button onClick={() => handleEditAsset(a)} style={{ padding: '0.25rem 0.5rem', background: 'rgba(251,191,36,0.2)', border: 'none', borderRadius: '4px', color: '#fbbf24', fontSize: '0.75rem', cursor: 'pointer', marginRight: '0.5rem' }}>수정</button>
                                                <button onClick={() => handleDeleteAsset(a.record_date)} style={{ padding: '0.25rem 0.5rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '4px', color: '#ef4444', fontSize: '0.75rem', cursor: 'pointer' }}>삭제</button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {assets.length === 0 && <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>자산 데이터가 없습니다.</div>}
                        </div>
                    </div>
                )}

                {/* Goal List - 목표 내역 */}
                {showGoalList && (
                    <div className="dashboard-section-panel">
                        <h3 className="dashboard-section-title">📋 목표 내역</h3>
                        <div className="dashboard-strategy-list">
                            {goals.length > 0 ? goals.map(g => {
                                const isAchieved = latestAsset && parseFloat(latestAsset.total_assets) >= parseFloat(g.target_amount);
                                const progress = latestAsset ? (parseFloat(latestAsset.total_assets) / parseFloat(g.target_amount) * 100) : 0;
                                return (
                                    <div key={g.id} className="dashboard-strategy-item" style={{ border: g.is_active ? '2px solid #fbbf24' : '1px solid rgba(255,255,255,0.1)' }}>
                                        <div className="dashboard-strategy-header">
                                            <div>
                                                <span style={{ fontSize: '1.1rem', fontWeight: '600', color: 'white' }}>{g.goal_name}</span>
                                                {g.is_active && <span style={{ marginLeft: '0.5rem', padding: '0.2rem 0.5rem', background: 'rgba(251,191,36,0.3)', borderRadius: '4px', fontSize: '0.7rem', color: '#fbbf24' }}>활성</span>}
                                                {isAchieved && <span style={{ marginLeft: '0.5rem', padding: '0.2rem 0.5rem', background: 'rgba(34,197,94,0.3)', borderRadius: '4px', fontSize: '0.7rem', color: '#22c55e' }}>🎉 달성</span>}
                                            </div>
                                            <span style={{ fontSize: '1.2rem', fontWeight: '700', color: isAchieved ? '#22c55e' : 'white' }}>{formatKRW(g.target_amount)}</span>
                                        </div>
                                        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem', flexWrap: 'wrap' }}>
                                            {g.target_date && <span>📅 목표일: {g.target_date}</span>}
                                            <span>📊 달성률: {progress.toFixed(1)}%</span>
                                        </div>
                                        <div style={{ marginTop: '0.5rem', background: 'rgba(255,255,255,0.2)', borderRadius: '8px', height: '6px', overflow: 'hidden' }}>
                                            <div style={{ background: isAchieved ? '#22c55e' : '#fbbf24', height: '100%', width: `${Math.min(progress, 100)}%`, borderRadius: '8px', transition: 'width 0.5s ease' }} />
                                        </div>
                                        {/* 버튼 영역 */}
                                        <div className="dashboard-strategy-actions" style={{ marginTop: '0.75rem' }}>
                                            {!g.is_active && <button onClick={() => handleSetActiveGoal(g.id)} style={{ padding: '0.4rem 0.8rem', background: 'rgba(251,191,36,0.2)', border: 'none', borderRadius: '6px', color: '#fbbf24', fontSize: '0.8rem', cursor: 'pointer' }}>활성화</button>}
                                            <button onClick={() => handleEditGoal(g)} style={{ padding: '0.4rem 0.8rem', background: 'rgba(96,165,250,0.2)', border: 'none', borderRadius: '6px', color: '#60a5fa', fontSize: '0.8rem', cursor: 'pointer' }}>수정</button>
                                            <button onClick={() => handleDeleteGoal(g.id)} style={{ padding: '0.4rem 0.8rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '6px', color: '#ef4444', fontSize: '0.8rem', cursor: 'pointer' }}>삭제</button>
                                        </div>
                                    </div>

                                );
                            }) : (
                                <div style={{ textAlign: 'center', padding: '2rem', color: 'rgba(255,255,255,0.5)' }}>등록된 목표가 없습니다.</div>
                            )}
                        </div>
                    </div>
                )}

                {/* Asset Input Form */}

                {showAssetForm && (
                    <div className="dashboard-section-panel">
                        <h3 className="dashboard-section-title">{editingAsset ? '✏️ 자산 수정' : '📝 일별 자산 입력'}</h3>
                        <form onSubmit={handleAssetSubmit} className="dashboard-form">

                            <div className="dashboard-form-row">
                                <div className="dashboard-form-group"><label className="dashboard-label">날짜</label><input type="date" className="dashboard-input" value={assetForm.record_date} onChange={e => setAssetForm({ ...assetForm, record_date: e.target.value })} required disabled={!!editingAsset} /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">총 자산 (원)</label><input type="number" step="1" className="dashboard-input" value={assetForm.total_assets} onChange={e => setAssetForm({ ...assetForm, total_assets: e.target.value })} required placeholder="예: 50000000" /></div>
                                {!editingAsset && <div className="dashboard-form-group"><label className="dashboard-label">수익률 (%)</label><input type="number" step="0.01" className="dashboard-input" value={assetForm.daily_return_pct} onChange={e => setAssetForm({ ...assetForm, daily_return_pct: e.target.value })} placeholder="예: 2.5" /></div>}
                                {!editingAsset && <div className="dashboard-form-group"><label className="dashboard-label">손익 (원)</label><input type="number" step="1" className="dashboard-input" value={assetForm.daily_pnl} onChange={e => setAssetForm({ ...assetForm, daily_pnl: e.target.value })} placeholder="예: 500000" /></div>}
                            </div>

                            <div><label className="dashboard-label">메모</label><input type="text" className="dashboard-input" value={assetForm.note} onChange={e => setAssetForm({ ...assetForm, note: e.target.value })} placeholder="참고 메모" /></div>
                            <button type="submit" className="dashboard-btn-primary" style={{ alignSelf: 'flex-end' }}>저장</button>
                        </form>
                    </div>
                )}

                {/* Goal Input Form */}
                {showGoalForm && (
                    <div className="dashboard-section-panel" style={{ background: 'linear-gradient(135deg, #d4af37 0%, #a67c00 100%)' }}>
                        <h3 className="dashboard-section-title">{editingGoal ? '✏️ 목표 수정' : '🎯 목표 금액 설정'}</h3>
                        <form onSubmit={editingGoal ? handleUpdateGoal : handleGoalSubmit} className="dashboard-form">
                            <div className="dashboard-form-row">
                                <div className="dashboard-form-group"><label className="dashboard-label">목표명</label><input type="text" className="dashboard-input" value={goalForm.goal_name} onChange={e => setGoalForm({ ...goalForm, goal_name: e.target.value })} required placeholder="예: 2026년 1분기 목표" /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 금액 (원)</label><input type="number" step="1" className="dashboard-input" value={goalForm.target_amount} onChange={e => setGoalForm({ ...goalForm, target_amount: e.target.value })} required placeholder="예: 100000000" /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 달성일</label><input type="date" className="dashboard-input" value={goalForm.target_date} onChange={e => setGoalForm({ ...goalForm, target_date: e.target.value })} /></div>
                            </div>
                            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                                {editingGoal && <button type="button" onClick={() => { setEditingGoal(null); setShowGoalForm(false); setGoalForm({ goal_name: '', target_amount: '', target_date: '' }); }} style={{ padding: '0.75rem 1.5rem', background: 'rgba(100,116,139,0.3)', border: 'none', borderRadius: '8px', color: '#94a3b8', cursor: 'pointer' }}>취소</button>}
                                <button type="submit" className="dashboard-btn-primary" style={{ background: '#1e3a8a' }}>{editingGoal ? '수정' : '저장'}</button>
                            </div>
                        </form>
                    </div>
                )}


                {/* Strategy Input Form */}
                {showStrategyForm && (
                    <div className="dashboard-section-panel" style={{ background: 'linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%)' }}>
                        <h3 className="dashboard-section-title">📋 전략 등록</h3>
                        <form onSubmit={handleStrategySubmit} className="dashboard-form">
                            <div className="dashboard-form-row">
                                <div style={{ flex: 2, minWidth: '200px' }}><label className="dashboard-label">전략명</label><input type="text" className="dashboard-input" value={strategyForm.strategy_name} onChange={e => setStrategyForm({ ...strategyForm, strategy_name: e.target.value })} required placeholder="예: SOXL 5분봉 GC 전략" /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">시작일</label><input type="date" className="dashboard-input" value={strategyForm.start_date} onChange={e => setStrategyForm({ ...strategyForm, start_date: e.target.value })} required /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">종료일</label><input type="date" className="dashboard-input" value={strategyForm.end_date} onChange={e => setStrategyForm({ ...strategyForm, end_date: e.target.value })} /></div>
                            </div>
                            <div className="dashboard-form-row">
                                <div className="dashboard-form-group"><label className="dashboard-label">시작 자산 (원)</label><input type="number" step="1" className="dashboard-input" value={strategyForm.initial_assets} onChange={e => setStrategyForm({ ...strategyForm, initial_assets: e.target.value })} placeholder="예: 40000000" /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 자산 (원)</label><input type="number" step="1" className="dashboard-input" value={strategyForm.target_assets} onChange={e => setStrategyForm({ ...strategyForm, target_assets: e.target.value })} placeholder="예: 60000000" /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 수익률 (%) <span style={{ fontSize: '0.7rem', color: '#a78bfa' }}>자동계산</span></label><input type="number" step="0.01" className="dashboard-input" value={strategyForm.target_return_pct} readOnly style={{ background: 'rgba(255,255,255,0.1)', cursor: 'default' }} placeholder="자동 계산됨" /></div>
                            </div>

                            <div><label className="dashboard-label">설명</label><textarea className="dashboard-input" value={strategyForm.description} onChange={e => setStrategyForm({ ...strategyForm, description: e.target.value })} placeholder="전략에 대한 간단한 설명" rows={2} style={{ resize: 'vertical' }} /></div>
                            <button type="submit" className="dashboard-btn-primary" style={{ alignSelf: 'flex-end', background: '#1e3a8a' }}>저장</button>
                        </form>
                    </div>
                )}

                {/* Asset Chart - 원화 표시 */}
                <div className="dashboard-chart-container">
                    <h3 className="dashboard-section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        📈 자산 추이 {targetAmount && <span style={{ fontSize: '0.9rem', color: '#d4af37' }}>목표: {formatKRW(targetAmount)}</span>}
                    </h3>
                    {chartData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={400}>
                            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                                <defs><linearGradient id="colorAsset" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} /><stop offset="95%" stopColor="#3b82f6" stopOpacity={0} /></linearGradient></defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="displayDate" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} domain={['auto', 'auto']} />
                                <Tooltip contentStyle={{ background: 'rgba(30, 41, 59, 0.95)', border: '1px solid rgba(147, 197, 253, 0.3)', borderRadius: '12px', color: '#fff' }} formatter={(value, name) => { if (name === 'total') return [formatKRW(value), '총 자산']; return [value, name]; }} labelFormatter={(label) => `날짜: ${label}`} />
                                <Legend />
                                {targetAmount && <ReferenceLine y={targetAmount} stroke="#d4af37" strokeDasharray="5 5" strokeWidth={2} label={{ value: `🎯 목표`, fill: '#d4af37', fontSize: 12, position: 'right' }} />}
                                <Area type="monotone" dataKey="total" fill="url(#colorAsset)" stroke="none" />
                                <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={3} dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }} activeDot={{ r: 8, fill: '#60a5fa' }} name="총 자산" />
                            </ComposedChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>자산 데이터가 없습니다. 위에서 자산을 입력해주세요.</div>
                    )}
                </div>

                {/* Strategy List with Analysis/Edit/Delete Buttons */}
                {strategies.length > 0 && (
                    <div className="dashboard-section-panel" style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', borderColor: 'rgba(167, 139, 250, 0.2)' }}>
                        <h3 className="dashboard-section-title">📋 등록된 전략</h3>
                        <div className="dashboard-strategy-list">
                            {strategies.map(s => (
                                <div key={s.id} className="dashboard-strategy-item">
                                    <div className="dashboard-strategy-header">
                                        <div>
                                            <span style={{ fontSize: '1.2rem', fontWeight: '700', color: 'white' }}>{s.strategy_name}</span>
                                            <span style={{ marginLeft: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600', background: s.status === 'ACTIVE' ? 'rgba(34,197,94,0.2)' : 'rgba(100,116,139,0.2)', color: s.status === 'ACTIVE' ? '#22c55e' : '#94a3b8' }}>
                                                {s.status === 'ACTIVE' ? '진행 중' : s.status === 'COMPLETED' ? '완료' : s.status}
                                            </span>
                                        </div>
                                        <div className="dashboard-strategy-actions">
                                            <button onClick={() => handleOpenAnalysis(s)} style={{ padding: '0.5rem 1rem', background: 'rgba(59,130,246,0.3)', border: 'none', borderRadius: '8px', color: '#60a5fa', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}>📊 분석</button>
                                            <button onClick={() => handleOpenEdit(s)} style={{ padding: '0.5rem 1rem', background: 'rgba(251,191,36,0.2)', border: 'none', borderRadius: '8px', color: '#fbbf24', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}>✏️ 수정</button>
                                            {s.status === 'ACTIVE' && (
                                                <button onClick={() => handleCompleteStrategy(s.id)} style={{ padding: '0.5rem 1rem', background: 'rgba(34,197,94,0.2)', border: 'none', borderRadius: '8px', color: '#22c55e', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}>✓ 완료</button>
                                            )}
                                            <button onClick={() => handleDeleteStrategy(s.id)} style={{ padding: '0.5rem 1rem', background: 'rgba(239,68,68,0.2)', border: 'none', borderRadius: '8px', color: '#ef4444', fontSize: '0.85rem', fontWeight: '600', cursor: 'pointer' }}>삭제</button>
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', gap: '2rem', color: '#a5b4fc', fontSize: '0.9rem', flexWrap: 'wrap' }}>
                                        <span>📅 {s.start_date?.slice(0, 10)} ~ {s.end_date?.slice(0, 10) || '진행 중'}</span>
                                        {s.initial_assets && <span>💵 시작: {formatKRW(s.initial_assets)}</span>}
                                        {s.target_assets && <span>🎯 목표: {formatKRW(s.target_assets)}</span>}
                                        {s.target_return_pct && <span>📈 목표수익: {s.target_return_pct}%</span>}
                                    </div>
                                    {/* 현재 손익/수익률 표시 */}
                                    {s.initial_assets && latestAsset && s.status === 'ACTIVE' && (() => {
                                        const currentPnl = parseFloat(latestAsset.total_assets) - parseFloat(s.initial_assets);
                                        const currentReturnPct = (currentPnl / parseFloat(s.initial_assets) * 100);
                                        const isProfit = currentPnl >= 0;
                                        return (
                                            <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: isProfit ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', borderRadius: '8px', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                                                <span style={{ color: isProfit ? '#22c55e' : '#ef4444', fontWeight: '600' }}>
                                                    💰 현재 손익: {isProfit ? '+' : ''}{formatKRW(currentPnl)}
                                                </span>
                                                <span style={{ color: isProfit ? '#22c55e' : '#ef4444', fontWeight: '600' }}>
                                                    📊 수익률: {isProfit ? '+' : ''}{currentReturnPct.toFixed(2)}%
                                                </span>
                                                {s.target_assets && (
                                                    <span style={{ color: '#60a5fa', fontWeight: '600', paddingLeft: '1rem', borderLeft: '1px solid rgba(255,255,255,0.1)' }}>
                                                        🏃 남은 목표: {(() => {
                                                            const remain = parseFloat(s.target_assets) - parseFloat(latestAsset.total_assets);
                                                            return remain <= 0 ? '🎉 달성!' : formatKRW(remain);
                                                        })()}
                                                    </span>
                                                )}
                                                <span style={{ color: '#94a3b8', fontSize: '0.8rem', marginLeft: 'auto' }}>
                                                    ({latestAsset.record_date} 기준)
                                                </span>
                                            </div>
                                        );
                                    })()}
                                    {s.description && <div style={{ marginTop: '0.75rem', color: '#c4b5fd', fontSize: '0.85rem' }}>{s.description}</div>}

                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Strategy Edit Modal */}
            {editingStrategy && (
                <div className="dashboard-modal-overlay">
                    <div className="dashboard-modal-content">
                        <div className="dashboard-modal-header">
                            <button onClick={handleCloseEdit} style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.7)', fontSize: '1.5rem', cursor: 'pointer', padding: '0.5rem', lineHeight: 1 }}>×</button>

                            <h2 style={{ color: 'white', margin: 0, fontSize: '1.5rem' }}>✏️ 전략 수정</h2>
                        </div>
                        <form onSubmit={handleUpdateStrategy} className="dashboard-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div><label className="dashboard-label">전략명</label><input type="text" className="dashboard-input" value={strategyForm.strategy_name} onChange={e => setStrategyForm({ ...strategyForm, strategy_name: e.target.value })} required /></div>
                            <div className="dashboard-form-row">
                                <div className="dashboard-form-group"><label className="dashboard-label">시작일</label><input type="date" className="dashboard-input" value={strategyForm.start_date} onChange={e => setStrategyForm({ ...strategyForm, start_date: e.target.value })} required /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">종료일</label><input type="date" className="dashboard-input" value={strategyForm.end_date} onChange={e => setStrategyForm({ ...strategyForm, end_date: e.target.value })} /></div>
                            </div>
                            <div className="dashboard-form-row">
                                <div className="dashboard-form-group"><label className="dashboard-label">시작 자산 (원)</label><input type="number" step="1" className="dashboard-input" value={strategyForm.initial_assets} onChange={e => setStrategyForm({ ...strategyForm, initial_assets: e.target.value })} /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 자산 (원)</label><input type="number" step="1" className="dashboard-input" value={strategyForm.target_assets} onChange={e => setStrategyForm({ ...strategyForm, target_assets: e.target.value })} /></div>
                                <div className="dashboard-form-group"><label className="dashboard-label">목표 수익률 (%) <span style={{ fontSize: '0.7rem', color: '#a78bfa' }}>자동계산</span></label><input type="number" step="0.01" className="dashboard-input" value={strategyForm.target_return_pct} readOnly style={{ background: 'rgba(255,255,255,0.1)', cursor: 'default' }} /></div>
                            </div>

                            <div><label className="dashboard-label">설명</label><textarea className="dashboard-input" value={strategyForm.description} onChange={e => setStrategyForm({ ...strategyForm, description: e.target.value })} rows={3} style={{ resize: 'vertical' }} /></div>
                            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                                <button type="button" onClick={handleCloseEdit} style={{ padding: '0.75rem 1.5rem', background: 'rgba(100,116,139,0.3)', border: 'none', borderRadius: '8px', color: '#94a3b8', cursor: 'pointer' }}>취소</button>
                                <button type="submit" className="dashboard-btn-primary">저장</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Strategy Analysis Modal */}
            {selectedStrategy && (
                <div className="dashboard-modal-overlay">
                    <div className="dashboard-modal-content" style={{ maxWidth: '900px' }}>
                        {/* Modal Header */}
                        <div className="dashboard-modal-header" style={{ background: 'linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%)' }}>
                            <button onClick={handleCloseAnalysis} style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.7)', fontSize: '1.5rem', cursor: 'pointer', padding: '0.5rem', lineHeight: 1 }}>×</button>

                            <h2 style={{ color: 'white', margin: 0, fontSize: '1.5rem' }}>📊 전략 분석: {selectedStrategy.strategy_name}</h2>
                            <div style={{ color: 'rgba(255,255,255,0.7)', marginTop: '0.5rem' }}>
                                {selectedStrategy.start_date?.slice(0, 10)} ~ {selectedStrategy.end_date?.slice(0, 10) || '진행 중'}
                            </div>
                        </div>

                        {/* Modal Body */}
                        <div className="dashboard-modal-body">
                            {loadingPerformance ? (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#a5b4fc' }}>분석 데이터 로딩 중...</div>
                            ) : strategyPerformance ? (
                                <>
                                    {/* Performance Summary Cards */}
                                    <div className="dashboard-performance-grid">
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>총 매매</div>
                                            <div style={{ fontSize: '1.8rem', fontWeight: '700', color: 'white' }}>{strategyPerformance.total_trades || 0}건</div>
                                        </div>
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>승률</div>
                                            <div style={{ fontSize: '1.8rem', fontWeight: '700', color: (strategyPerformance.win_rate || 0) >= 50 ? '#22c55e' : '#ef4444' }}>{strategyPerformance.win_rate || 0}%</div>
                                            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{strategyPerformance.wins || 0}승 {strategyPerformance.losses || 0}패</div>
                                        </div>
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>총 손익</div>
                                            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: (strategyPerformance.total_pnl || 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                                                {(strategyPerformance.total_pnl || 0) >= 0 ? '+' : ''}{formatKRW(strategyPerformance.total_pnl || 0)}
                                            </div>
                                        </div>
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>기간 수익률</div>
                                            <div style={{ fontSize: '1.8rem', fontWeight: '700', color: (strategyPerformance.total_return_pct || 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                                                {(strategyPerformance.total_return_pct || 0) >= 0 ? '+' : ''}{strategyPerformance.total_return_pct || 0}%
                                            </div>
                                        </div>
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>평균 손익률</div>
                                            <div style={{ fontSize: '1.8rem', fontWeight: '700', color: (strategyPerformance.avg_pnl_pct || 0) >= 0 ? '#22c55e' : '#ef4444' }}>
                                                {(strategyPerformance.avg_pnl_pct || 0) >= 0 ? '+' : ''}{strategyPerformance.avg_pnl_pct || 0}%
                                            </div>
                                        </div>
                                        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1.25rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '0.8rem', color: '#a5b4fc', marginBottom: '0.5rem' }}>평균 보유</div>
                                            <div style={{ fontSize: '1.8rem', fontWeight: '700', color: 'white' }}>{strategyPerformance.avg_hold_days || 0}일</div>
                                        </div>
                                    </div>

                                    {/* Win/Loss Pie Chart */}
                                    {strategyPerformance.total_trades > 0 && (
                                        <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
                                            <div style={{ flex: 1, minWidth: '250px', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', padding: '1.5rem' }}>
                                                <h4 style={{ color: 'white', marginBottom: '1rem', fontSize: '1rem' }}>승패 비율</h4>
                                                <ResponsiveContainer width="100%" height={200}>
                                                    <PieChart>
                                                        <Pie data={getPieData()} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={5} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                                                            {getPieData().map((entry, index) => (
                                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                                            ))}
                                                        </Pie>
                                                        <Tooltip />
                                                    </PieChart>
                                                </ResponsiveContainer>
                                            </div>

                                            <div style={{ flex: 1, minWidth: '250px', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', padding: '1.5rem' }}>
                                                <h4 style={{ color: 'white', marginBottom: '1rem', fontSize: '1rem' }}>자산 변동</h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(59,130,246,0.1)', borderRadius: '8px' }}>
                                                        <span style={{ color: '#94a3b8' }}>시작 자산</span>
                                                        <span style={{ color: 'white', fontWeight: '600' }}>{formatKRW(strategyPerformance.start_assets)}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(59,130,246,0.1)', borderRadius: '8px' }}>
                                                        <span style={{ color: '#94a3b8' }}>현재/종료 자산</span>
                                                        <span style={{ color: 'white', fontWeight: '600' }}>{formatKRW(strategyPerformance.end_assets)}</span>
                                                    </div>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: (strategyPerformance.total_return_pct || 0) >= 0 ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', borderRadius: '8px' }}>
                                                        <span style={{ color: '#94a3b8' }}>순 변동</span>
                                                        <span style={{ color: (strategyPerformance.total_return_pct || 0) >= 0 ? '#22c55e' : '#ef4444', fontWeight: '600' }}>
                                                            {strategyPerformance.start_assets && strategyPerformance.end_assets
                                                                ? `${(strategyPerformance.end_assets - strategyPerformance.start_assets) >= 0 ? '+' : ''}${formatKRW(strategyPerformance.end_assets - strategyPerformance.start_assets)}`
                                                                : '-'}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Strategy Evaluation */}
                                    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '16px', padding: '1.5rem' }}>
                                        <h4 style={{ color: 'white', marginBottom: '1rem', fontSize: '1rem' }}>📋 전략 평가</h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                            {strategyPerformance.win_rate >= 60 && (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#22c55e' }}>
                                                    <span>✅</span> <span>우수한 승률 ({strategyPerformance.win_rate}%)을 유지하고 있습니다.</span>
                                                </div>
                                            )}
                                            {strategyPerformance.win_rate < 50 && strategyPerformance.total_trades > 3 && (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f59e0b' }}>
                                                    <span>⚠️</span> <span>승률이 50% 미만입니다. 진입 조건을 재검토해 보세요.</span>
                                                </div>
                                            )}
                                            {strategyPerformance.avg_hold_days > 5 && (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a5b4fc' }}>
                                                    <span>ℹ️</span> <span>평균 보유 기간이 {strategyPerformance.avg_hold_days}일입니다. 단기 전략이라면 익/손절 타이밍을 조정해 보세요.</span>
                                                </div>
                                            )}
                                            {strategyPerformance.total_return_pct > 0 && (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#22c55e' }}>
                                                    <span>✅</span> <span>기간 내 양의 수익률을 달성했습니다. (+{strategyPerformance.total_return_pct}%)</span>
                                                </div>
                                            )}
                                            {strategyPerformance.total_trades === 0 && (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8' }}>
                                                    <span>ℹ️</span> <span>아직 청산된 거래가 없습니다. 매매일지에서 거래를 기록해 주세요.</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>분석 데이터를 불러올 수 없습니다.</div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AssetDashboardPage;
