"use client";

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

// /academy/courses redirects to /academy (el listado de cursos está en la página principal)
// La ruta correcta para un curso individual es /academy/course/[id]
export default function AcademyCoursesPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/academy');
    }, [router]);

    return (
        <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-2">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm text-slate-500">Redirigiendo a Academia...</p>
            </div>
        </div>
    );
}
