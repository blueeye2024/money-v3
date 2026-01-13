import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import FinalSignal from './components/FinalSignal';
import MarketStats from './components/MarketStats';
import MarketInsight from './components/MarketInsight';
import JournalPage from './JournalPage';
import TradingJournalPage from './TradingJournalPage';
import SignalPage from './SignalPage';
import ManagedStocksPage from './ManagedStocksPage';
import BacktestPage from './BacktestPage';
import AssetDashboardPage from './AssetDashboardPage';
import './index.css';
import packageJson from '../package.json'; // Version Import

// 시장 상태 판단 함수 (EST 기준)
// 시장 상태 판단 (백엔드와 동일 로직 적용 - Local Fallback)
const getMarketStatus = () => {
    const now = new Date();
    // UTC Time
    const utcHours = now.getUTCHours();
    const utcMinutes = now.getUTCMinutes();
    const utcTime = utcHours * 60 + utcMinutes;
    const day = now.getUTCDay(); // 0=Sun, 6=Sat

    // 1. Weekend Check (Sat 05:00 UTC ~ Mon 04:00 UTC approx?)
    // Simple: Sat/Sun based on US Time (UTC-5/4)
    // Let's stick to the prompt: Just distinguish phases.
    // If backend provides it, use it. This is just initial state.
    // Safe fallback: 'closed'
    return 'closed';
};


function Dashboard() {
    const [data, setData] = useState(null);
    const [signalHistory, setSignalHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdateTime, setLastUpdateTime] = useState(null);

    // 폴링 모드: 'auto' | 'on' | 'off'
    const [pollingMode, setPollingMode] = useState(() => {
        return localStorage.getItem('pollingMode') || 'auto';
    });

    // 시장 상태
    const [marketStatus, setMarketStatus] = useState(getMarketStatus());

    // 시장 상태 1분마다 갱신
    useEffect(() => {
        const statusInterval = setInterval(() => {
            setMarketStatus(getMarketStatus());
        }, 60000);
        return () => clearInterval(statusInterval);
    }, []);

    // 폴링 모드 저장
    useEffect(() => {
        localStorage.setItem('pollingMode', pollingMode);
    }, [pollingMode]);

    // 폴링 활성화 여부 결정
    const shouldPoll = () => {
        if (pollingMode === 'on') return true;
        if (pollingMode === 'off') return false;
        // auto 모드: 장중 또는 장외일 때만 폴링
        return marketStatus === 'open' || marketStatus === 'pre-after';
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(() => {
            if (shouldPoll()) {
                fetchData();
            }
        }, 10000); // 10 seconds
        return () => clearInterval(interval);
    }, [pollingMode, marketStatus]);

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
                // 최근 업데이트 시간 설정 (HH:mm 형식)
                setLastUpdateTime(new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false }));

                // [Optimized] Use Backend Market Status
                if (jsonData.market_status) {
                    setMarketStatus(jsonData.market_status.toLowerCase());
                }
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
                    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
                        {/* 상태 정보는 MarketInsight로 이동됨 */}
                    </div>
                </div>


            </header>

            {data?.market && <MarketStats market={data.market} />}


            {data && <MarketInsight
                market={data}
                stocks={visibleStocks}
                signalHistory={signalHistory}
                onRefresh={fetchData}
                pollingMode={pollingMode}
                setPollingMode={setPollingMode}
                marketStatus={marketStatus}
                lastUpdateTime={lastUpdateTime}
            />}

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
                <Link to="/trading-journal" className="nav-link" style={{
                    color: location.pathname === '/trading-journal' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/trading-journal' ? 'bold' : 'normal',
                }}>매매일지</Link>
                <Link to="/signals" className="nav-link" style={{
                    color: location.pathname === '/signals' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/signals' ? 'bold' : 'normal',
                }}>신호 포착</Link>
                <Link to="/journal" className="nav-link" style={{
                    color: location.pathname === '/journal' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/journal' ? 'bold' : 'normal',
                }}>자산 관리</Link>
                <Link to="/asset-dashboard" className="nav-link" style={{
                    color: location.pathname === '/asset-dashboard' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/asset-dashboard' ? 'bold' : 'normal',
                }}>💰 자산현황</Link>
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
                <Route path="/trading-journal" element={<TradingJournalPage />} />
                <Route path="/managed-stocks" element={<ManagedStocksPage />} />
                <Route path="/backtest" element={<BacktestPage />} />
                <Route path="/requests" element={<RequestPage />} />
                <Route path="/asset-dashboard" element={<AssetDashboardPage />} />
                <Route path="/login" element={<LoginPage />} />
            </Routes>


            <footer style={{
                textAlign: 'center', padding: '2rem', marginTop: '4rem',
                borderTop: '1px solid var(--glass-border)', color: 'var(--text-secondary)'
            }}>
                <div className="footer-copyright">
                    <p>© 2026 Cheongan Fintech. All rights reserved.</p>
                    <p className="version-info">Ver 5.3.1 (Updated: 2026-01-14 04:15)</p>
                </div>
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
