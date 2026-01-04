import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Lock, ArrowRight, Sparkles } from 'lucide-react';
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
                    alert('에이전트 액세스 신청이 완료되었습니다. 로그인해주세요.');
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                setError(data.message || '요청 처리에 실패했습니다.');
            }
        } catch (err) {
            setError('Nexus 서버 연결에 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center p-4 relative overflow-hidden bg-black font-sans">
            {/* 배경 효과 (대시보드와 동일한 우주/네온 배경) */}
            <div className="absolute inset-0 bg-[#020617] pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px] opacity-30 animate-pulse" style={{ animationDuration: '4s' }}></div>
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-[120px] opacity-30 animate-pulse delay-1000" style={{ animationDuration: '6s' }}></div>
                <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,#000_60%,transparent_100%)]" />
            </div>

            {/* 메인 로그인 글래스 카드 */}
            <motion.div
                initial={{ opacity: 0, y: 30, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="relative z-10 w-full max-w-[450px] rounded-[2.5rem] p-8 md:p-12 border-t border-l border-white/20 shadow-[0_0_50px_rgba(6,182,212,0.15)] bg-slate-900/40 backdrop-blur-2xl"
            >
                {/* 헤더 섹션 */}
                <div className="text-center mb-10">
                    <motion.div
                        initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.3 }}
                        className="inline-flex items-center justify-center bg-cyan-500/10 p-3 rounded-2xl mb-4 border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                    >
                        <Sparkles size={24} className="text-cyan-400" />
                    </motion.div>
                    <h1 className="text-3xl font-black tracking-tighter uppercase italic mb-2 text-white">
                        Antigravity <span className="text-cyan-400 text-sm not-italic font-bold tracking-normal align-middle ml-1">Gateway</span>
                    </h1>
                    <p className="text-slate-400 text-sm font-light tracking-wide">Financial Intelligence Nexus 접속</p>
                </div>

                {/* 폼 섹션 */}
                <form onSubmit={handleSubmit} className="space-y-6">
                    {!isLogin && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            className="group relative overflow-hidden"
                        >
                            <User size={20} className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/30 group-focus-within:text-cyan-400 transition-colors z-10" />
                            <input
                                type="text"
                                placeholder="Agent Name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required={!isLogin}
                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder:text-white/30 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:bg-white/10 transition-all duration-300"
                            />
                        </motion.div>
                    )}

                    {/* 이메일 입력 */}
                    <div className="group relative">
                        <User size={20} className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/30 group-focus-within:text-cyan-400 transition-colors z-10" />
                        <input
                            type="email"
                            placeholder="Email Address"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder:text-white/30 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:bg-white/10 transition-all duration-300"
                        />
                    </div>

                    {/* 비밀번호 입력 */}
                    <div className="group relative">
                        <Lock size={20} className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/30 group-focus-within:text-cyan-400 transition-colors z-10" />
                        <input
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder:text-white/30 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:bg-white/10 transition-all duration-300"
                        />
                    </div>

                    {/* 에러 메시지 */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }}
                            className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl text-sm text-center"
                        >
                            {error}
                        </motion.div>
                    )}

                    {/* 옵션 (로그인 유지 / 비밀번호 찾기) - 로그인 시에만 표시 */}
                    {isLogin && (
                        <div className="flex items-center justify-between text-sm text-white/40 px-1">
                            <label className="flex items-center gap-2 cursor-pointer hover:text-white/60 transition-colors">
                                <input type="checkbox" className="accent-cyan-400 w-4 h-4 rounded border-white/10 bg-white/5 appearance-none checked:bg-cyan-500 checked:border-cyan-500 cursor-pointer relative"
                                    style={{ backgroundImage: "url(\"data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='black' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e\")", backgroundSize: "100% 100%" }}
                                />
                                Remember Agent
                            </label>
                            <a href="#" className="hover:text-cyan-400 transition-colors">Forgot Password?</a>
                        </div>
                    )}

                    {/* 로그인 버튼 */}
                    <motion.button
                        type="submit"
                        disabled={isLoading}
                        whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(6, 182, 212, 0.4)" }}
                        whileTap={{ scale: 0.98 }}
                        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-black text-lg py-4 rounded-2xl flex items-center justify-center gap-2 relative overflow-hidden group transition-all duration-300 disabled:opacity-70 disabled:cursor-not-allowed border border-white/10"
                    >
                        {isLoading ? (
                            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <span className="relative z-10 flex items-center gap-2 tracking-wide uppercase text-sm">
                                {isLogin ? 'Enter Nexus' : 'Initialize Access'} <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                            </span>
                        )}
                        <div className="absolute inset-0 bg-white/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    </motion.button>
                </form>

                {/* 하단 가입 링크 */}
                <div className="mt-8 text-center text-sm text-white/40">
                    <p>
                        {isLogin ? "Nexus 액세스 권한이 없으신가요?" : "이미 계정이 있으신가요?"}{' '}
                        <button
                            onClick={() => { setIsLogin(!isLogin); setError(null); }}
                            className="text-cyan-400 font-bold hover:text-cyan-300 transition-colors ml-1 focus:outline-none"
                        >
                            {isLogin ? "에이전트 액세스 신청하기" : "게이트웨이 로그인"}
                        </button>
                    </p>
                </div>

            </motion.div>
        </div>
    );
};

export default LoginPage;
