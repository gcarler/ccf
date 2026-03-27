import type { Metadata } from 'next';
import AcademyClient from './AcademyClient';
import { serverApiFetch } from '@/lib/serverApi';

export const metadata: Metadata = {
    title: 'Academia Faro · CCF Mesh',
};

export const dynamic = 'force-dynamic';

async function fetchInitialCourses() {
    try {
        const data = await serverApiFetch<any[]>('/courses/');
        return Array.isArray(data) ? data : [];
    } catch (error) {
        console.error('academy courses fetch failed', error);
        return [];
    }
}

async function fetchInitialEnrollments() {
    try {
        const me = await serverApiFetch<{ user_id: string }>('/auth/me');
        if (!me?.user_id) return [];
        const enrollments = await serverApiFetch<any[]>(`/users/${me.user_id}/enrollments`);
        return Array.isArray(enrollments) ? enrollments : [];
    } catch (error) {
        console.error('academy enrollments fetch failed', error);
        return [];
    }
}

export default async function AcademyPage() {
    const [courses, enrollments] = await Promise.all([
        fetchInitialCourses(),
        fetchInitialEnrollments(),
    ]);

    return <AcademyClient initialCourses={courses} initialEnrollments={enrollments} />;
}
