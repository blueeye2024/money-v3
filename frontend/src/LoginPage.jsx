import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Mail, UserPlus, LogIn, TrendingUp, Activity, Globe, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

// --- Styled Components (Tailwind + Framer) ---

const GlassCard = ({ children, className = "" }) => (
    <div className={`relative bg-black/40 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden rounded-3xl ${className}`}>
        {/* Inner Glare Effect */}
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />
        {children}
    </div>
);

const Input = ({ id, type, placeholder, value, onChange, required, icon: Icon }) => (
    <div className="relative group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-cyan-400 transition-colors duration-300">
            {Icon && <Icon className="w-5 h-5" />}
        </div>
        <input
            id={id}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-12 py-3.5 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500/50 focus:bg-slate-900/80 focus:ring-1 focus:ring-cyan-500/50 transition-all duration-300"
        />
    </div>
);

const Button = ({ children, variant = "primary", className = "", isLoading, ...props }) => {
    const baseStyle = "relative inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-all duration-300 overflow-hidden h-12 w-full active:scale-[0.98]";

    // Gradient Primary
    const primaryStyle = "bg-gradient-to-r from-cyan-600 to-blue-600 text-white hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] border border-transparent";
    // Outline Secondary
    const outlineStyle = "bg-transparent border border-white/10 text-slate-400 hover:text-white hover:bg-white/5";

    return (
        <button className={`${baseStyle} ${variant === 'primary' ? primaryStyle : outlineStyle} ${className}`} disabled={isLoading} {...props}>
            {isLoading ? (
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span className="opacity-80">Processing...</span>
                </div>
            ) : children}
        </button>
    );
};

// --- Animated Background Components ---

const BackgroundEffects = () => (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Dark Base */}
        <div className="absolute inset-0 bg-slate-950" />

        {/* Grid Pattern */}
        <div className="absolute inset-0 opacity-[0.03]"
            style={{ backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)', backgroundSize: '50px 50px' }}
        />

        {/* Moving Orbs */}
        <motion.div
            animate={{
                x: [0, 100, 0],
                y: [0, -50, 0],
                scale: [1, 1.2, 1]
            }}
            transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px]"
        />
        <motion.div
            animate={{
                x: [0, -100, 0],
                y: [0, 100, 0],
                scale: [1, 1.3, 1]
            }}
            transition={{ duration: 25, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
            className="absolute bottom-[-10%] right-[10%] w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[120px]"
        />
        <motion.div
            animate={{ opacity: [0.1, 0.3, 0.1] }}
            transition={{ duration: 10, repeat: Infinity }}
            className="absolute top-[40%] left-[50%] -translate-x-1/2 w-[800px] h-[300px] bg-indigo-900/20 rounded-full blur-[100px] rotate-12"
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

    // Animate presence for form switching
    const [activeTab, setActiveTab] = useState('login'); // 'login' or 'register'

    const navigate = useNavigate();

    useEffect(() => {
        const token = localStorage.getItem('authToken');
        if (token) navigate('/');
    }, [navigate]);

    const handleTabChange = (mode) => {
        setIsLogin(mode);
        setActiveTab(mode ? 'login' : 'register');
        setError(null);
    }

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
                    localStorage.setItem('authToken', data.token);
                    localStorage.setItem('isAuthenticated', 'true');
                    localStorage.setItem('userName', data.user.name);
                    window.dispatchEvent(new Event('storage'));
                    navigate('/');
                } else {
                    alert("Account created successfully. Please sign in.");
                    handleTabChange(true);
                    setPassword('');
                }
            } else {
                setError(data.message || "Operation failed.");
            }
        } catch (err) {
            console.error(err);
            setError("Server connection failed. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen w-full flex items-center justify-center p-4 font-sans text-slate-200">
            <BackgroundEffects />

            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="relative z-10 w-full max-w-[440px]"
            >
                {/* Brand Logo Area */}
                <div className="flex flex-col items-center mb-8">
                    <motion.div
                        initial={{ y: -20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="relative group"
                    >
                        <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-2xl blur opacity-40 group-hover:opacity-75 transition duration-500" />
                        <div className="relative w-16 h-16 bg-slate-900 rounded-2xl flex items-center justify-center border border-white/10 shadow-xl">
                            <TrendingUp className="w-8 h-8 text-cyan-400" />
                        </div>
                    </motion.div>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                        className="text-center mt-6"
                    >
                        <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">
                            CHEONGAN
                        </h1>
                        <p className="text-slate-400 text-sm font-medium tracking-wide uppercase opacity-80">
                            Global Market Intelligence
                        </p>
                    </motion.div>
                </div>

                <GlassCard>
                    <div className="p-8">
                        {/* Tab Switcher */}
                        <div className="flex p-1 bg-slate-900/50 rounded-xl mb-8 border border-white/5">
                            {['Sign In', 'Create Account'].map((tab, idx) => {
                                const isSignIn = idx === 0;
                                const isActive = isSignIn === isLogin;
                                return (
                                    <button
                                        key={tab}
                                        onClick={() => handleTabChange(isSignIn)}
                                        className={`relative flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${isActive ? 'text-white' : 'text-slate-500 hover:text-slate-400'
                                            }`}
                                    >
                                        {isActive && (
                                            <motion.div
                                                layoutId="activeTab"
                                                className="absolute inset-0 bg-white/10 rounded-lg shadow-sm"
                                                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                            />
                                        )}
                                        <span className="relative z-10">{tab}</span>
                                    </button>
                                );
                            })}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-5">
                            <AnimatePresence mode="wait">
                                {!isLogin && (
                                    <motion.div
                                        key="name-field"
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: "auto", opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="mb-5">
                                            <Input
                                                id="name"
                                                type="text"
                                                icon={User}
                                                placeholder="Full Name"
                                                value={name}
                                                onChange={(e) => setName(e.target.value)}
                                                required={!isLogin}
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <Input
                                id="email"
                                type="email"
                                icon={Mail}
                                placeholder="Email Address"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />

                            <div className="space-y-2">
                                <Input
                                    id="password"
                                    type="password"
                                    icon={Lock}
                                    placeholder="Password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                                {isLogin && (
                                    <div className="flex justify-end">
                                        <a href="#" className="text-xs text-slate-500 hover:text-cyan-400 transition-colors">
                                            Forgot your password?
                                        </a>
                                    </div>
                                )}
                            </div>

                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400 text-sm"
                                >
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                                    {error}
                                </motion.div>
                            )}

                            <div className="pt-2">
                                <Button type="submit" variant="primary" isLoading={isLoading}>
                                    {isLogin ? (
                                        <span className="flex items-center gap-2">
                                            Access Dashboard <ArrowRight className="w-4 h-4" />
                                        </span>
                                    ) : (
                                        "Create Account"
                                    )}
                                </Button>
                            </div>
                        </form>
                    </div>

                    {/* Footer decoration */}
                    <div className="p-4 border-t border-white/5 bg-white/[0.02] text-center">
                        <p className="text-xs text-slate-600 flex items-center justify-center gap-2">
                            <ShieldCheck className="w-3 h-3" /> Secure 256-bit Encryption
                        </p>
                    </div>
                </GlassCard>

                {/* Footer Links */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="mt-8 text-center text-xs text-slate-600"
                >
                    <p>&copy; 2026 Cheongan FinTech. All rights reserved.</p>
                </motion.div>
            </motion.div>
        </div>
    );
}
