import React, { useEffect, useState } from 'react';
import StockCard from './components/StockCard';
import SummaryTable from './components/SummaryTable';
import FinalSignal from './components/FinalSignal';
import MarketStats from './components/MarketStats';
import MarketInsight from './components/MarketInsight';
import './index.css';

function App() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000 * 5); // 5 min refresh
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
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
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
        <div className="container">
            <header>
                <div style={{ fontSize: '0.9rem', color: 'var(--accent-blue)', fontWeight: 600, letterSpacing: '1px' }}>
                    PREMIUM FINANCIAL REPORT
                </div>
                <h1>청안 30분봉 멀티 종목 종합 분석</h1>
                <p>분석 시점: {data?.timestamp?.full_str}</p>
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

            {data?.market && <MarketInsight market={data.market} />}

            <footer style={{ textAlign: 'center', marginTop: '4rem', color: 'var(--text-secondary)', fontSize: '0.8rem', paddingBottom: '2rem' }}>
                © 2024 Cheong-An Financial Intelligence. All rights reserved.
            </footer>
        </div>
    );
}

export default App;
