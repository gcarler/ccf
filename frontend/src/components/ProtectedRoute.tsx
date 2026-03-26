"use client";

import React from 'react';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    requireVerifiedEmail?: boolean;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
    // BYPASS FOR DEVELOPMENT: Always allow access while finishing the platform
    return <>{children}</>;
}
