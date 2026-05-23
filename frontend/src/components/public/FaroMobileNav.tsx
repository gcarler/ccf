import React from "react";

export default function FaroMobileNav() {
    return (
        <div className="md:hidden fixed bottom-0 left-0 w-full flex justify-center pb-8 z-50">
            <div className="bg-[#001134]/80 backdrop-blur-2xl w-[90%] max-w-md rounded-[0.75rem] px-3 py-3 flex justify-between items-center shadow-[0_20px_40px_rgba(0,0,0,0.5)]">
                <div className="flex flex-col items-center justify-center text-faro-primary bg-[#004581]/50 rounded-[0.75rem] p-2 shadow-[0_0_15px_rgba(128,208,255,0.3)]">
                    <span className="material-symbols-outlined">home</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Inicio</span>
                </div>
                <div className="flex flex-col items-center justify-center text-[#d9e2ff]/50">
                    <span className="material-symbols-outlined">calendar_today</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Eventos</span>
                </div>
                <div className="flex flex-col items-center justify-center text-[#d9e2ff]/50">
                    <span className="material-symbols-outlined">play_circle</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Multimed</span>
                </div>
                <div className="flex flex-col items-center justify-center text-[#d9e2ff]/50">
                    <span className="material-symbols-outlined">location_on</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Sedes</span>
                </div>
                <div className="flex flex-col items-center justify-center text-[#d9e2ff]/50">
                    <span className="material-symbols-outlined">menu</span>
                    <span className="font-body text-[10px] font-medium tracking-wide">Más</span>
                </div>
            </div>
        </div>
    );
}
