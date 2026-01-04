import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Mail, ShieldCheck, Activity, Cpu, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

// --- Background Component ---
const Background = () => (
    <div className="fixed inset-0 overflow-hidden bg-black pointer-events-none">
        {/* Background Gradients */}
        <div className="absolute top-[-20%] left-[-20%] w-[800px] h-[800px] bg-blue-900/20 rounded-full blur-[150px] animate-pulse" style={{ animationDuration: '6s' }} />
        <div className="absolute bottom-[-20%] right-[-20%] w-[800px] h-[800px] bg-cyan-900/10 rounded-full blur-[150px] animate-pulse" style={{ animationDuration: '8s' }} />

        {/* Grid Texture */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,#000_60%,transparent_100%)]" />
    </div>
);

// --- Input Component ---
const InputField = ({ id, type, placeholder, icon: Icon, value, onChange, required }) => (
    <div className="relative group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors duration-300">
            {Icon && <Icon size={20} />}
        </div>
        <input
            id={id}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            className="w-full h-14 bg-slate-950/50 border border-slate-800 rounded-2xl pl-12 pr-4 text-slate-200 placeholder:text-slate-600 
                       focus:outline-none focus:border-cyan-500/50 focus:bg-slate-900/80 focus:ring-1 focus:ring-cyan-500/30 
                       transition-all duration-300 backdrop-blur-md"
        />
    </div>
);

export default function LoginPage() {
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');

    const navigate = useNavigate();

    useEffect(() => {
        if (localStorage.getItem('authToken')) navigate('/');
    }, [navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
        const payload = isLogin ? { email, password } : { email, password, name };

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.status === 'success') {
                if (isLogin) {
                    localStorage.setItem('isAuthenticated', 'true');
                    localStorage.setItem('userName', data.user.name);
                    localStorage.setItem('authToken', data.token);
                    window.dispatchEvent(new Event('storage'));
                    navigate('/');
                } else {
                    alert('회원가입이 완료되었습니다. 로그인해주세요.');
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                setError(data.message || '요청 처리에 실패했습니다.');
            }
        } catch (err) {
            setError('서버 연결에 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center p-4 font-sans text-slate-200">
            <Background />

            {/* Main Container - Bento Grid Style */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="relative z-10 w-full max-w-5xl grid grid-cols-1 md:grid-cols-5 gap-4 md:h-[600px]"
            >

                {/* Left Panel: Brand & Agentic Status (Span 2) */}
                <div className="md:col-span-2 bg-slate-900/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden group">
                    {/* Glow Effect */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />

                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            <span className="text-xs font-mono text-green-500 tracking-wider">SYSTEM ONLINE</span>
                        </div>
                        <h1 className="text-3xl font-extrabold text-white leading-tight mb-2">
                            CHEONGAN<br />INTELLIGENCE
                        </h1>
                        <p className="text-slate-400 text-sm">
                            AI 기반 실시간 시장 분석 및<br />자율 트레이딩 시스템
                        </p>
                    </div>

                    {/* Agentic Point: Pulsing Core */}
                    <div className="flex-1 flex items-center justify-center py-8">
                        <div className="relative">
                            <div className="absolute inset-0 bg-cyan-500 blur-[40px] opacity-20 animate-pulse" />
                            <div className="relative w-24 h-24 bg-slate-900 border border-cyan-500/50 rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.3)]">
                                <Activity className="w-10 h-10 text-cyan-400 animate-pulse" />
                            </div>
                            {/* Orbiting Particles */}
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                                className="absolute inset-[-20px] rounded-full border border-dashed border-cyan-500/20"
                            />
                        </div>
                    </div>

                    {/* Stats / Info */}
                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-slate-950/50 p-3 rounded-xl border border-white/5">
                            <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Cpu size={12} /> AI 엔진</div>
                            <div className="text-sm font-bold text-white">V3.5 Active</div>
                        </div>
                        <div className="bg-slate-950/50 p-3 rounded-xl border border-white/5">
                            <div className="text-xs text-slate-500 mb-1 flex items-center gap-1"><Zap size={12} /> 응답 속도</div>
                            <div className="text-sm font-bold text-cyan-400">12ms</div>
                        </div>
                    </div>
                </div>

                {/* Right Panel: Login Form (Span 3) */}
                <div className="md:col-span-3 bg-slate-900/60 backdrop-blur-3xl border border-white/10 rounded-3xl p-8 md:p-12 flex flex-col justify-center relative shadow-2xl">
                    {/* Tab Switcher */}
                    <div className="flex bg-slate-950/50 p-1.5 rounded-2xl mb-8 border border-white/5 max-w-xs mx-auto w-full">
                        {['로그인', '회원가입'].map((tab, idx) => {
                            const isSignIn = idx === 0;
                            const active = isLogin === isSignIn;
                            return (
                                <button
                                    key={tab}
                                    onClick={() => { setIsLogin(isSignIn); setError(null); }}
                                    className={`flex-1 py-2.5 text-sm font-bold rounded-xl transition-all duration-300 relative ${active ? 'text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
                                        }`}
                                >
                                    {active && (
                                        <motion.div
                                            layoutId="activeTabBg"
                                            className="absolute inset-0 bg-slate-800 rounded-xl"
                                            transition={{ type: "spring", stiffness: 400, damping: 30 }}
                                        />
                                    )}
                                    <span className="relative z-10">{tab}</span>
                                </button>
                            );
                        })}
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5 max-w-sm mx-auto w-full">
                        <AnimatePresence mode="wait">
                            {!isLogin && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <InputField id="name" type="text" placeholder="이름 (Full Name)" icon={User} value={name} onChange={e => setName(e.target.value)} required />
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <InputField id="email" type="email" placeholder="이메일 주소" icon={Mail} value={email} onChange={e => setEmail(e.target.value)} required />

                        <InputField id="password" type="password" placeholder="비밀번호" icon={Lock} value={password} onChange={e => setPassword(e.target.value)} required />

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs font-medium flex items-center gap-3"
                            >
                                <ShieldCheck size={16} className="shrink-0" /> {error}
                            </motion.div>
                        )}

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="group w-full h-14 mt-6 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-base font-bold rounded-2xl shadow-[0_0_30px_-5px_rgba(6,182,212,0.4)] border border-white/10 transition-all duration-300 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 relative overflow-hidden"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                            {isLoading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <>
                                    {isLogin ? '시스템 접속' : '계정 생성'}
                                    <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-8 text-center text-xs text-slate-500">
                        <p>Secured by Cheongan FinTech V3.5</p>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
