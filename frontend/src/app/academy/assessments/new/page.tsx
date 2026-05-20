"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { 
    GraduationCap, 
    FilePlus, 
    Plus, 
    Trash2, 
    Save, 
    CheckCircle2,
    ListChecks,
} from 'lucide-react';
import { toast } from 'sonner';
import { DSCard } from '@/design/components/DSCard';
import clsx from 'clsx';

interface Question {
    id: string;
    type: 'multiple_choice' | 'true_false' | 'text';
    text: string;
    options: string[];
    correct_option?: number;
    points: number;
}

export default function NewAssessmentPage() {
    const router = useRouter();
    useAuth();
    
    const [title, setTitle] = useState('');
    const [passingScore, setPassingScore] = useState(70);
    const [questions, setQuestions] = useState<Question[]>([]);

    const addQuestion = () => {
        const newQuestion: Question = {
            id: Math.random().toString(36).substr(2, 9),
            type: 'multiple_choice',
            text: '',
            options: ['', ''],
            correct_option: 0,
            points: 10
        };
        setQuestions([...questions, newQuestion]);
    };

    const updateQuestion = (id: string, updates: Partial<Question>) => {
        setQuestions(questions.map(q => q.id === id ? { ...q, ...updates } : q));
    };

    const removeQuestion = (id: string) => {
        setQuestions(questions.filter(q => q.id !== id));
    };

    const handleSave = async () => {
        if (!title || questions.length === 0) {
            toast.error('Completa el título y agrega al menos una pregunta');
            return;
        }

        try {
            toast.success('Evaluación creada correctamente');
            router.back();
        } catch {
            toast.error('Error al guardar la evaluación');
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap },
                    { label: 'Nueva Evaluación', icon: FilePlus },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => router.back()}
                            className="px-4 py-2 text-slate-500 text-[10px] font-black uppercase tracking-widest hover:text-slate-700 transition-all"
                        >
                            Cancelar
                        </button>
                        <button 
                            onClick={handleSave}
                            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2"
                        >
                            <Save size={14} /> Guardar Evaluación
                        </button>
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
                <div className="max-w-4xl mx-auto space-y-3">
                    <DSCard>
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Configuración General</h3>
                        <div className="space-y-3">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Título de la Evaluación</label>
                                <input 
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Ej: Examen Final de Teología Básica"
                                    className="w-full bg-transparent border-b-2 border-slate-100 dark:border-white/5 py-1.5 text-lg font-black outline-none focus:border-blue-500 transition-all"
                                />
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Nota Mínima de Aprobación (%)</label>
                                    <input 
                                        type="number"
                                        value={passingScore}
                                        onChange={(e) => setPassingScore(Number(e.target.value))}
                                        className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-1.5 px-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10"
                                    />
                                </div>
                            </div>
                        </div>
                    </DSCard>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-black uppercase tracking-[0.3em] text-slate-400">Preguntas ({questions.length})</h3>
                            <button 
                                onClick={addQuestion}
                                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest hover:border-blue-500 transition-all"
                            >
                                <Plus size={14} /> Agregar Pregunta
                            </button>
                        </div>

                        {questions.map((q, index) => (
                            <DSCard key={q.id}>
                                <div className="space-y-3">
                                    <div className="flex items-start justify-between">
                                        <span className="size-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-black text-xs">
                                            {index + 1}
                                        </span>
                                        <button 
                                            onClick={() => removeQuestion(q.id)}
                                            className="text-slate-300 hover:text-rose-500 transition-colors"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>

                                    <div className="space-y-4">
                                        <textarea 
                                            value={q.text}
                                            onChange={(e) => updateQuestion(q.id, { text: e.target.value })}
                                            placeholder="Escribe la pregunta aquí..."
                                            className="w-full bg-transparent border-none text-sm font-bold outline-none resize-none placeholder:text-slate-300"
                                            rows={2}
                                        />

                                        <div className="grid grid-cols-1 gap-3">
                                            {q.options.map((opt, optIndex) => (
                                                <div key={optIndex} className="flex items-center gap-3 group">
                                                    <button 
                                                        onClick={() => updateQuestion(q.id, { correct_option: optIndex })}
                                                        className={clsx(
                                                            'size-6 rounded-lg flex items-center justify-center border-2 transition-all',
                                                            q.correct_option === optIndex 
                                                                ? 'bg-emerald-500 border-emerald-500 text-white' 
                                                                : 'border-slate-200 dark:border-white/10 text-transparent'
                                                        )}
                                                    >
                                                        <CheckCircle2 size={14} />
                                                    </button>
                                                    <input 
                                                        value={opt}
                                                        onChange={(e) => {
                                                            const newOpts = [...q.options];
                                                            newOpts[optIndex] = e.target.value;
                                                            updateQuestion(q.id, { options: newOpts });
                                                        }}
                                                        placeholder={`Opción ${optIndex + 1}`}
                                                        className="flex-1 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl py-2 px-4 text-sm outline-none focus:border-blue-500 transition-all"
                                                    />
                                                </div>
                                            ))}
                                            <button 
                                                onClick={() => {
                                                    updateQuestion(q.id, { options: [...q.options, ''] });
                                                }}
                                                className="text-[10px] font-black uppercase tracking-widest text-blue-500 mt-2 hover:underline text-left"
                                            >
                                                + Agregar opción
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </DSCard>
                        ))}

                        {questions.length === 0 && (
                            <div className="p-20 text-center border-2 border-dashed border-slate-200 dark:border-white/10 rounded-xl">
                                <ListChecks size={48} className="mx-auto text-slate-200 mb-4" />
                                <p className="text-xs font-black uppercase tracking-widest text-slate-400">Tu evaluación está vacía</p>
                                <p className="text-[11px] text-slate-300 mt-2">Comienza agregando tu primera pregunta</p>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
