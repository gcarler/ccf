import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PLATAFORMA_ROUTES = [
    'crm',
    'projects',
    'evangelism',
    'academy',
    'agenda',
    'finances',
    'groups',
    'inbox',
    'tasks',
    'whiteboard',
    'wiki',
    'community',
    'settings',
    'account',
    'admin',
    'cms',
    'onboarding',
    'support',
    'spiritual-life',
    'calendar',
    'graph',
    'theme',
];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Skip already-prefixed paths and root-level paths
    if (pathname.startsWith('/plataforma/') || pathname === '/' || pathname.startsWith('/_next/') || pathname.startsWith('/api/') || pathname.startsWith('/favicon') || pathname.startsWith('/login') || pathname.startsWith('/register') || pathname.startsWith('/reset-password') || pathname.startsWith('/verify-email') || pathname.startsWith('/donate') || pathname.startsWith('/events') || pathname.startsWith('/sermons') || pathname.startsWith('/books') || pathname.startsWith('/privacy') || pathname.startsWith('/terms') || pathname.startsWith('/testimonials') || pathname.startsWith('/pastores') || pathname.startsWith('/public') || pathname.startsWith('/auth') || pathname.startsWith('/s/')) {
        return NextResponse.next();
    }

    const firstSegment = pathname.split('/')[1];
    if (PLATAFORMA_ROUTES.includes(firstSegment)) {
        const url = request.nextUrl.clone();
        url.pathname = `/plataforma${pathname}`;
        return NextResponse.redirect(url, { status: 308 });
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        /*
         * Match all paths except static files and Next.js internals
         */
        '/((?!_next/static|_next/image|favicon.ico|manifest.json|sw.js|workbox-).*)',
    ],
};
