import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import StockCard from './components/StockCard';
import SummaryTable from './components/SummaryTable';
import FinalSignal from './components/FinalSignal';
import MarketStats from './components/MarketStats';
import MarketInsight from './components/MarketInsight';
import JournalPage from './JournalPage';
import SignalPage from './SignalPage';
import './index.css';
import packageJson from '../package.json'; // Version Import

function Dashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000); // 1 min refresh
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const response = await fetch('/api/report');
            if (!response.ok) throw new Error('Failed to fetch data');
            const jsonData = await response.json();
            setData(jsonData);
            setLoading(false);
        } catch (err) {
            console.error(err);
            setError(err.message);
            setLoading(false);
        }
    };

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column' }}>
            <div className="animate-pulse-slow" style={{ fontSize: '2rem', fontWeight: 700 }}>청안 시스템 가동 중...</div>
            <div style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>데이터를 수집하고 분석하고 있습니다.</div>
        </div>
    );

    if (error) return (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--accent-red)' }}>
            <h2>시스템 오류 발생</h2>
            <p>{error}</p>
            <button onClick={fetchData} style={{ padding: '0.5rem 1rem', background: 'var(--bg-secondary)', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>재시도</button>
        </div>
    );

    return (
        <div>
            <header>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.9rem', color: 'var(--accent-blue)', fontWeight: 600, letterSpacing: '1px' }}>
                        PREMIUM FINANCIAL REPORT
                    </div>
                </div>
                <h1>청안 해외주식 멀티 종목 종합 분석</h1>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', color: 'var(--text-secondary)' }}>
                    <p style={{ margin: 0 }}>분석 시점: {data?.timestamp?.full_str}</p>
                </div>
            </header>

            {data?.market && <MarketStats market={data.market} />}

            {data?.stocks && <FinalSignal stocks={data.stocks} />}

            <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem', marginTop: '3rem' }}>종목별 상세 분석</h2>
            <div className="grid-cards">
                {data?.stocks?.map(stock => (
                    <StockCard key={stock.ticker} data={stock} />
                ))}
            </div>

            {data?.stocks && <SummaryTable stocks={data.stocks} />}

            {data?.market && <MarketInsight market={{ ...data.market, insight: data.insight }} />}

            <footer style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-secondary)', fontSize: '0.8rem', paddingBottom: '2rem' }}>
                © 2024 Cheong-An Financial Intelligence. All rights reserved. v{packageJson.version}
            </footer>
        </div>
    );
}

function NavBar() {
    const location = useLocation();

    const linkStyle = (path) => ({
        padding: '0.8rem 1.5rem',
        textDecoration: 'none',
        color: location.pathname === path ? 'white' : 'var(--text-secondary)',
        fontWeight: location.pathname === path ? 'bold' : 'normal',
        borderBottom: location.pathname === path ? '2px solid var(--accent-blue)' : '2px solid transparent',
        transition: 'all 0.3s',
        whiteSpace: 'nowrap'
    });

    return (
        <nav style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem 0',
            marginBottom: '2rem',
            borderBottom: '1px solid var(--glass-border)',
            flexWrap: 'wrap',
            gap: '1rem'
        }}>
            <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto' }}>
                <Link to="/" style={linkStyle('/')}>대시보드</Link>
                <Link to="/signals" style={linkStyle('/signals')}>신호 포착</Link>
                <Link to="/journal" style={linkStyle('/journal')}>매매 일지</Link>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.5rem' }}>
                Ver {packageJson.version}
            </div>
        </nav>
    );
}

function App() {
    return (
        <Router>
            <div className="container">
                <NavBar />
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/signals" element={<SignalPage />} />
                    <Route path="/journal" element={<JournalPage />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
