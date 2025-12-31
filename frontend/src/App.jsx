import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import StockCard from './components/StockCard';
import SummaryTable from './components/SummaryTable';
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
            if (jsonData.error) {
                setError(jsonData.error);
            } else {
                setData(jsonData);
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

    if (loading) return (
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
                            {/* Market Regime Badge */}
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
                                    {data.market_regime.regime === 'Bull' ? '🚀 상승장 (Bull)' :
                                        data.market_regime.regime === 'Bear' ? '📉 하락장 (Bear)' : '🦀 보합장 (Sideways)'}
                                </div>
                            )}

                            <div style={{
                                background: 'rgba(255, 255, 255, 0.03)',
                                padding: '0.5rem 1rem',
                                borderRadius: '12px',
                                border: '1px solid rgba(255, 255, 255, 0.08)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                fontSize: '0.8rem',
                                color: 'var(--text-secondary)',
                            }}>
                                <span style={{ display: 'inline-block', width: '6px', height: '6px', background: '#10b981', borderRadius: '50%', boxShadow: '0 0 8px #10b981' }}></span>
                                <strong>분석:</strong> {data.timestamp.full_str.split('KST')[0]}
                            </div>
                        </div>
                    )}
                </div>


            </header>

            {data?.market && <MarketStats market={data.market} />}

            {data?.stocks && <FinalSignal stocks={visibleStocks} />}

            {data && <MarketInsight market={data} />}

            <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem', marginTop: '3rem' }}>종목별 상세 분석</h2>
            <div className="grid-cards">
                {visibleStocks.map(stock => (
                    <StockCard key={stock.ticker} data={stock} />
                ))}
            </div>

            {data?.stocks && <SummaryTable stocks={sortedStocks} onToggleVisibility={toggleTickerVisibility} />}
        </div>
    );
}

function Layout() {
    const location = useLocation();
    const [isMenuOpen, setIsMenuOpen] = useState(false);

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
            </nav>

            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/signals" element={<SignalPage />} />
                <Route path="/journal" element={<JournalPage />} />
                <Route path="/managed-stocks" element={<ManagedStocksPage />} />
                <Route path="/backtest" element={<BacktestPage />} />
            </Routes>


            <footer style={{
                textAlign: 'center', padding: '2rem', marginTop: '4rem',
                borderTop: '1px solid var(--glass-border)', color: 'var(--text-secondary)'
            }}>
                <p>&copy; 2024 Cheongan FinTech. All rights reserved. Ver {packageJson.version}</p>
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
