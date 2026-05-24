import Link from "next/link";
import React from "react";

export default function FaroFooter() {
    return (
        <footer className="bg-[#001134] w-full rounded-none">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 px-4 py-1.5 border-t border-faro-primary-fixed-dim/10 max-w-[1440px] mx-auto">
                <div className="space-y-3">
                    <div className="text-lg font-bold text-faro-primary-fixed-dim font-headline">FARO</div>
                    <p className="text-faro-on-background/60 font-body leading-relaxed text-sm">Iluminando el camino hacia una conexión profunda con lo divino a través de la comunidad y la guía espiritual.</p>
                    <div className="flex gap-4">
                        <span className="material-symbols-outlined text-faro-primary-fixed-dim opacity-80 hover:opacity-100 cursor-pointer">public</span>
                        <span className="material-symbols-outlined text-faro-primary-fixed-dim opacity-80 hover:opacity-100 cursor-pointer">mail</span>
                    </div>
                </div>
                <div className="space-y-3">
                    <h4 className="text-faro-primary-fixed-dim font-bold uppercase text-xs tracking-wide">Navegación</h4>
                    <ul className="space-y-4">
                        <li><Link className="text-faro-on-background/60 hover:text-faro-primary-fixed-dim underline-offset-4 hover:underline text-sm font-body" href="https://facebook.com/comunidadfaro" target="_blank">Facebook</Link></li>
                        <li><Link className="text-faro-on-background/60 hover:text-faro-primary-fixed-dim underline-offset-4 hover:underline text-sm font-body" href="https://instagram.com/comunidadfaro" target="_blank">Instagram</Link></li>
                        <li><Link className="text-faro-on-background/60 hover:text-faro-primary-fixed-dim underline-offset-4 hover:underline text-sm font-body" href="https://youtube.com/comunidadfaro" target="_blank">YouTube</Link></li>
                    </ul>
                </div>
                <div className="space-y-3">
                    <h4 className="text-faro-primary-fixed-dim font-bold uppercase text-xs tracking-wide">Recursos</h4>
                    <ul className="space-y-4">
                        <li><Link className="text-faro-on-background/60 hover:text-faro-primary-fixed-dim underline-offset-4 hover:underline text-sm font-body" href="/boletin">Newsletter Signup</Link></li>
                        <li><Link className="text-faro-on-background/60 hover:text-faro-primary-fixed-dim underline-offset-4 hover:underline text-sm font-body" href="/conocer-a-jesus#contacto">Contact Us</Link></li>
                    </ul>
                </div>
                <div className="space-y-3">
                    <h4 className="text-faro-primary-fixed-dim font-bold uppercase text-xs tracking-wide">Legal</h4>
                    <p className="text-faro-on-background/60 text-sm font-body leading-relaxed">© 2024 FARO. The Radiant Guide.</p>
                    <div className="pt-4">
                        <Link href="/privacidad" className="text-faro-secondary-fixed-dim font-semibold text-xs uppercase tracking-wide hover:text-faro-primary-fixed-dim transition-all">Política de Privacidad</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
