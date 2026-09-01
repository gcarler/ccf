"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import {
    ChevronLeft,
    Heart,
    CreditCard,
    Building,
    ShieldCheck,
    Globe,
    CheckCircle2,
    Sparkles,
    HandHeart,
    Lock,
    Loader2,
    ExternalLink,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { useCmsV2Page } from '@/hooks/useCmsV2Page';
import { safeJsonParse } from '@/lib/safeJson';

export default function DonatePage() {
    const { user } = useAuth();
    const { addToast } = useToast();
    const cmsPage = useCmsV2Page('donate');
    const cmsHero = cmsPage?.blocks?.hero;
    const cmsFeed = cmsPage?.blocks?.feed;
    const hero = safeJsonParse<Record<string, unknown>>(cmsHero?.content, {});
    const feed = safeJsonParse<Record<string, unknown>>(cmsFeed?.content, {});

    if (!cmsPage) return null;

    // All editorial copy is owned by the CMS page sections.
    const str = (obj: Record<string, unknown>, key: string) =>
        typeof obj[key] === "string" ? (obj[key] as string) : "";

    // Header & hero
    const headerLabel = str(hero, "header_label");
    const heroBadge = str(hero, "badge");
    const heroTitle = str(hero, "title");
    const heroTitleAccent = str(hero, "title_accent");
    const heroTitleConnector = str(hero, "title_connector");
    const heroDescription = str(hero, "description");

    // Benefits
    const benefit1Title = str(hero, "benefit1_title");
    const benefit1Desc = str(hero, "benefit1_desc");
    const benefit2Title = str(hero, "benefit2_title");
    const benefit2Desc = str(hero, "benefit2_desc");

    // Amount & type selectors
    const amountsLabel = str(feed, "amounts_label");
    const customAmountLabel = str(feed, "custom_amount_label");
    const typeLabel = str(feed, "type_label");
    const diezmoValue = str(feed, "diezmo_value");
    const ofrendaValue = str(feed, "ofrenda_value");
    const diezmoLabel = str(feed, "diezmo_label");
    const ofrendaLabel = str(feed, "ofrenda_label");

    // Buttons
    const payButtonLabel = str(feed, "pay_button_label");
    const connectingLabel = str(feed, "connecting_label");
    const manualButtonLabel = str(feed, "manual_button_label");
    const manualDividerLabel = str(feed, "manual_divider_label");

    // Footer badges
    const sslLabel = str(feed, "ssl_label");
    const verifiedLabel = str(feed, "verified_label");

    // Success screen
    const successTitleApproved = str(feed, "success_title_approved");
    const successTitlePending = str(feed, "success_title_pending");
    const successDescApproved = str(feed, "success_desc_approved");
    const successDescPending = str(feed, "success_desc_pending");
    const amountLabel = str(feed, "amount_label");
    const categoryLabel = str(feed, "category_label");
    const backHomeLabel = str(feed, "back_home_label");

    // Toasts
    const toastSuccess = str(feed, "toast_success");
    const toastError = str(feed, "toast_error");
    const toastMpError = str(feed, "toast_mp_error");
    const toastMpPending = str(feed, "toast_mp_pending");
    const toastMpFailure = str(feed, "toast_mp_failure");

    // Amounts (editable from CMS)
    const AMOUNTS = Array.isArray(feed.amounts) ? (feed.amounts as string[]) : [];

    const [amount, setAmount] = useState(() => str(feed, "default_amount"));
    const [type, setType] = useState(() => diezmoValue);
    const [isCustom, setIsCustom] = useState(false);
    const [loading, setLoading] = useState(false);
    const [mpLoading, setMpLoading] = useState(false);
    const [completed, setCompleted] = useState(false);
    const [paymentStatus, setPaymentStatus] = useState<string | null>(null);

    // Handle return from MercadoPago (status in URL params)
    React.useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const status = params.get('status');
        if (status === 'success') {
            setCompleted(true);
            setPaymentStatus('approved');
        } else if (status === 'failure') {
            addToast(toastMpFailure, 'error');
        } else if (status === 'pending') {
            addToast(toastMpPending, 'warning');
            setCompleted(true);
            setPaymentStatus('pending');
        }
    }, [addToast, toastMpFailure, toastMpPending]);

    const handleManualDonation = async () => {
        setLoading(true);
        try {
            await apiFetch('/donations/', {
                method: 'POST',
                body: {
                    amount: parseFloat(amount),
                    donation_type: type,
                    donor_name: user?.username || "Anónimo"
                }
            });
            setCompleted(true);
            addToast(toastSuccess, "success");
        } catch (error) {
            console.error(error);
            addToast(toastError, "error");
        } finally {
            setLoading(false);
        }
    };

    const handleMercadoPago = async () => {
        setMpLoading(true);
        try {
            const pref = await apiFetch<{ id: string; init_point: string }>('/donations/mercadopago/create-preference', {
                method: 'POST',
                body: {
                    amount: parseFloat(amount),
                    title: type,
                    donor_name: user?.username || undefined,
                    email: user?.email || undefined,
                },
            });
            if (pref?.init_point) {
                window.location.href = pref.init_point;
            } else {
                addToast(toastMpError, 'error');
            }
        } catch (error: any) {
            const detail = error?.detail?.detail || error?.message;
            addToast(detail || toastMpError, 'error');
        } finally {
            setMpLoading(false);
        }
    };

    if (completed) {
        const isApproved = paymentStatus === 'approved' || !paymentStatus;
        return (
            <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] flex items-center justify-center p-3">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                    className="max-w-md w-full text-center space-y-3 p-4 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-2xl"
                >
                    <div className={`size-10 rounded-full mx-auto flex items-center justify-center shadow-lg ${isApproved ? 'bg-[hsl(var(--success))]' : 'bg-[hsl(var(--warning))]'}`}>
                        {isApproved ? <CheckCircle2 size={48} /> : <Sparkles size={48} />}
                    </div>
                    <div className="space-y-3">
                        <h2 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">
                            {isApproved ? successTitleApproved : successTitlePending}
                        </h2>
                        <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">
                            {isApproved
                                ? successDescApproved
                                : successDescPending}
                        </p>
                    </div>
                    <div className="py-2 border-y border-[hsl(var(--border))] dark:border-white/10 flex justify-between items-center px-4">
                        <div className="text-left">
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{amountLabel}</p>
                            <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">${amount}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{categoryLabel}</p>
                            <p className="text-sm font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{type}</p>
                        </div>
                    </div>
                    <Link href="/" className="block w-full py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-bold text-sm uppercase tracking-wide active:scale-95 transition-all shadow-xl">
                        {backHomeLabel}
                    </Link>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] relative overflow-hidden flex flex-col items-center">
            {/* Decorative backgrounds */}
            <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] opacity-10 dark:opacity-20 pointer-events-none" />
            <div className="absolute top-[-10%] right-[-10%] size-96 bg-[hsl(var(--primary))] rounded-full blur-[120px] opacity-10 animate-pulse" />

            <header className="w-full max-w-5xl px-3 pt-12 flex items-center justify-between relative z-10">
                <Link href="/" className="size-7 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm">
                    <ChevronLeft size={24} />
                </Link>
                <div className="flex flex-col items-center">
                    <h1 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{headerLabel}</h1>
                    <div className="h-1 w-8 bg-[hsl(var(--primary))] rounded-full mt-1" />
                </div>
                <div className="size-7" />
            </header>

            <main className="w-full max-w-5xl px-3 py-1.5 grid grid-cols-1 lg:grid-cols-2 gap-3 relative z-10 items-start">
                {/* Left Side: Inspiration */}
                <div className="space-y-3 pt-4">
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-info-soft dark:bg-[hsl(var(--info))]/30 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-full text-2xs font-bold uppercase tracking-wide">
                        <HandHeart size={14} /> {heroBadge}
                    </div>
                    <h2 className="text-lg lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-[0.9]">
                        {heroTitle} <br /> {heroTitleConnector} <br /> <span className="text-[hsl(var(--primary))]">{heroTitleAccent}</span>
                    </h2>
                    <p className="text-lg text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-md leading-relaxed">
                        {heroDescription}
                    </p>

                    <div className="grid grid-cols-1 gap-4 pt-4">
                        <BenefitCard icon={ShieldCheck} title={benefit1Title} desc={benefit1Desc} />
                        <BenefitCard icon={Globe} title={benefit2Title} desc={benefit2Desc} />
                    </div>
                </div>

                {/* Right Side: Action Card */}
                <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.1)] dark:shadow-black/50 space-y-3">
                    {/* Amount Selector */}
                    <div className="space-y-3">
                        <div className="text-center">
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-4">{amountsLabel}</p>
                            <div className="flex items-center justify-center gap-2">
                                <span className="text-lg font-bold text-[hsl(var(--text-secondary))]">$</span>
                                {isCustom ? (
                                    <input
                                        type="number" autoFocus value={amount} onChange={(e) => setAmount(e.target.value)}
                                        className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white bg-transparent w-48 text-center outline-none tracking-tighter"
                                    />
                                ) : (
                                    <span className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter">{amount}</span>
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-4 gap-3">
                            {AMOUNTS.map(val => (
                                <button
                                    key={val} onClick={() => { setAmount(val); setIsCustom(false); }}
                                    className={clsx(
                                        "py-1.5 rounded-lg font-bold text-sm transition-all",
                                        amount === val && !isCustom
                                            ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-[hsl(var(--info)/30%)] scale-105"
                                            : "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
                                    )}
                                >
                                    ${val}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={() => setIsCustom(true)}
                            className={clsx(
                                "w-full py-1.5 rounded-lg font-bold text-2xs uppercase tracking-wide transition-all border-2",
                                isCustom ? "border-[hsl(var(--info)/100%)] bg-info-soft/50 dark:bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))]" : "border-transparent bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))]"
                            )}
                        >
                            {customAmountLabel}
                        </button>
                    </div>

                    {/* Type Selector */}
                    <div className="space-y-4">
                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-center">{typeLabel}</p>
                        <div className="grid grid-cols-2 gap-3">
                            <TypeOption active={type === diezmoValue} onClick={() => setType(diezmoValue)} icon={Building} label={diezmoLabel} />
                            <TypeOption active={type === ofrendaValue} onClick={() => setType(ofrendaValue)} icon={Heart} label={ofrendaLabel} />
                        </div>
                    </div>

                    {/* Submit — MercadoPago */}
                    <button
                        onClick={handleMercadoPago}
                        disabled={mpLoading || !amount || parseFloat(amount) <= 0}
                        className="w-full py-2.5 bg-[hsl(var(--primary))] text-white rounded-lg font-bold text-sm uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/30%)] active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-[hsl(var(--primary))]"
                    >
                        {mpLoading ? (
                            <><Loader2 size={18} className="animate-spin" /> {connectingLabel}</>
                        ) : (
                            <><ExternalLink size={18} /> {payButtonLabel}</>
                        )}
                    </button>

                    {/* Manual registration (admin only) */}
                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-[hsl(var(--border))] dark:border-white/5" />
                        </div>
                        <div className="relative flex justify-center">
                            <span className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] px-3 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                {manualDividerLabel}
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={handleManualDonation}
                        disabled={loading || !amount || parseFloat(amount) <= 0}
                        className="w-full py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-lg font-bold text-xs uppercase tracking-wide active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10"
                    >
                        {loading ? <Loader2 size={16} className="animate-spin" /> : <><CreditCard size={16} /> {manualButtonLabel}</>}
                    </button>

                    <div className="flex items-center justify-center gap-4 pt-4 border-t border-[hsl(var(--border))] dark:border-white/5 opacity-40">
                        <div className="flex items-center gap-1"><Lock size={12} /><span className="text-2xs font-semibold uppercase">{sslLabel}</span></div>
                        <div className="flex items-center gap-1"><CheckCircle2 size={12} /><span className="text-2xs font-semibold uppercase">{verifiedLabel}</span></div>
                    </div>
                </div>
            </main>
        </div>
    );
}

function BenefitCard({ icon: Icon, title, desc }: any) {
    return (
        <div className="flex items-start gap-4 group">
            <div className="size-10 rounded-md bg-info-soft dark:bg-[hsl(var(--info))]/30 flex items-center justify-center text-[hsl(var(--primary))] shrink-0 group-hover:scale-110 transition-transform shadow-sm">
                <Icon size={20} />
            </div>
            <div>
                <h4 className="text-sm font-bold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{title}</h4>
                <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed mt-0.5">{desc}</p>
            </div>
        </div>
    );
}

function TypeOption({ active, onClick, icon: Icon, label }: any) {
    return (
        <button
            onClick={onClick}
            className={clsx(
                "p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition-all group",
                active
                    ? "border-[hsl(var(--info)/100%)] bg-info-soft/50 dark:bg-[hsl(var(--info))]/10 shadow-md"
                    : "border-[hsl(var(--border))] dark:border-white/5 hover:border-[hsl(var(--info)/25%)]"
            )}
        >
            <div className={clsx(
                "size-10 rounded-md flex items-center justify-center transition-all",
                active ? "bg-[hsl(var(--primary))] text-white shadow-lg" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))]"
            )}>
                <Icon size={20} />
            </div>
            <span className={clsx("text-2xs font-bold uppercase tracking-wide", active ? "text-[hsl(var(--primary))] dark:text-white" : "text-[hsl(var(--text-secondary))]")}>{label}</span>
        </button>
    );
}
