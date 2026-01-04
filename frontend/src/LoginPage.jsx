import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Mail, ShieldCheck, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const Background = () => (
    <div className="absolute inset-0 overflow-hidden pointer-events-none bg-[#09090b]">
        {/* Deep Gradient Base */}
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-[#09090b] to-black" />

        {/* Subtle Textured Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)] opacity-20" />

        {/* Dynamic Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] bg-cyan-900/10 rounded-full blur-[120px] mix-blend-screen animate-pulse" style={{ animationDuration: '8s' }} />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[100px] mix-blend-screen animate-pulse" style={{ animationDuration: '10s' }} />
    </div>
);

const InputField = ({ id, type, placeholder, icon: Icon, value, onChange, required }) => (
    <div className="relative group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors duration-300 pointer-events-none">
            {Icon && <Icon size={18} />}
        </div>
        <input
            id={id}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            className="w-full h-12 bg-white/5 border border-white/10 rounded-xl pl-11 pr-4 text-sm text-slate-200 placeholder:text-slate-600 
                       focus:outline-none focus:border-cyan-500/50 focus:bg-white/10 focus:ring-1 focus:ring-cyan-500/50 
                       transition-all duration-300 backdrop-blur-sm shadow-inner"
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
                    alert('Account created! Please sign in.');
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                setError(data.message || 'Action failed.');
            }
        } catch (err) {
            setError('Server unavailable.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center p-6 font-sans overflow-hidden">
            <Background />

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="relative w-full max-w-[380px] z-10"
            >
                {/* Brand Header */}
                <div className="text-center mb-10">
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.2, duration: 0.5 }}
                        className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-2xl shadow-[0_0_30px_-5px_rgba(6,182,212,0.4)] mb-6 relative group"
                    >
                        <div className="absolute inset-0 bg-white/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        <Activity className="text-white w-8 h-8" />
                    </motion.div>
                    <h1 className="text-3xl font-extrabold text-white tracking-tight mb-2 drop-shadow-lg">
                        CHEONGAN
                    </h1>
                    <div className="h-[2px] w-8 bg-cyan-500/50 mx-auto mb-2 rounded-full" />
                    <p className="text-slate-400 text-xs font-medium tracking-widest uppercase opacity-80">
                        Global Strategic Intelligence
                    </p>
                </div>

                {/* Glassmorphism Card */}
                <div className="relative bg-[#0f172a]/80 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl overflow-hidden ring-1 ring-white/5">

                    {/* Top Lighting Accent */}
                    <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />

                    <div className="p-8 pb-6">
                        {/* Tab Switcher */}
                        <div className="flex bg-black/20 p-1.5 rounded-xl mb-6 relative">
                            {['Sign In', 'Create Account'].map((tab, idx) => {
                                const isSignIn = idx === 0;
                                const active = isLogin === isSignIn;
                                return (
                                    <button
                                        key={tab}
                                        onClick={() => { setIsLogin(isSignIn); setError(null); }}
                                        className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all duration-300 relative z-10 ${active ? 'text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'
                                            }`}
                                    >
                                        {active && (
                                            <motion.div
                                                layoutId="activeTabBg"
                                                className="absolute inset-0 bg-[#1e293b] rounded-lg shadow-inner border border-white/5"
                                                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                            />
                                        )}
                                        <span className="relative">{tab}</span>
                                    </button>
                                );
                            })}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            <AnimatePresence mode="wait">
                                {!isLogin && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: "auto", opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden"
                                    >
                                        <InputField id="name" type="text" placeholder="Full Name" icon={User} value={name} onChange={e => setName(e.target.value)} required />
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <InputField id="email" type="email" placeholder="Email Address" icon={Mail} value={email} onChange={e => setEmail(e.target.value)} required />

                            <InputField id="password" type="password" placeholder="Password" icon={Lock} value={password} onChange={e => setPassword(e.target.value)} required />

                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: -5 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs font-medium flex items-center gap-2"
                                >
                                    <ShieldCheck size={14} className="shrink-0" /> {error}
                                </motion.div>
                            )}

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="group w-full h-12 mt-4 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-sm font-bold rounded-xl shadow-[0_5px_20px_-5px_rgba(6,182,212,0.4)] border border-white/10 hover:border-white/20 transition-all duration-300 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 overflow-hidden relative"
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                                {isLoading ? (
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <>
                                        {isLogin ? 'Sign In' : 'Get Started'}
                                        <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    {/* Footer Area */}
                    <div className="px-8 py-5 bg-[#0b111e]/50 border-t border-white/5 text-center">
                        <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1.5 opacity-70">
                            <ShieldCheck size={12} className="text-cyan-500/70" /> Secured with 256-bit AES Encryption
                        </p>
                    </div>
                </div>

                {/* Bottom Copyright */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="mt-8 text-center"
                >
                    <p className="text-[11px] text-slate-600 font-medium tracking-wide">
                        &copy; 2026 CHEONGAN FINTECH
                    </p>
                </motion.div>
            </motion.div>
        </div>
    );
}
