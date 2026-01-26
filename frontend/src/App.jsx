import React, { useEffect, useState, useRef } from 'react';
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
import CryptoPage from './CryptoPage';
import DailyReportPage from './DailyReportPage';
import LabPage from './LabPage';
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


// ═══════════════════════════════════════════════════════════════════
// [Dashboard Component]
// ═══════════════════════════════════════════════════════════════════
function Dashboard({ isMuted, toggleMute }) {
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

    // [Ver 5.7.4] Sequential Sound Queue with 30s Throttle
    const [lastPlayedMap, setLastPlayedMap] = useState({});
    const soundQueueRef = React.useRef([]);
    const isPlayingRef = React.useRef(false);

    const processQueue = () => {
        if (isPlayingRef.current || soundQueueRef.current.length === 0) return;

        // Mute Check
        if (isMuted) {
            console.log("🔇 Dashboard Sound Muted. Skipping queue.");
            soundQueueRef.current = []; // Clear queue
            return;
        }

        const nextSound = soundQueueRef.current.shift(); // Dequeue
        isPlayingRef.current = true;

        console.log(`🔊 Playing Sequence: ${nextSound}.mp3`);
        const audio = new Audio(`/sounds/${nextSound}.mp3`);

        audio.onended = () => {
            isPlayingRef.current = false;
            processQueue(); // Play next
        };

        audio.onerror = (e) => {
            console.warn(`Sound Error (${nextSound}):`, e);
            isPlayingRef.current = false;
            processQueue(); // Skip to next
        };

        audio.play().catch(e => {
            console.warn("Play interrupted/failed:", e);
            isPlayingRef.current = false;
            processQueue();
        });
    };

    useEffect(() => {
        if (data?.sounds && data.sounds.length > 0) {
            const now = Date.now();
            const newPlayedMap = { ...lastPlayedMap };
            let hasUpdate = false;

            data.sounds.forEach(soundCode => {
                // Check throttle (30 seconds)
                const lastTime = newPlayedMap[soundCode] || 0;

                // Only enqueue if NOT throttled
                if (now - lastTime > 30000) {
                    // Also check if already in queue to prevent burst duplicates
                    if (!soundQueueRef.current.includes(soundCode)) {
                        soundQueueRef.current.push(soundCode);
                        newPlayedMap[soundCode] = now;
                        hasUpdate = true;
                        console.log(`➕ Enqueued: ${soundCode}`);
                    }
                } else {
                    // console.log(`🔇 Throttled: ${soundCode}`);
                }
            });

            if (hasUpdate) {
                setLastPlayedMap(newPlayedMap);
                processQueue(); // Trigger processing
            }
        }
    }, [data?.sounds]); // Only run when sounds array changes

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

    const fetchData = async (retryCount = 0) => {
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

                // 성공 시 에러 초기화
                setError(null);
            }
            setLoading(false);
        } catch (err) {
            console.error(`Fetch Error (Retry ${retryCount}/5):`, err);

            if (retryCount < 5) {
                // 재시도 (Exponential Backoff 없음, 단순 1초 대기)
                setTimeout(() => {
                    fetchData(retryCount + 1);
                }, 1000);
            } else {
                setError(err.message + " (서버 연결 실패 - 잠시 후 다시 시도해주세요)");
                setLoading(false);
            }
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
            {/* Header removed for space optimization */}

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
                isMuted={isMuted}
                toggleMute={toggleMute}
            />}

            {data?.stocks && <FinalSignal stocks={visibleStocks} total_assets={data.total_assets} />}
        </div>
    );
}

import RequestPage from './RequestPage';
import LoginPage from './LoginPage';

