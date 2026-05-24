import React from "react";

export default function FaroMobileNav() {
    return (
        <div className="md:hidden fixed bottom-0 left-0 w-full flex justify-center pb-8 z-50">
            <div
                className="backdrop-blur-2xl w-[90%] max-w-md rounded-[0.75rem] px-3 py-3 flex justify-between items-center"
                style={{
                    background: "var(--faro-mobile-nav-bg)",
                    boxShadow: "var(--faro-mobile-nav-shadow)",
                }}
            >
                <div
                    className="flex flex-col items-center justify-center text-faro-primary rounded-[0.75rem] p-2"
                    style={{
                        background: "var(--faro-primary-container)",
                        boxShadow: "var(--faro-mobile-nav-glow)",
                    }}
                >
                    <span className="material-symbols-outlined">home</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Inicio</span>
                </div>
                <div className="flex flex-col items-center justify-center" style={{ color: "var(--faro-mobile-nav-inactive)" }}>
                    <span className="material-symbols-outlined">calendar_today</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Eventos</span>
                </div>
                <div className="flex flex-col items-center justify-center" style={{ color: "var(--faro-mobile-nav-inactive)" }}>
                    <span className="material-symbols-outlined">play_circle</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Multimed</span>
                </div>
                <div className="flex flex-col items-center justify-center" style={{ color: "var(--faro-mobile-nav-inactive)" }}>
                    <span className="material-symbols-outlined">location_on</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Sedes</span>
                </div>
                <div className="flex flex-col items-center justify-center" style={{ color: "var(--faro-mobile-nav-inactive)" }}>
                    <span className="material-symbols-outlined">menu</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Más</span>
                </div>
            </div>
        </div>
    );
}
