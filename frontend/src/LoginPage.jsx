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
        <div className="min-h-screen w-full flex items-center justify-center bg-black font-sans selection:bg-[#0A84FF]/30">
            <div className="w-full max-w-[380px] p-6 flex flex-col items-center">

                {/* 1. Header (Logo & Title) */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center mb-10 text-center"
                >
                    <div className="w-16 h-16 bg-[#1C1C1E] rounded-[18px] flex items-center justify-center mb-5 shadow-inner border border-[#2C2C2E]">
                        <TrendingUp className="w-8 h-8 text-[#0A84FF]" />
                    </div>
                    <h1 className="text-[26px] font-semibold text-white tracking-tight">
                        Cheongan ID
                    </h1>
                    <p className="text-[15px] text-[#86868B] mt-2 font-normal leading-relaxed">
                        {isLogin ? '청안 인텔리전스에 로그인하세요.' : '새로운 계정을 생성하여 시작하세요.'}
                    </p>
                </motion.div>

                {/* 2. Form Section */}
                <motion.form
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.1 }}
                    onSubmit={handleSubmit}
                    className="w-full space-y-4"
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
                                        placeholder="이름"
                                        className="w-full h-[52px] bg-[#1C1C1E] rounded-xl px-4 text-[17px] text-white placeholder-[#58585C] border border-transparent focus:border-[#0A84FF] focus:ring-1 focus:ring-[#0A84FF] outline-none transition-all duration-200"
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
                            placeholder="이메일 주소"
                            className="w-full h-[52px] bg-[#1C1C1E] rounded-xl px-4 text-[17px] text-white placeholder-[#58585C] border border-transparent focus:border-[#0A84FF] focus:ring-1 focus:ring-[#0A84FF] outline-none transition-all duration-200"
                        />
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            placeholder="비밀번호"
                            className="w-full h-[52px] bg-[#1C1C1E] rounded-xl px-4 text-[17px] text-white placeholder-[#58585C] border border-transparent focus:border-[#0A84FF] focus:ring-1 focus:ring-[#0A84FF] outline-none transition-all duration-200"
                        />
                    </div>

                    {/* Error Message */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-[#FF453A] text-[13px] text-center font-medium py-1"
                        >
                            {error}
                        </motion.div>
                    )}

                    {/* 3. Action Button (Below Inputs) */}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full h-[52px] bg-[#0A84FF] hover:bg-[#0077ED] active:scale-[0.98] text-white text-[17px] font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 mt-2 disabled:opacity-70 disabled:cursor-not-allowed"
                    >
                        {isLoading ? (
                            <Loader2 className="w-5 h-5 animate-spin text-white/80" />
                        ) : (
                            <>
                                {isLogin ? '로그인' : '계정 생성'}
                                <ArrowRight className="w-4 h-4 opacity-70" />
                            </>
                        )}
                    </button>

                    {/* Forgot Password Link (Login Only) */}
                    {isLogin && (
                        <div className="text-center">
                            <button type="button" className="text-[13px] text-[#0A84FF] hover:underline font-medium">
                                비밀번호를 잊으셨나요?
                            </button>
                        </div>
                    )}
                </motion.form>

                {/* 4. Toggle Link (Bottom, Centered) */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="mt-12 pt-6 border-t border-[#2C2C2E] w-full text-center"
                >
                    <p className="text-[15px] text-[#86868B]">
                        {isLogin ? '계정이 없으신가요?' : '이미 계정이 있으신가요?'}
                        <button
                            onClick={() => { setIsLogin(!isLogin); setError(null); }}
                            className="ml-2 text-[#0A84FF] hover:text-[#409CFF] font-medium transition-colors"
                        >
                            {isLogin ? '지금 가입하기' : '로그인'}
                        </button>
                    </p>
                </motion.div>

                {/* Footer Copy */}
                <div className="mt-8 text-[11px] text-[#48484A] font-medium tracking-wide">
                    COPYRIGHT © 2026 CHEONGAN. ALL RIGHTS RESERVED.
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
