import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import FinalSignal from './components/FinalSignal';
import MarketStats from './components/MarketStats';
import MarketInsight from './components/MarketInsight';
import JournalPage from './JournalPage';
import SignalPage from './SignalPage';
import ManagedStocksPage from './ManagedStocksPage';
import BacktestPage from './BacktestPage';
import './index.css';
import packageJson from '../package.json'; // Version Import

function Dashboard() {
    const [data, setData] = useState(null);
    const [signalHistory, setSignalHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); // 10 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const response = await fetch('/api/report');
            if (!response.ok) throw new Error('Failed to fetch data');
            const jsonData = await response.json();

            // Fetch Signal History
            const historyRes = await fetch('/api/signals?limit=5');
            let historyData = [];
            if (historyRes.ok) historyData = await historyRes.json();

            if (jsonData.error) {
                setError(jsonData.error);
            } else {
                setData(jsonData);
                setSignalHistory(historyData);
            }
            setLoading(false);
        } catch (err) {
            console.error(err);
            setError(err.message);
            setLoading(false);
        }
    };

    const toggleTickerVisibility = async (ticker, isVisible) => {
        try {
            await fetch('/api/dashboard-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, is_visible: isVisible })
            });
            setData(prev => {
                if (!prev) return prev;
                return {
                    ...prev,
                    stocks: prev.stocks.map(s => s.ticker === ticker ? { ...s, is_visible: isVisible } : s)
                };
            });
        } catch (err) {
            console.error("Failed to update ticker visibility:", err);
        }
    };

    if (loading && !data) return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh', flexDirection: 'column' }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '2rem', background: 'linear-gradient(to right, #60a5fa, #34d399)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                CHEONGAN SYSTEM
            </div>
            <div style={{ width: '320px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '10px', overflow: 'hidden', position: 'relative' }}>
                <div style={{
                    position: 'absolute', top: 0, left: 0, height: '100%', width: '100px',
                    background: 'linear-gradient(90deg, transparent, #60a5fa, #34d399, transparent)',
                    animation: 'loading-slide 1.5s infinite linear'
                }} />
            </div>
            <div style={{ color: 'var(--text-secondary)', marginTop: '1.5rem', fontSize: '1rem', letterSpacing: '2px', fontWeight: 600 }}>
                청안 해외주식 분석 시스템 가동 중...
            </div>
            <style>{`
                @keyframes loading-slide {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(320px); }
                }
            `}</style>
        </div>
    );

    if (error) return (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--accent-red)' }}>
            <h2>시스템 오류 발생</h2>
            <p>{error}</p>
            <button onClick={fetchData} style={{ padding: '0.5rem 1rem', background: 'var(--bg-secondary)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>재시도</button>
        </div>
    );

    // Sorting Logic: Buy Group -> Sell Group -> Others -> Score DESC
    const sortedStocks = data?.stocks ? [...data.stocks].sort((a, b) => {
        const getGroup = (stock) => {
            const pos = stock.position || '';
            if (pos.includes('매수')) return 1;
            if (pos.includes('매도')) return 2;
            return 3;
        };
        const groupA = getGroup(a);
        const groupB = getGroup(b);
        if (groupA !== groupB) return groupA - groupB;
        return (b.score || 0) - (a.score || 0);
    }) : [];

    const visibleStocks = sortedStocks.filter(s => s.is_visible !== false);

    return (
        <div className="container">
            <header>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '2.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '4px', height: '24px', background: 'var(--accent-blue)', borderRadius: '2px' }}></div>
                        <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 700, letterSpacing: '-0.5px', background: 'linear-gradient(135deg, #fff 0%, #a5b4fc 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                            청안 해외주식 종합 분석
                        </h1>
                    </div>
                    {data?.timestamp?.full_str && (
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            {/* Sync Button */}
                            <button
                                onClick={async () => {
                                    if (confirm("최근 30일 데이터를 다시 가져와 DB를 갱신하시겠습니까? (약 10초 소요)")) {
                                        try {
                                            const res = await fetch('/api/system/backfill', { method: 'POST' });
                                            const data = await res.json();
                                            alert(data.message);
                                        } catch (e) {
                                            alert("동기화 요청 실패: " + e.message);
                                        }
                                    }
                                }}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: '6px',
                                    padding: '0.4rem 0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.2)',
                                    borderRadius: '8px', color: '#e2e8f0', cursor: 'pointer', fontSize: '0.8rem'
                                }}
                                title="데이터 전체 동기화 (30일)"
                            >
                                <span style={{ fontSize: '1rem' }}>🔄</span> 동기화
                            </button>

                            {/* Market Regime Badge (UPRO Status) */}
                            {data.market_regime && (
                                <div style={{
                                    padding: '0.4rem 0.8rem',
                                    borderRadius: '8px',
                                    fontSize: '0.85rem',
                                    fontWeight: 700,
                                    background: data.market_regime.regime === 'Bull' ? 'rgba(34, 197, 94, 0.15)' :
                                        data.market_regime.regime === 'Bear' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                                    color: data.market_regime.regime === 'Bull' ? '#4ade80' :
                                        data.market_regime.regime === 'Bear' ? '#f87171' : '#cbd5e1',
                                    border: '1px solid rgba(255,255,255,0.1)'
                                }}>
                                    {data.market_regime.reason || '시장 분석 중'}
                                </div>
                            )}

                            <div style={{
                                background: 'rgba(255, 255, 255, 0.03)',
                                padding: '0.5rem 1rem',
                                borderRadius: '12px',
                                display: 'flex', alignItems: 'center', gap: '8px',
                                border: '1px solid rgba(255,255,255,0.05)'
                            }}>
                                <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Last Analysis:</span>
                                <span style={{ fontSize: '0.9rem', fontWeight: 500, color: '#e2e8f0' }}>
                                    {data.market_regime?.soxl?.data_time ? `${data.market_regime.soxl.data_time} (Data)` : data.timestamp.full_str}
                                </span>
                            </div>
                        </div>
                    )}
                </div>


            </header>

            {data?.market && <MarketStats market={data.market} />}


            {data && <MarketInsight market={data} stocks={visibleStocks} signalHistory={signalHistory} />}

            {data?.stocks && <FinalSignal stocks={visibleStocks} total_assets={data.total_assets} />}
        </div>
    );
}

