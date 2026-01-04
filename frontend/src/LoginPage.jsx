import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Lock, ArrowRight, TrendingUp, Github, Globe } from 'lucide-react';
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
        <div className="min-h-screen w-full flex items-center justify-center bg-[#09090b] text-slate-200 font-sans p-4 selection:bg-blue-500/30">
            {/* Subtle Gradient Background */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900/10 via-[#09090b] to-[#09090b]" />
            </div>

            <motion.div
                initial={{ opacity: 0, scale: 0.98, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="relative w-full max-w-[400px] z-10"
            >
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-xl shadow-lg shadow-blue-900/20 mb-4">
                        <TrendingUp className="text-white w-6 h-6" />
                    </div>
                    <h1 className="text-2xl font-bold text-white tracking-tight">
                        Cheongan Intelligence
                    </h1>
                    <p className="text-slate-500 text-sm mt-2">
                        {isLogin ? '계정에 로그인하여 시작하세요' : '새로운 계정을 생성하세요'}
                    </p>
                </div>

                {/* Card */}
                <div className="bg-[#121212] border border-[#27272a] rounded-2xl shadow-xl overflow-hidden">
                    <div className="p-6 md:p-8 space-y-6">

                        {/* Social Login (Mock) */}
                        <div className="grid grid-cols-2 gap-3">
                            <button className="flex items-center justify-center gap-2 h-10 bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] rounded-lg text-sm font-medium transition-colors text-slate-300">
                                <Github size={16} /> GitHub
                            </button>
                            <button className="flex items-center justify-center gap-2 h-10 bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] rounded-lg text-sm font-medium transition-colors text-slate-300">
                                <Globe size={16} /> Google
                            </button>
                        </div>

                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-[#27272a]" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-[#121212] px-2 text-slate-500">Or continue with</span>
                            </div>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {!isLogin && (
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-slate-400 ml-1">이름</label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                        <input
                                            type="text"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            required={!isLogin}
                                            placeholder="홍길동"
                                            className="w-full h-11 bg-[#0a0a0a] border border-[#27272a] rounded-lg pl-10 pr-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-400 ml-1">이메일</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                        placeholder="name@example.com"
                                        className="w-full h-11 bg-[#0a0a0a] border border-[#27272a] rounded-lg pl-10 pr-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-xs font-semibold text-slate-400 ml-1">비밀번호</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        placeholder="••••••••"
                                        className="w-full h-11 bg-[#0a0a0a] border border-[#27272a] rounded-lg pl-10 pr-3 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                    />
                                </div>
                            </div>

                            {error && (
                                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium text-center">
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full h-11 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg shadow-lg hover:shadow-blue-500/20 transition-all duration-200 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
                            >
                                {isLoading ? (
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        {isLogin ? '로그인' : '계정 생성'}
                                        <ArrowRight size={16} />
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    <div className="px-6 py-4 bg-[#18181b] border-t border-[#27272a]">
                        <p className="text-center text-xs text-slate-500">
                            {isLogin ? "계정이 없으신가요?" : "이미 계정이 있으신가요?"}{' '}
                            <button
                                onClick={() => { setIsLogin(!isLogin); setError(null); }}
                                className="text-blue-500 hover:text-blue-400 font-semibold hover:underline transition-all"
                            >
                                {isLogin ? "회원가입" : "로그인"}
                            </button>
                        </p>
                    </div>
                </div>

                <p className="text-center text-[10px] text-slate-600 mt-6">
                    © 2026 Cheongan FinTech. Secure Access System.
                </p>
            </motion.div>
        </div>
    );
};

export default LoginPage;
