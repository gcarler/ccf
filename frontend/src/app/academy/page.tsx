"use client";

import React, { useEffect, useState } from 'react';
import AcademyClient from './AcademyClient';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

export default function AcademyPage() {
    const { token } = useAuth();
    const [courses, setCourses] = useState<any[]>([]);
    const [enrollments, setEnrollments] = useState<any[]>([]);

    useEffect(() => {
        if (!token) return;
        Promise.all([
            apiFetch<any[]>('/academy/courses', { token }),
            apiFetch<any[]>('/academy/enrollments/my', { token })
        ]).then(([c, e]) => {
            setCourses(c);
            setEnrollments(e);
        });
    }, [token]);

    return <AcademyClient />;
}