import RequestPage from './RequestPage';
import LoginPage from './LoginPage';

function Layout() {
    const location = useLocation();
    const navigate = useNavigate();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Check authentication and Protect Routes
    useEffect(() => {
        const checkAuth = () => {
            const auth = localStorage.getItem('isAuthenticated') === 'true';
            setIsAuthenticated(auth);

            // 미인증 상태에서 로그인 페이지가 아닌 곳에 접근 시 로그인 페이지로 이동
            if (!auth && location.pathname !== '/login') {
                navigate('/login');
            }
        };

        checkAuth();
        window.addEventListener('storage', checkAuth);

        return () => {
            window.removeEventListener('storage', checkAuth);
        };
    }, [location, navigate]); // 라우트 변경 시마다 체크

    const handleLogout = () => {
        localStorage.removeItem('isAuthenticated');
        localStorage.removeItem('authToken');
        localStorage.removeItem('userName');
        setIsAuthenticated(false);
        navigate('/login');
    };

    // Close menu when route changes
    useEffect(() => {
        setIsMenuOpen(false);
    }, [location]);

    return (
        <div className="app-container">
            <button
                className="mobile-menu-btn"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                aria-label="Toggle Menu"
            >
                {isMenuOpen ? '✕' : '☰'}
            </button>
            <nav className={`main-nav ${isMenuOpen ? 'active' : ''}`}>
                <Link to="/" className="nav-link" style={{
                    color: location.pathname === '/' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/' ? 'bold' : 'normal',
                }}>대시보드</Link>
                <Link to="/signals" className="nav-link" style={{
                    color: location.pathname === '/signals' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/signals' ? 'bold' : 'normal',
                }}>신호 포착</Link>
                <Link to="/journal" className="nav-link" style={{
                    color: location.pathname === '/journal' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/journal' ? 'bold' : 'normal',
                }}>매매 일지</Link>
                <Link to="/managed-stocks" className="nav-link" style={{
                    color: location.pathname === '/managed-stocks' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/managed-stocks' ? 'bold' : 'normal',
                }}>거래 종목</Link>
                <Link to="/backtest" className="nav-link" style={{
                    color: location.pathname === '/backtest' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/backtest' ? 'bold' : 'normal',
                }}>백테스트</Link>
                <Link to="/requests" className="nav-link" style={{
                    color: location.pathname === '/requests' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/requests' ? 'bold' : 'normal',
                }}>요청사항</Link>

                {isAuthenticated ? (
                    <button
                        onClick={handleLogout}
                        className="nav-link"
                        style={{
                            background: 'rgba(255, 99, 71, 0.1)',
                            border: '1px solid rgba(255, 99, 71, 0.2)',
                            cursor: 'pointer',
                            color: '#ff6347',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            marginLeft: '10px'
                        }}
                    >
                        로그아웃
                    </button>
                ) : (
                    <Link to="/login" className="nav-link" style={{
                        color: location.pathname === '/login' ? 'var(--accent-blue)' : 'var(--text-primary)',
                        fontWeight: location.pathname === '/login' ? 'bold' : 'normal',
                        background: 'rgba(99, 102, 241, 0.1)',
                        padding: '0.5rem 1rem',
                        borderRadius: '6px',
                        border: '1px solid rgba(99, 102, 241, 0.2)',
                        marginLeft: '10px'
                    }}>로그인</Link>
                )}
            </nav>

            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/signals" element={<SignalPage />} />
                <Route path="/journal" element={<JournalPage />} />
                <Route path="/managed-stocks" element={<ManagedStocksPage />} />
                <Route path="/backtest" element={<BacktestPage />} />
                <Route path="/requests" element={<RequestPage />} />
                <Route path="/login" element={<LoginPage />} />
            </Routes>


            <footer style={{
                textAlign: 'center', padding: '2rem', marginTop: '4rem',
                borderTop: '1px solid var(--glass-border)', color: 'var(--text-secondary)'
            }}>
                <p>&copy; 2026 Cheongan FinTech. All rights reserved. Ver {packageJson.version} (Updated: {import.meta.env.VITE_BUILD_TIME || 'Local'}) (Holding Score System)</p>
            </footer>
        </div>
    );
}

function App() {
    return (
        <Router>
            <Layout />
        </Router>
    );
}

export default App;
