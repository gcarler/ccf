"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { ArrowLeft, BookOpen, Upload, CreditCard, Wallet, Landmark, Lock, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

export default function EnrollmentWizard({ params }: { params: { id: string } }) {
    const { token, isAuthenticated, user } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [step, setStep] = useState(1);
    const [course, setCourse] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [enrolling, setEnrolling] = useState(false);
    const [paymentMethod, setPaymentMethod] = useState('card');

    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/login');
            return;
        }

        const fetchCourse = async () => {
            try {
                // Since there isn't a single course GET endpoint, we'll fetch all and find it
                const response = await fetch(apiUrl('/courses/?modality=formal'), { cache: 'no-store' });
                const informalRes = await fetch(apiUrl('/courses/?modality=no_formal'), { cache: 'no-store' });

                const dataFormal = await response.ok ? await response.json() : [];
                const dataInformal = await informalRes.ok ? await informalRes.json() : [];

                const allCourses = [...dataFormal, ...dataInformal];
                const found = allCourses.find(c => c.id.toString() === params.id);

                if (found) {
                    setCourse(found);
                } else {
                    addToast("Curso no encontrado", "error");
                    router.push('/academy');
                }
            } catch (error) {
                addToast("Error al cargar detalles del curso", "error");
            } finally {
                setLoading(false);
            }
        };

        fetchCourse();
    }, [isAuthenticated, params.id, router, addToast]);

    const handleEnrollment = async () => {
        setEnrolling(true);
        try {
            const response = await fetch(apiUrl("/enrollments/"), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ user_id: user?.id, course_id: parseInt(params.id) }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                addToast(errorData.detail || "No se pudo realizar la inscripción.", "error");
                setEnrolling(false);
                return;
            }

            addToast("¡Inscripción y pago exitosos!", "success");
            setStep(3); // Success step
        } catch (error) {
            addToast("Error de conexión.", "error");
            setEnrolling(false);
        }
    };

    if (loading) {
        return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Loader2 className="animate-spin text-primary w-12 h-12" /></div>;
    }

    if (!course) return null;

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative">
            {/* Background elements */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative flex flex-col min-h-screen w-full max-w-lg mx-auto overflow-hidden">
                {/* TopAppBar */}
                <div className="flex items-center px-6 pt-8 pb-4 justify-between sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
                    <button onClick={() => router.back()} className="text-primary flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 hover:bg-primary/20 transition-colors">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center">
                        {step === 1 ? 'Inscripción a Carrera' : step === 2 ? 'Pago de Matrícula' : 'Inscripción Exitosa'}
                    </h2>
                    <div className="size-10"></div>
                </div>

                {/* Progress Steps Indicator */}
                <div className="px-6 mt-6">
                    <div className="flex justify-between items-center bg-white/5 p-3 rounded-2xl border border-white/5 shadow-inner">
                        <div className={`flex flex-col items-center flex-1 transition-opacity ${step >= 1 ? 'opacity-100' : 'opacity-40'}`}>
                            <span className={`font-bold text-[10px] uppercase tracking-widest ${step >= 1 ? 'text-primary' : 'text-slate-500'}`}>Requisitos</span>
                            <div className={`h-1.5 w-1.5 rounded-full mt-2 transition-colors ${step >= 1 ? 'bg-primary shadow-[0_0_8px_rgba(66,66,240,0.8)]' : 'bg-slate-700'}`}></div>
                        </div>
                        <div className={`flex flex-col items-center flex-1 transition-opacity ${step >= 2 ? 'opacity-100' : 'opacity-40'}`}>
                            <span className={`font-bold text-[10px] uppercase tracking-widest ${step >= 2 ? 'text-primary' : 'text-slate-500'}`}>Pago</span>
                            <div className={`h-1.5 w-1.5 rounded-full mt-2 transition-colors ${step >= 2 ? 'bg-primary shadow-[0_0_8px_rgba(66,66,240,0.8)]' : 'bg-slate-700'}`}></div>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto pb-32">
                    {/* STEP 1: Info & Documents */}
                    {step === 1 && (
                        <div className="animate-in fade-in slide-in-from-right-8 duration-500">
                            {/* Hero Section */}
                            <div className="px-6 py-6">
                                <div className="relative bg-primary rounded-[2rem] overflow-hidden min-h-[220px] shadow-2xl shadow-primary/20 flex flex-col justify-end p-8 border border-white/10 group">
                                    <div className="absolute top-6 right-6 text-white/10 group-hover:scale-110 transition-transform duration-700">
                                        <BookOpen size={100} strokeWidth={1} />
                                    </div>
                                    <div className="z-10 relative">
                                        <span className="bg-white/20 backdrop-blur-md text-white border border-white/10 text-[10px] uppercase tracking-widest font-bold px-3 py-1.5 rounded-lg mb-3 inline-block shadow-sm">
                                            {course.modality === 'formal' ? 'Ruta Formal' : 'Ruta No Formal'}
                                        </span>
                                        <h1 className="text-white text-3xl font-black leading-tight tracking-tight drop-shadow-md">{course.title}</h1>
                                        <p className="text-primary-100 mt-2 text-sm font-medium">{course.code}</p>
                                    </div>
                                    <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/80 to-transparent mix-blend-multiply"></div>
                                </div>
                            </div>

                            {/* Curriculum Glass Card */}
                            <div className="px-6 mb-8">
                                <div className="bg-slate-900/50 backdrop-blur-xl rounded-3xl p-6 shadow-xl border border-white/10">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-2.5 bg-primary/20 rounded-xl text-primary border border-primary/20">
                                            <BookOpen size={20} />
                                        </div>
                                        <h3 className="font-bold text-white text-lg tracking-tight">Resumen del Curso</h3>
                                    </div>
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center text-sm">
                                            <span className="text-slate-400 font-medium">Duración</span>
                                            <span className="font-bold text-slate-200">{course.duration_hours} Horas</span>
                                        </div>
                                        <div className="flex justify-between items-center text-sm border-t border-white/5 pt-4">
                                            <span className="text-slate-400 font-medium">Modalidad</span>
                                            <span className="font-bold text-slate-200">{course.is_self_paced ? 'Autoguiado' : 'Con cohorte'}</span>
                                        </div>
                                        {course.description && (
                                            <p className="text-xs text-slate-400 leading-relaxed mt-4 pt-4 border-t border-white/5 text-justify">
                                                {course.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Document Attachment Section (Mock UI to match Stitch) */}
                            {course.modality === 'formal' && (
                                <div className="px-6 mb-8">
                                    <h3 className="text-xs font-black text-slate-300 uppercase tracking-widest mb-4 ml-1">Adjuntar Documentos</h3>
                                    <div className="grid grid-cols-1 gap-3">
                                        <button className="flex items-center justify-between p-5 bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-white/5 shadow-sm hover:border-primary/30 transition-colors group">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-white/5 rounded-xl text-slate-300 group-hover:text-primary transition-colors">
                                                    <CreditCard size={20} />
                                                </div>
                                                <div className="text-left">
                                                    <p className="text-sm font-bold text-slate-200">Identificación Oficial</p>
                                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">DNI, Cédula o Pasaporte</p>
                                                </div>
                                            </div>
                                            <Upload size={20} className="text-slate-500 group-hover:text-primary transition-colors" />
                                        </button>
                                        <button className="flex items-center justify-between p-5 bg-slate-900/50 backdrop-blur-xl rounded-2xl border border-white/5 shadow-sm hover:border-primary/30 transition-colors group">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-white/5 rounded-xl text-slate-300 group-hover:text-primary transition-colors">
                                                    <BookOpen size={20} />
                                                </div>
                                                <div className="text-left">
                                                    <p className="text-sm font-bold text-slate-200">Estudios Previos</p>
                                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-1">Título de secundaria o equivalente</p>
                                                </div>
                                            </div>
                                            <Upload size={20} className="text-slate-500 group-hover:text-primary transition-colors" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* STEP 2: Payment */}
                    {step === 2 && (
                        <div className="animate-in fade-in slide-in-from-right-8 duration-500 pb-8">
                            {/* Summary Card */}
                            <div className="p-6">
                                <div className="flex flex-col rounded-[2.5rem] shadow-2xl bg-slate-900/80 backdrop-blur-xl overflow-hidden border border-white/10 group">
                                    <div className="w-full h-32 bg-primary/20 relative overflow-hidden flex items-center justify-center">
                                        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent z-10"></div>
                                        <BookOpen className="w-16 h-16 text-primary opacity-50 absolute right-4 -top-4 -rotate-12 transform group-hover:rotate-0 transition-transform duration-700" strokeWidth={1} />
                                    </div>
                                    <div className="flex w-full flex-col p-8 -mt-16 z-20">
                                        <p className="text-primary font-black text-[10px] uppercase tracking-widest drop-shadow-md bg-slate-900 px-3 py-1 rounded-full w-fit mb-4 border border-primary/20">Resumen Académico</p>
                                        <p className="text-white text-2xl font-black leading-tight tracking-tight">{course.title}</p>
                                        <div className="flex items-center justify-between mt-6 pt-6 border-t border-white/10">
                                            <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">Total de Inscripción</p>
                                            <p className="text-primary text-2xl font-black drop-shadow-md">{course.modality === 'formal' ? '$250.00' : 'Gratis'} <span className="text-sm">USD</span></p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {course.modality === 'formal' ? (
                                <>
                                    {/* Payment Methods */}
                                    <div className="px-6 py-4">
                                        <h3 className="text-white text-base font-bold leading-tight tracking-tight mb-4">Métodos de Pago</h3>
                                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-3xl p-3 flex flex-col gap-3 border border-white/5">
                                            <label className="flex items-center gap-4 rounded-2xl p-4 flex-row-reverse cursor-pointer transition-all hover:bg-slate-800/50 border border-transparent has-[:checked]:border-primary/50 has-[:checked]:bg-primary/10">
                                                <input defaultChecked name="payment-method" type="radio" value="card" onChange={(e) => setPaymentMethod(e.target.value)} className="h-5 w-5 border-2 border-slate-600 bg-transparent text-primary focus:ring-primary focus:ring-offset-0 checked:border-primary appearance-none rounded-full checked:bg-primary checked:ring-2 checked:ring-primary/20" />
                                                <div className="flex grow items-center gap-4">
                                                    <div className="size-12 rounded-xl bg-primary/20 flex items-center justify-center text-primary shadow-inner">
                                                        <CreditCard size={24} />
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <p className="text-white text-sm font-bold">Tarjeta de Crédito / Débito</p>
                                                        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mt-1">Visa, Mastercard, AMEX</p>
                                                    </div>
                                                </div>
                                            </label>
                                            <label className="flex items-center gap-4 rounded-2xl p-4 flex-row-reverse cursor-pointer transition-all hover:bg-slate-800/50 border border-transparent has-[:checked]:border-primary/50 has-[:checked]:bg-primary/10">
                                                <input name="payment-method" type="radio" value="paypal" onChange={(e) => setPaymentMethod(e.target.value)} className="h-5 w-5 border-2 border-slate-600 bg-transparent text-primary focus:ring-primary focus:ring-offset-0 checked:border-primary appearance-none rounded-full checked:bg-primary checked:ring-2 checked:ring-primary/20" />
                                                <div className="flex grow items-center gap-4">
                                                    <div className="size-12 rounded-xl bg-blue-500/20 flex items-center justify-center text-blue-400 shadow-inner">
                                                        <Wallet size={24} />
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <p className="text-white text-sm font-bold">PayPal</p>
                                                        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mt-1">Procesamiento instantáneo</p>
                                                    </div>
                                                </div>
                                            </label>
                                            <label className="flex items-center gap-4 rounded-2xl p-4 flex-row-reverse cursor-pointer transition-all hover:bg-slate-800/50 border border-transparent has-[:checked]:border-primary/50 has-[:checked]:bg-primary/10">
                                                <input name="payment-method" type="radio" value="bank" onChange={(e) => setPaymentMethod(e.target.value)} className="h-5 w-5 border-2 border-slate-600 bg-transparent text-primary focus:ring-primary focus:ring-offset-0 checked:border-primary appearance-none rounded-full checked:bg-primary checked:ring-2 checked:ring-primary/20" />
                                                <div className="flex grow items-center gap-4">
                                                    <div className="size-12 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-inner">
                                                        <Landmark size={24} />
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <p className="text-white text-sm font-bold">Transferencia Bancaria</p>
                                                        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mt-1">Banco Nacional, BAC</p>
                                                    </div>
                                                </div>
                                            </label>
                                        </div>
                                    </div>

                                    {/* Card Details (Mock) */}
                                    {paymentMethod === 'card' && (
                                        <div className="px-6 py-4 flex flex-col gap-5 animate-in fade-in slide-in-from-top-4">
                                            <h3 className="text-white text-base font-bold leading-tight tracking-tight">Detalles de la Tarjeta</h3>
                                            <div className="flex flex-col gap-4">
                                                <div className="flex flex-col gap-2">
                                                    <label className="text-[10px] font-black tracking-widest uppercase text-slate-400 ml-1">Nombre en la Tarjeta</label>
                                                    <input type="text" placeholder="Ej. Juan Pérez" className="w-full px-5 py-4 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-white/10 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 text-white font-medium" />
                                                </div>
                                                <div className="flex flex-col gap-2">
                                                    <label className="text-[10px] font-black tracking-widest uppercase text-slate-400 ml-1">Número de Tarjeta</label>
                                                    <div className="relative">
                                                        <input type="text" placeholder="0000 0000 0000 0000" className="w-full px-5 py-4 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-white/10 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 text-white font-medium tracking-widest" />
                                                        <div className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-500">
                                                            <Lock size={20} />
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="flex flex-col gap-2">
                                                        <label className="text-[10px] font-black tracking-widest uppercase text-slate-400 ml-1">Vencimiento</label>
                                                        <input type="text" placeholder="MM/YY" className="w-full px-5 py-4 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-white/10 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 text-white font-medium tracking-widest" />
                                                    </div>
                                                    <div className="flex flex-col gap-2">
                                                        <label className="text-[10px] font-black tracking-widest uppercase text-slate-400 ml-1">CVV</label>
                                                        <input type="password" placeholder="***" className="w-full px-5 py-4 bg-slate-900/50 backdrop-blur-md rounded-2xl border border-white/10 focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-slate-600 text-white font-medium tracking-widest" />
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Security Badge */}
                                            <div className="flex items-center justify-center gap-2 py-4 px-4 bg-emerald-500/5 rounded-2xl border border-emerald-500/10 mt-2">
                                                <CheckCircle2 className="text-emerald-500" size={16} />
                                                <p className="text-[10px] text-emerald-400/80 uppercase tracking-widest font-black">Pago Seguro Encriptado SSL 256-bit</p>
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="px-6 py-12 text-center text-slate-400 animate-in fade-in">
                                    <div className="w-20 h-20 bg-emerald-500/10 text-emerald-500 rounded-full mx-auto flex items-center justify-center mb-6">
                                        <CheckCircle2 size={40} />
                                    </div>
                                    <p className="text-lg font-bold text-white mb-2 tracking-tight">Registro Gratuito</p>
                                    <p className="text-sm">Al continuar, quedarás inscrito automáticamente en este curso de liderazgo.</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* STEP 3: Success */}
                    {step === 3 && (
                        <div className="animate-in zoom-in-95 duration-500 flex flex-col items-center justify-center h-full pt-12 text-center px-6">
                            <div className="relative">
                                <div className="absolute inset-0 bg-emerald-500/20 blur-2xl rounded-full"></div>
                                <div className="w-32 h-32 bg-emerald-500 rounded-[2.5rem] flex items-center justify-center mx-auto mb-8 shadow-2xl shadow-emerald-500/40 border border-emerald-400 rotate-6 transform hover:rotate-0 transition-transform relative z-10">
                                    <CheckCircle2 size={64} className="text-white" strokeWidth={2.5} />
                                </div>
                            </div>
                            <h2 className="text-4xl font-black text-white mb-4 tracking-tight leading-tight">¡Inscripción Exitosa!</h2>
                            <p className="text-slate-400 mb-10 max-w-sm text-lg leading-relaxed">
                                Ya eres parte de <span className="text-white font-bold">{course.title}</span>. Prepárate para iniciar este nuevo ciclo de aprendizaje.
                            </p>
                            <button
                                onClick={() => router.push('/academy')}
                                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-5 rounded-2xl shadow-xl transition-all border border-white/10 active:scale-95 text-sm uppercase tracking-widest flex items-center justify-center gap-3"
                            >
                                Ir a Mis Cursos <BookOpen size={18} />
                            </button>
                        </div>
                    )}
                </div>

                {/* Floating Bottom Button */}
                {step < 3 && (
                    <div className="fixed bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent z-40">
                        <div className="max-w-lg mx-auto">
                            <button
                                onClick={() => {
                                    if (step === 1) setStep(2);
                                    else if (step === 2) handleEnrollment();
                                }}
                                disabled={enrolling}
                                className="w-full bg-primary text-white py-5 rounded-2xl font-black uppercase tracking-widest text-sm shadow-[0_0_40px_rgba(66,66,240,0.4)] flex items-center justify-center gap-3 active:scale-[0.98] transition-all hover:bg-primary/90 disabled:opacity-70 disabled:active:scale-100"
                            >
                                {enrolling ? (
                                    <><Loader2 className="animate-spin w-5 h-5" /> Procesando pago...</>
                                ) : (
                                    <>
                                        {step === 1 ? 'Continuar al Pago' : 'Finalizar Inscripción'}
                                        <ArrowRight size={18} />
                                    </>
                                )}
                            </button>
                            {step === 2 && course.modality === 'formal' && (
                                <p className="text-center text-[9px] font-black uppercase tracking-wider text-slate-500 mt-5 px-6 pb-2">
                                    Al hacer clic en &quot;Finalizar&quot;, aceptas nuestros <span className="text-primary cursor-pointer hover:underline">Términos</span> y <span className="text-primary cursor-pointer hover:underline">Políticas</span>.
                                </p>

                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
