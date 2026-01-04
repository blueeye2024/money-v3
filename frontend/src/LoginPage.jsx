import React, { useState, useEffect } from 'react';
import { User, Lock, ArrowRight, Github, Mail, UserPlus, LogIn } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Shadcn/UI 스타일의 유틸리티 컴포넌트 (Tailwind 기반)
const Card = ({ children, className = "" }) => (
    <div className={`bg-white/90 backdrop-blur-sm rounded-xl border border-slate-200 shadow-xl overflow-hidden ${className}`}>
        {children}
    </div>
);

const CardHeader = ({ children, className = "" }) => (
    <div className={`p-6 pb-2 ${className}`}>{children}</div>
);

const CardContent = ({ children, className = "" }) => (
    <div className={`p-6 pt-2 ${className}`}>{children}</div>
);

const CardFooter = ({ children, className = "" }) => (
    <div className={`p-6 pt-0 flex items-center ${className}`}>{children}</div>
);

const Label = ({ children, htmlFor }) => (
    <label htmlFor={htmlFor} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-slate-700 block mb-2">
        {children}
    </label>
);

const Input = ({ id, type, placeholder, value, onChange, required }) => (
    <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
    />
);

const Button = ({ children, variant = "primary", className = "", ...props }) => {
    const baseStyle = "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2 w-full";
    const variants = {
        primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm",
        outline: "border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 text-slate-700",
        ghost: "bg-transparent text-slate-600 hover:bg-slate-100"
    };

    return (
        <button className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
};

export default function LoginPage() {
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [rememberMe, setRememberMe] = useState(true);

    // Form States
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState(''); // 회원가입용

    const navigate = useNavigate();

    // Auto Login Check
    useEffect(() => {
        const token = localStorage.getItem('authToken');
        if (token) navigate('/');
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
                    // Login Success
                    localStorage.setItem('authToken', data.token);
                    localStorage.setItem('isAuthenticated', 'true');
                    localStorage.setItem('userName', data.user.name);

                    // Trigger storage event for App.jsx
                    window.dispatchEvent(new Event('storage'));

                    navigate('/');
                } else {
                    // Register Success
                    alert("회원가입이 완료되었습니다. 로그인해주세요.");
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                setError(data.message || "처리 중 오류가 발생했습니다.");
            }
        } catch (err) {
            console.error(err);
            setError("서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 p-4">
            <Card className="w-full max-w-md animate-in fade-in zoom-in duration-500 slide-in-from-bottom-4">
                <CardHeader className="text-center space-y-1">
                    <div className="mx-auto w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mb-4 transition-transform hover:scale-110 duration-200">
                        {isLogin ? <Lock className="w-6 h-6 text-indigo-600" /> : <UserPlus className="w-6 h-6 text-indigo-600" />}
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-slate-900">
                        {isLogin ? "Welcome Back" : "Create Account"}
                    </h2>
                    <p className="text-sm text-slate-500">
                        {isLogin ? "Enter your credentials to access the workspace" : "Sign up to start your financial journey"}
                    </p>
                </CardHeader>

                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        {error && (
                            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-md flex items-center">
                                <span className="mr-2">⚠️</span> {error}
                            </div>
                        )}

                        {!isLogin && (
                            <div className="space-y-2 animate-in fade-in slide-in-from-left-4 duration-300">
                                <Label htmlFor="name">Full Name</Label>
                                <div className="relative">
                                    <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                    <Input
                                        id="name"
                                        type="text"
                                        placeholder="홍길동"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        required={!isLogin}
                                        className="pl-10"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="pl-10"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="password">Password</Label>
                                {isLogin && (
                                    <a href="#" className="text-xs text-indigo-600 hover:text-indigo-500 font-medium">
                                        Forgot password?
                                    </a>
                                )}
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    className="pl-10"
                                />
                            </div>
                        </div>

                        {isLogin && (
                            <div className="flex items-center space-x-2">
                                <input
                                    type="checkbox"
                                    id="remember"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                                />
                                <label htmlFor="remember" className="text-sm text-slate-600 cursor-pointer">
                                    접속 유지 (Keep me signed in)
                                </label>
                            </div>
                        )}
                    </CardContent>

                    <CardFooter className="flex-col gap-4">
                        <Button type="submit" disabled={isLoading} className="w-full">
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    {isLogin ? "Signing in..." : "Creating account..."}
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    {isLogin ? "Sign In" : "Create Account"} <ArrowRight className="w-4 h-4" />
                                </span>
                            )}
                        </Button>

                        <div className="relative w-full">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-slate-200" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-white px-2 text-slate-500">Or</span>
                            </div>
                        </div>

                        <div className="flex w-full gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setIsLogin(!isLogin);
                                    setError(null);
                                }}
                                className="w-full"
                            >
                                {isLogin ? (
                                    <> <UserPlus className="mr-2 h-4 w-4" /> Create an account </>
                                ) : (
                                    <> <LogIn className="mr-2 h-4 w-4" /> Already have an account? </>
                                )}
                            </Button>
                        </div>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
