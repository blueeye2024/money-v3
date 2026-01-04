import React, { useState } from 'react';
import { User, Lock, ArrowRight, Github } from 'lucide-react';
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
    <label htmlFor={htmlFor} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-slate-700">
        {children}
    </label>
);

const Input = ({ id, type, placeholder }) => (
    <input
        id={id}
        type={type}
        placeholder={placeholder}
        className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200"
    />
);

const Button = ({ children, variant = "primary", className = "", ...props }) => {
    const baseStyle = "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2 w-full";
    const variants = {
        primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm",
        outline: "border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 text-slate-700"
    };

    return (
        <button className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
            {children}
        </button>
    );
};

export default function LoginPage() {
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        setIsLoading(true);

        // 로그인 시뮬레이션 (1.5초 후 성공)
        setTimeout(() => {
            setIsLoading(false);
            localStorage.setItem('isAuthenticated', 'true'); // 인증 상태 저장
            // 이벤트를 발생시켜 상위 컴포넌트가 감지할 수 있게 함 (선택적)
            window.dispatchEvent(new Event('storage'));
            navigate('/'); // 메인으로 이동
        }, 1500);
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 p-4">
            <Card className="w-full max-w-md animate-in fade-in zoom-in duration-500 slide-in-from-bottom-4">
                <CardHeader className="text-center space-y-1">
                    <div className="mx-auto w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center mb-4">
                        <Lock className="w-6 h-6 text-indigo-600" />
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-slate-900">Welcome Back</h2>
                    <p className="text-sm text-slate-500">Enter your credentials to access the workspace</p>
                </CardHeader>

                <form onSubmit={handleLogin}>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <div className="relative">
                                <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                <Input id="email" type="email" placeholder="name@example.com" className="pl-10" />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="password">Password</Label>
                                <a href="#" className="text-xs text-indigo-600 hover:text-indigo-500 font-medium">Forgot password?</a>
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                <Input id="password" type="password" placeholder="••••••••" className="pl-10" />
                            </div>
                        </div>
                    </CardContent>

                    <CardFooter className="flex-col gap-4">
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? (
                                <span className="flex items-center gap-2">
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Signing in...
                                </span>
                            ) : (
                                <span className="flex items-center gap-2">
                                    Sign In <ArrowRight className="w-4 h-4" />
                                </span>
                            )}
                        </Button>

                        <div className="relative w-full">
                            <div className="absolute inset-0 flex items-center">
                                <span className="w-full border-t border-slate-200" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                                <span className="bg-white px-2 text-slate-500">Or continue with</span>
                            </div>
                        </div>

                        <Button variant="outline" type="button">
                            <Github className="mr-2 h-4 w-4" /> Github
                        </Button>

                        <p className="text-center text-sm text-slate-500 mt-2">
                            Don't have an account?{' '}
                            <a href="#" className="text-indigo-600 hover:text-indigo-500 font-medium hover:underline">
                                Sign up
                            </a>
                        </p>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
