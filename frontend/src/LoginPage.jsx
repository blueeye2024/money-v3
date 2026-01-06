import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, ArrowRight, Loader2 } from 'lucide-react';
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
        <div className="min-h-screen w-full flex items-center justify-center bg-[#050505] font-sans selection:bg-[#0A84FF]/30 relative overflow-hidden">
            {/* Background Gradients */}
            <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] mix-blend-screen animate-pulse" style={{ animationDuration: '4s' }} />
            <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] mix-blend-screen" />

            <div className="w-full max-w-[400px] p-8 flex flex-col items-center relative z-10">
                {/* Glass Card Container */}
                <div className="absolute inset-0 bg-white/[0.02] backdrop-blur-xl rounded-3xl border border-white/[0.05] shadow-2xl" />

                <div className="relative z-20 w-full flex flex-col items-center py-6">
                    {/* 1. Header (Logo & Title) */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex flex-col items-center mb-8 text-center"
                    >
                        <div className="w-16 h-16 bg-gradient-to-br from-[#1C1C1E] to-[#2c2c2e] rounded-2xl flex items-center justify-center mb-5 shadow-lg border border-white/10 group">
                            <TrendingUp className="w-8 h-8 text-[#0A84FF] group-hover:scale-110 transition-transform duration-300" />
                        </div>
                        <h1 className="text-[28px] font-bold text-white tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
                            Cheongan ID
                        </h1>
                        <p className="text-[14px] text-[#86868B] mt-2 font-medium">
                            {isLogin ? 'Welcome back, Commander.' : 'Join the Intelligence Network.'}
                        </p>
                    </motion.div>

                    {/* 2. Form Section */}
                    <motion.form
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        onSubmit={handleSubmit}
                        className="w-full space-y-5"
                    >
                        <AnimatePresence mode="popLayout">
                            {!isLogin && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="space-y-1">
                                        <input
                                            type="text"
                                            value={name}
                                            onChange={(e) => setName(e.target.value)}
                                            required={!isLogin}
                                            placeholder="User Name"
                                            className="w-full h-[50px] bg-white/5 rounded-xl px-4 text-[15px] text-white placeholder-white/20 border border-white/5 focus:border-[#0A84FF]/50 focus:bg-white/10 focus:ring-1 focus:ring-[#0A84FF]/50 outline-none transition-all duration-200"
                                        />
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="space-y-4">
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                placeholder="Email Access"
                                className="w-full h-[50px] bg-white/5 rounded-xl px-4 text-[15px] text-white placeholder-white/20 border border-white/5 focus:border-[#0A84FF]/50 focus:bg-white/10 focus:ring-1 focus:ring-[#0A84FF]/50 outline-none transition-all duration-200"
                            />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                placeholder="Security Token (Password)"
                                className="w-full h-[50px] bg-white/5 rounded-xl px-4 text-[15px] text-white placeholder-white/20 border border-white/5 focus:border-[#0A84FF]/50 focus:bg-white/10 focus:ring-1 focus:ring-[#0A84FF]/50 outline-none transition-all duration-200"
                            />
                        </div>

                        {/* Error Message */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -5 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-[#ff5b5b] text-[13px] text-center font-medium py-1 bg-red-500/10 rounded-lg border border-red-500/20"
                            >
                                {error}
                            </motion.div>
                        )}

                        {/* 3. Action Button */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full h-[50px] bg-gradient-to-r from-[#0A84FF] to-[#0077ED] hover:from-[#0077ED] hover:to-[#0066CC] active:scale-[0.98] text-white text-[16px] font-semibold rounded-xl shadow-lg shadow-blue-500/20 transition-all duration-200 flex items-center justify-center gap-2 mt-4"
                        >
                            {isLoading ? (
                                <Loader2 className="w-5 h-5 animate-spin text-white/80" />
                            ) : (
                                <>
                                    {isLogin ? 'Access System' : 'Create Credential'}
                                    <ArrowRight className="w-4 h-4 opacity-70" />
                                </>
                            )}
                        </button>

                        {/* Forgot Password Link */}
                        {isLogin && (
                            <div className="text-center">
                                <button type="button" className="text-[12px] text-white/40 hover:text-white/60 transition-colors">
                                    Lost your access key?
                                </button>
                            </div>
                        )}
                    </motion.form>

                    {/* 4. Toggle Link */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="mt-8 pt-6 border-t border-white/5 w-full text-center"
                    >
                        <p className="text-[13px] text-[#86868B]">
                            {isLogin ? 'Need clearance?' : 'Already have credentials?'}
                            <button
                                onClick={() => { setIsLogin(!isLogin); setError(null); }}
                                className="ml-2 text-[#0A84FF] hover:text-[#409CFF] font-medium transition-colors"
                            >
                                {isLogin ? 'Register' : 'Login'}
                            </button>
                        </p>
                    </motion.div>

                    {/* Footer */}
                    <div className="mt-6 text-[10px] text-white/20 tracking-wider">
                        SECURE CONNECTION ESTABLISHED
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
