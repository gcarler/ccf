"use client";

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

// /plataforma/academy/courses redirige al catálogo principal.
// La ruta de aprendizaje individual es /plataforma/academy/course/[id].
export default function AcademyCoursesPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/academy');
    }, [router]);

    return (
        <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm text-[hsl(var(--text-secondary))]">Redirigiendo a Academia...</p>
            </div>
        </div>
    );
}