// ═══════════════════════════════════════════════════════════════════
// [Ver 5.9.1] GlobalAlertSounds - 전역 알림 사운드 (모든 페이지에서 동작)
// ═══════════════════════════════════════════════════════════════════
const GlobalAlertSounds = ({ isMuted }) => {
    const prevTriggeredRef = useRef(new Set());  // 이전 트리거 상태
    const lastPlayedRef = useRef({});  // 쓰로틀링용
    const isPlayingRef = useRef(false);
    const queueRef = useRef([]);

    // 순차 재생 처리
    const processQueue = () => {
        if (isPlayingRef.current || queueRef.current.length === 0) return;

        // Mute Check
        if (isMuted) {
            console.log("🔇 GlobalAlertSounds Muted. Skipping queue.");
            queueRef.current = []; // Clear queue or just skip? Clear is safer to avoid accumulation.
            return;
        }

        const sound = queueRef.current.shift();
        isPlayingRef.current = true;

        const audio = new Audio(`/sounds/${sound}.mp3`);
        audio.onended = () => { isPlayingRef.current = false; processQueue(); };
        audio.onerror = () => { isPlayingRef.current = false; processQueue(); };
        audio.play().catch(() => { isPlayingRef.current = false; processQueue(); });

        console.log(`🔔 GlobalAlert Sound: ${sound}`);
    };

    // Re-process queue if unmuted (optional, but good UX)
    useEffect(() => {
        if (!isMuted) processQueue();
    }, [isMuted]);

    useEffect(() => {
        const checkAlerts = async () => {
            try {
                const [soxlRes, soxsRes] = await Promise.all([
                    fetch('/api/v2/alerts/SOXL').then(r => r.json()),
                    fetch('/api/v2/alerts/SOXS').then(r => r.json())
                ]);

                const allLevels = [
                    ...(soxlRes.data || []).map(l => ({ ...l, ticker: 'SOXL' })),
                    ...(soxsRes.data || []).map(l => ({ ...l, ticker: 'SOXS' }))
                ];

                const currentTriggered = new Set();
                const now = Date.now();

                allLevels.forEach(lvl => {
                    if (lvl.triggered === 'Y' && lvl.is_active === 'Y') {
                        const key = `${lvl.ticker}-${lvl.level_type}-${lvl.stage}`;
                        currentTriggered.add(key);

                        // 새로 트리거된 경우에만 사운드
                        if (!prevTriggeredRef.current.has(key)) {
                            // 쓰로틀링 (30초)
                            const lastPlayed = lastPlayedRef.current[key] || 0;
                            if (now - lastPlayed > 30000) {
                                // 사운드 코드: LB1, LS2, SB3 등
                                const tickerCode = lvl.ticker === 'SOXL' ? 'L' : 'S';
                                const typeCode = lvl.level_type === 'BUY' ? 'B' : 'S';
                                const soundCode = `${tickerCode}${typeCode}${lvl.stage}`;

                                queueRef.current.push(soundCode);
                                lastPlayedRef.current[key] = now;
                            }
                        }
                    }
                });

                prevTriggeredRef.current = currentTriggered;
                processQueue();
            } catch (e) {
                // Silent fail
            }
        };

        checkAlerts();
        const interval = setInterval(checkAlerts, 5000);
        return () => clearInterval(interval);
    }, []);

    return null;  // UI 없음
};

function Layout() {
    const location = useLocation();
    const navigate = useNavigate();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // [Sound Control]
    const [isMuted, setIsMuted] = useState(() => {
        return localStorage.getItem('isMuted') === 'true';
    });

    const toggleMute = () => {
        setIsMuted(prev => {
            const next = !prev;
            localStorage.setItem('isMuted', next);
            return next;
        });
    };

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
            {/* 전역 알림 사운드 (항상 실행) */}
            <GlobalAlertSounds isMuted={isMuted} />

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
                <Link to="/crypto" className="nav-link" style={{
                    color: location.pathname === '/crypto' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/crypto' ? 'bold' : 'normal',
                }}>가상자산</Link>
                <Link to="/daily-reports" className="nav-link" style={{
                    color: location.pathname === '/daily-reports' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/daily-reports' ? 'bold' : 'normal',
                }}>Daily Reports</Link>
                <Link to="/journal" className="nav-link" style={{
                    color: location.pathname === '/journal' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/journal' ? 'bold' : 'normal',
                }}>자산 관리</Link>
                <Link to="/asset-dashboard" className="nav-link" style={{
                    color: location.pathname === '/asset-dashboard' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/asset-dashboard' ? 'bold' : 'normal',
                }}>목표관리</Link>
                <Link to="/signals" className="nav-link" style={{
                    color: location.pathname === '/signals' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/signals' ? 'bold' : 'normal',
                }}>신호 포착</Link>
                <Link to="/trading-journal" className="nav-link" style={{
                    color: location.pathname === '/trading-journal' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/trading-journal' ? 'bold' : 'normal',
                }}>매매일지</Link>
                <Link to="/lab" className="nav-link" style={{
                    color: location.pathname === '/lab' ? 'var(--accent-blue)' : 'var(--text-primary)',
                    fontWeight: location.pathname === '/lab' ? 'bold' : 'normal',
                }}>🧪 실험실</Link>


                {isAuthenticated ? (
                    <button
                        onClick={handleLogout}
                        className="nav-link"
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            color: '#94a3b8',
                            padding: '0.5rem 1rem',
                            fontSize: '0.9rem',
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
                <Route path="/" element={<Dashboard isMuted={isMuted} toggleMute={toggleMute} />} />
                <Route path="/crypto" element={<CryptoPage />} />
                <Route path="/signals" element={<SignalPage />} />
                <Route path="/journal" element={<JournalPage />} />
                <Route path="/trading-journal" element={<TradingJournalPage />} />
                <Route path="/managed-stocks" element={<ManagedStocksPage />} />
                <Route path="/backtest" element={<BacktestPage />} />
                <Route path="/requests" element={<RequestPage />} />
                <Route path="/daily-reports" element={<DailyReportPage />} />
                <Route path="/lab" element={<LabPage />} />
                <Route path="/asset-dashboard" element={<AssetDashboardPage />} />
                <Route path="/asset-dashboard" element={<AssetDashboardPage />} />
                <Route path="/login" element={<LoginPage />} />
            </Routes>


            <footer style={{
                textAlign: 'center', padding: '2rem', marginTop: '4rem',
                borderTop: '1px solid var(--glass-border)', color: 'var(--text-secondary)'
            }}>
                <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '0.8rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <p>&copy; 2026 BlueEye AI. All rights reserved. | System Status: <span style={{ color: '#4ade80' }}>Operational</span> | Ver {packageJson.version} (Updated: 2026-01-27 04:35)</p>
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
