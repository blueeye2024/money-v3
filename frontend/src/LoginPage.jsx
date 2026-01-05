import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Lock, ArrowRight, TrendingUp, ShieldCheck, Mail, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
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
                    alert('계정이 생성되었습니다. 로그인해주세요.');
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                setError(data.message || '요청을 처리할 수 없습니다.');
            }
        } catch (err) {
            setError('서버에 연결할 수 없습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center overflow-hidden bg-black font-sans selection:bg-cyan-500/30">
            {/* --- Background Effects --- */}
            <div className="absolute inset-0 z-0">
                {/* Deep Space Base */}
                <div className="absolute inset-0 bg-[#050505]" />

                {/* Aurora Gradients */}
                <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-blue-600/20 rounded-full blur-[120px] mix-blend-screen opacity-40 animate-pulse" style={{ animationDuration: '4s' }} />
                <div className="absolute bottom-[-10%] right-[-10%] w-[40vw] h-[40vw] bg-cyan-600/20 rounded-full blur-[120px] mix-blend-screen opacity-40 animate-pulse" style={{ animationDuration: '7s' }} />

                {/* Subtle Grid Texture */}
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:3rem_3rem] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_100%,transparent_100%)] opacity-20" />
            </div>

            {/* --- Main Content --- */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="relative z-10 w-full max-w-[420px] p-6"
            >
                {/* Brand Logo Section */}
                <div className="flex flex-col items-center mb-10 text-center">
                    <motion.div
                        initial={{ scale: 0 }} animate={{ scale: 1 }}
                        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                        div className="relative group mb-6"
                    >
                        <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-2xl blur-lg opacity-40 group-hover:opacity-60 transition-opacity duration-500" />
                        <div className="relative w-20 h-20 bg-gradient-to-tr from-[#1a1a1a] to-[#0a0a0a] rounded-2xl border border-white/10 flex items-center justify-center shadow-2xl">
                            <TrendingUp className="w-10 h-10 text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]" />
                        </div>
                        {/* Status Dot */}
                        <div className="absolute -top-1 -right-1 w-4 h-4 bg-black rounded-full flex items-center justify-center">
                            <div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
                        </div>
                    </motion.div>

                    <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60 tracking-tight mb-2">
                        Cheongan <span className="font-light text-cyan-400">Intelligence</span>
                    </h1>
                    <p className="text-sm text-slate-500 font-medium tracking-wide">
                        PREMIER AI TRADING SYSTEM V3.5
                    </p>
                </div>

                {/* Glass Card */}
                <div className="bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-3xl shadow-[0_0_40px_-10px_rgba(0,0,0,0.5)] overflow-hidden">
                    {/* Top Highlight Line */}
                    <div className="h-[1px] w-full bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent opacity-50" />

                    <div className="p-8">
                        {/* Toggle Tabs */}
                        <div className="flex p-1 bg-black/40 rounded-xl mb-8 border border-white/5">
                            {['로그인', '회원가입'].map((tab, idx) => {
                                const isSignIn = idx === 0;
                                const active = isLogin === isSignIn;
                                return (
                                    <button
                                        key={tab}
                                        onClick={() => { setIsLogin(isSignIn); setError(null); }}
                                        className={`relative flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${active ? 'text-white' : 'text-slate-500 hover:text-slate-300'
                                            }`}
                                    >
                                        {active && (
                                            <motion.div
                                                layoutId="activeTab"
                                                className="absolute inset-0 bg-[#1e293b] rounded-lg shadow-sm border border-white/10"
                                                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                            />
                                        )}
                                        <span className="relative z-10">{tab}</span>
                                    </button>
                                );
                            })}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            {!isLogin && (
                                <div className="space-y-1.5">
                                    <div className="relative group">
                                        <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors" size={18} />
                                        <input
                                            type="text"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            required={!isLogin}
                                            placeholder="이름 (Full Name)"
                                            className="w-full h-12 bg-black/20 border border-white/10 rounded-xl pl-11 pr-4 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-white/5 transition-all"
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="space-y-1.5">
                                <div className="relative group">
                                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors" size={18} />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                        placeholder="이메일 주소"
                                        className="w-full h-12 bg-black/20 border border-white/10 rounded-xl pl-11 pr-4 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-white/5 transition-all"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <div className="relative group">
                                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors" size={18} />
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        placeholder="비밀번호"
                                        className="w-full h-12 bg-black/20 border border-white/10 rounded-xl pl-11 pr-4 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-white/5 transition-all"
                                    />
                                </div>
                            </div>

                            {/* Error Message */}
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }}
                                    className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold flex items-center justify-center gap-2"
                                >
                                    <ShieldCheck size={14} /> {error}
                                </motion.div>
                            )}

                            {/* Submit Button */}
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="group w-full h-12 mt-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-bold rounded-xl shadow-[0_4px_20px_-5px_rgba(6,182,212,0.4)] border border-transparent hover:border-white/20 transition-all duration-300 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 relative overflow-hidden"
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
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
                    </div>

                    {/* Footer Area inside Card */}
                    <div className="px-8 py-5 bg-black/20 border-t border-white/5 text-center">
                        <p className="text-[11px] text-slate-500 flex items-center justify-center gap-1.5 opacity-80">
                            <Sparkles size={12} className="text-cyan-500" />
                            Secured Intelligence Gateway
                        </p>
                    </div>
                </div>

                {/* Bottom Copyright */}
                <p className="text-center text-[10px] text-slate-600 mt-8 tracking-wider uppercase font-medium">
                    © 2026 Cheongan FinTech. All rights reserved.
                </p>
            </motion.div>
        </div>
    );
};

export default LoginPage;
