"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, ArrowRight, ShieldCheck, Eye, EyeOff, Sparkles, Command } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const { login, isAuthenticated, user } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (isAuthenticated && user?.role) {
            const role = user.role.toLowerCase();
            if (["admin", "coordinador", "docente"].includes(role)) {
                router.push('/admin');
            } else {
                router.push('/academy');
            }
        }
    }, [isAuthenticated, user, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const response = await apiFetch<any>('/auth/login', {
                method: 'POST',
                body: formData,
            });
            
            if (response.access_token) {
                await login(response.access_token);
            } else {
                setError('No se recibió el token de acceso.');
            }
        } catch (err: any) {
            console.error('[LOGIN ERROR]', err);
            setError('Credenciales incorrectas o problema de conexión.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen w-full flex items-center justify-center bg-[#f1f5f9] dark:bg-[#0f172a] p-4 md:p-8 font-sans transition-colors duration-500">
            <style jsx>{`
                .app-card {
                    display: flex;
                    width: 100%;
                    max-width: 1280px;
                    height: 820px;
                    background: white;
                    border-radius: 4.5rem;
                    overflow: hidden;
                    box-shadow: 
                        0 40px 80px -15px rgba(0, 27, 72, 0.2),
                        0 20px 40px -10px rgba(0, 0, 0, 0.1);
                    position: relative;
                }

                .visual-panel {
                    flex: 1.4;
                    background: linear-gradient(145deg, #004581, #001b48);
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    padding: 90px;
                    overflow: hidden;
                }

                .form-panel {
                    flex: 1;
                    padding: 90px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    background: white;
                    position: relative;
                    z-index: 10;
                }

                .lighthouse-flare {
                    position: absolute;
                    top: -10%;
                    right: -10%;
                    width: 120%;
                    height: 120%;
                    background: radial-gradient(circle at 75% 25%, rgba(1, 138, 189, 0.4) 0%, transparent 70%);
                    z-index: 1;
                    pointer-events: none;
                }

                .lighthouse-beam-rotate {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 400%;
                    height: 400%;
                    background: conic-gradient(
                        from 180deg at 50% 50%,
                        transparent 0deg,
                        rgba(221, 232, 240, 0.08) 8deg,
                        rgba(221, 232, 240, 0.12) 10deg,
                        rgba(221, 232, 240, 0.08) 12deg,
                        transparent 20deg
                    );
                    animation: rotate-beam 25s linear infinite;
                    z-index: 0;
                }

                @keyframes rotate-beam {
                    from { transform: translate(-50%, -50%) rotate(0deg); }
                    to { transform: translate(-50%, -50%) rotate(360deg); }
                }

                .input-pro {
                    background-color: #f8fafc;
                    border: 2px solid #f1f5f9;
                    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
                }

                .input-pro:focus {
                    background-color: white;
                    border-color: #018abd;
                    outline: none;
                    box-shadow: 0 10px 25px -5px rgba(1, 138, 189, 0.15);
                    transform: translateY(-2px);
                }

                .btn-submit {
                    background: linear-gradient(135deg, #018abd, #006da1);
                    transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
                    font-weight: 800;
                    position: relative;
                    overflow: hidden;
                }

                .btn-submit:hover {
                    transform: translateY(-3px) scale(1.01);
                    box-shadow: 0 25px 50px -12px rgba(1, 138, 189, 0.5);
                }

                .btn-submit::after {
                    content: '';
                    position: absolute;
                    top: -50%;
                    left: -60%;
                    width: 20%;
                    height: 200%;
                    background: rgba(255, 255, 255, 0.2);
                    transform: rotate(30deg);
                    transition: all 0.6s;
                }

                .btn-submit:hover::after {
                    left: 120%;
                }

                .title-heavy {
                    font-weight: 900;
                    letter-spacing: -0.06em;
                    line-height: 0.75;
                    text-shadow: 0 20px 40px rgba(0,0,0,0.2);
                }

                .grain-overlay {
                    position: absolute;
                    inset: 0;
                    background-image: url("https://grainy-gradients.vercel.app/noise.svg");
                    opacity: 0.05;
                    pointer-events: none;
                    z-index: 2;
                }

                @media (max-width: 1200px) {
                    .visual-panel { padding: 60px; }
                    .form-panel { padding: 60px; }
                }

                @media (max-width: 1100px) {
                    .app-card { height: auto; min-height: 600px; flex-direction: column; border-radius: 3rem; }
                    .visual-panel { display: none; }
                    .form-panel { padding: 80px 40px; flex: 1; }
                }
            `}</style>

            <motion.div 
                initial={{ opacity: 0, y: 40, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
                className="app-card"
            >
                {/* SECCIÓN IZQUIERDA: IDENTIDAD */}
                <section className="visual-panel">
                    <div className="lighthouse-flare"></div>
                    <div className="lighthouse-beam-rotate"></div>
                    <div className="grain-overlay"></div>

                    {/* Logo Superior */}
                    <motion.div 
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.5 }}
                        className="relative z-10"
                    >
                        <div className="inline-flex items-center gap-4 bg-white/10 backdrop-blur-2xl p-4 rounded-[2rem] border border-white/20 shadow-2xl">
                            <div className="size-10 rounded-2xl bg-white/10 flex items-center justify-center">
                                <Command size={20} className="text-white" />
                            </div>
                            <span className="text-white font-black uppercase tracking-[0.4em] text-[10px]">CCF MESH SYSTEM</span>
                        </div>
                    </motion.div>

                    {/* Título Principal Masivo */}
                    <div className="relative z-10">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.7 }}
                        >
                            <h1 className="text-[10rem] title-heavy text-white uppercase select-none">EL <br /> FARO</h1>
                            <div className="flex items-center gap-6 mt-8">
                                <p className="text-[#018abd] text-3xl font-black tracking-[0.4em] uppercase">
                                    COMUNIDAD <br /> CRISTIANA
                                </p>
                                <div className="h-16 w-1.5 bg-white/20 rounded-full"></div>
                            </div>
                        </motion.div>
                    </div>

                    {/* Footer Visual */}
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1 }}
                        className="relative z-10 flex items-end justify-between"
                    >
                        <div>
                            <p className="text-blue-100/50 text-sm font-bold uppercase tracking-[0.2em] leading-relaxed">
                                Transformando vidas <br /> a través de la luz de Cristo.
                            </p>
                        </div>
                        <div className="flex items-center gap-2 text-white/20">
                            <Sparkles size={16} />
                            <span className="text-[10px] font-black uppercase tracking-widest">Global Outreach</span>
                        </div>
                    </motion.div>

                    {/* Mapa Decorativo */}
                    <svg className="absolute bottom-[-15%] left-[-15%] w-[130%] h-auto opacity-10 text-white pointer-events-none" viewBox="0 0 800 400" fill="currentColor">
                        <path d="M100,100c50,0,100,50,150,50s100-50,150-50s100,50,150,50s100-50,150-50v300H0V100z" />
                    </svg>
                </section>

                {/* SECCIÓN DERECHA: FORMULARIO */}
                <section className="form-panel">
                    <div className="w-full max-w-md mx-auto">
                        {/* Header */}
                        <div className="mb-14">
                            <motion.h2 
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.4 }}
                                className="text-6xl font-black text-[#001b48] tracking-tighter mb-4"
                            >
                                Hola de nuevo
                            </motion.h2>
                            <motion.p 
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.5 }}
                                className="text-slate-400 font-black uppercase tracking-[0.3em] text-[11px] ml-1"
                            >
                                Identidad Ministerial · Acceso Único
                            </motion.p>
                        </div>

                        {/* Formulario Principal */}
                        <form className="space-y-8" onSubmit={handleSubmit}>
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.6 }}
                            >
                                <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest mb-4 block ml-2">Email del Ministerio</label>
                                <input 
                                    type="text" 
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="usuario@ministeriofaro.org" 
                                    className="w-full input-pro py-6 px-8 rounded-[2.2rem] text-[#001b48] font-bold text-lg placeholder:text-slate-300"
                                />
                            </motion.div>

                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.7 }}
                            >
                                <div className="flex justify-between items-center mb-4 ml-2">
                                    <label className="text-[11px] font-black text-slate-400 uppercase tracking-widest block">Contraseña Maestra</label>
                                    <Link href="#" className="text-[10px] text-[#018abd] font-black hover:text-[#001b48] transition-colors uppercase tracking-widest">¿Ayuda con el acceso?</Link>
                                </div>
                                <div className="relative group">
                                    <input 
                                        type={showPassword ? "text" : "password"} 
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="••••••••" 
                                        className="w-full input-pro py-6 px-8 rounded-[2.2rem] text-[#001b48] font-bold text-lg placeholder:text-slate-300"
                                    />
                                    <button 
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-6 top-1/2 -translate-y-1/2 text-slate-300 hover:text-[#018abd] transition-colors"
                                    >
                                        {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                                    </button>
                                </div>
                            </motion.div>

                            <AnimatePresence>
                                {error && (
                                    <motion.div 
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        className="p-5 bg-rose-50 border-2 border-rose-100 rounded-3xl text-rose-600 text-xs font-black text-center uppercase tracking-widest"
                                    >
                                        {error}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Botón Ingresar */}
                            <motion.button 
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.8 }}
                                type="submit" 
                                disabled={loading}
                                className="btn-submit w-full py-7 rounded-[2.5rem] text-white text-sm font-black uppercase tracking-[0.5em] flex items-center justify-center gap-4 active:scale-95 disabled:opacity-50"
                            >
                                {loading ? (
                                    <Loader2 className="animate-spin" size={24} />
                                ) : (
                                    <>
                                        INGRESAR AHORA
                                        <ArrowRight size={20} className="stroke-[3]" />
                                    </>
                                )}
                            </motion.button>
                        </form>

                        {/* Separador */}
                        <div className="relative my-12">
                            <div className="absolute inset-0 flex items-center"><div className="w-full border-t-2 border-slate-50"></div></div>
                            <div className="relative flex justify-center text-[10px] font-black uppercase tracking-[0.4em] text-slate-300">
                                <span className="bg-white px-8">Identidad Digital</span>
                            </div>
                        </div>

                        {/* Google Auth */}
                        <motion.button 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.9 }}
                            type="button" 
                            className="w-full flex items-center justify-center gap-4 border-2 border-slate-100 py-5 rounded-[2rem] font-black text-slate-500 hover:bg-slate-50 hover:border-slate-200 transition-all text-[11px] tracking-[0.2em] uppercase mb-12"
                        >
                            <svg className="w-6 h-6" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Continuar con Google
                        </motion.button>

                        {/* Footer del Formulario */}
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 1 }}
                            className="text-center"
                        >
                            <p className="text-slate-400 text-[11px] font-bold tracking-widest uppercase mb-4">
                                ¿Nuevo en el ecosistema digital?
                            </p>
                            <Link href="/register" className="text-[#018abd] font-black text-[11px] uppercase tracking-[0.3em] border-b-2 border-transparent hover:border-current transition-all pb-1">
                                Solicitar Registro Ministerial
                            </Link>
                        </motion.div>
                    </div>
                </section>
            </motion.div>

            {/* Floating Security Badge */}
            <div className="fixed bottom-10 right-10 flex items-center gap-3 bg-white dark:bg-slate-900 px-6 py-3 rounded-full shadow-xl border border-slate-100 dark:border-slate-800 z-50">
                <ShieldCheck size={16} className="text-[#018abd]" />
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em]">Identity Secure · MESH v2.2</span>
            </div>
        </div>
    );
}
