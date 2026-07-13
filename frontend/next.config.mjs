/** @type {import('next').NextConfig} */
const apiBaseUrl = process.env.API_BASE_URL || '';
const apiProxyTarget =
    process.env.API_PROXY_TARGET ||
    (apiBaseUrl ? apiBaseUrl.replace(/\/api\/?$/, '').replace(/\/$/, '') : '');

const nextConfig = {
    allowedDevOrigins: ['elfarocc.tech', 'www.elfarocc.tech'],
    images: {
        // CMS media is already served by the backend as immutable WebP assets.
        // Avoid Next's image proxy for /api/static media to prevent noisy 400s
        // when the optimizer receives proxied local URLs.
        unoptimized: true,
        // Enable WebP and AVIF automatic format negotiation
        formats: ['image/webp', 'image/avif'],
        deviceSizes: [640, 768, 1024, 1280, 1536, 1920],
        imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
        remotePatterns: [
            {
                protocol: 'https',
                hostname: 'images.unsplash.com',
                pathname: '**',
            },
            {
                protocol: 'https',
                hostname: 'picsum.photos',
                pathname: '**',
            },
            {
                protocol: 'https',
                hostname: 'ui-avatars.com',
                pathname: '/api/**',
            },
            {
                protocol: 'https',
                hostname: 'img.youtube.com',
                pathname: '/vi/**',
            },
            // Backend serving optimized images (WebP)
            {
                protocol: 'https',
                hostname: 'elfarocc.tech',
                pathname: '/api/static/**',
            },
            // Allow localhost for development
            {
                protocol: 'http',
                hostname: 'localhost',
                port: '8000',
                pathname: '/api/static/**',
            },
            {
                protocol: 'http',
                hostname: '127.0.0.1',
                port: '8000',
                pathname: '/api/static/**',
            },
            // Backend proxy route
            {
                protocol: 'http',
                hostname: 'backend',
                port: '8000',
                pathname: '/api/static/**',
            },
            // QR code generation for certificates
            {
                protocol: 'https',
                hostname: 'api.qrserver.com',
                pathname: '/v1/**',
            },
        ],
    },
    eslint: {
        ignoreDuringBuilds: true,
    },
    typescript: {
        ignoreBuildErrors: false,
    },
    outputFileTracingRoot: process.env.OUTPUT_FILE_TRACING_ROOT || '/root/ccf/frontend',
    outputFileTracingExcludes: {
        '*': ['**/@swc/core*', '**/@esbuild/**', '**/terser/**'],
    },
    async headers() {
        return [
            {
                source: '/((?!_next/static|_next/image|api|icons|pastores|manifest.json|favicon.ico|noise.svg).*)',
                headers: [
                    { key: 'Cache-Control', value: 'no-store, no-cache, max-age=0, must-revalidate' },
                    { key: 'Pragma', value: 'no-cache' },
                    { key: 'Expires', value: '0' },
                ],
            },
            {
                source: '/auth/callback',
                headers: [
                    { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
                    { key: 'Pragma', value: 'no-cache' },
                    { key: 'Expires', value: '0' },
                ],
            },
        ];
    },
    async redirects() {
        return [
            {
                source: '/faro',
                destination: '/',
                permanent: true,
            },
            {
                source: '/faro/:path*',
                destination: '/:path*',
                permanent: true,
            },
            {
                source: '/plataforma/evangelism/faro',
                destination: '/plataforma/evangelism/groups',
                permanent: true,
            },
            {
                source: '/plataforma/evangelism/faro/:path*',
                destination: '/plataforma/evangelism/groups/:path*',
                permanent: true,
            },
        ];
    },
    async rewrites() {
        const target = process.env.API_PROXY_TARGET || 'http://backend:8000';
        return [
            {
                source: '/api/:path*',
                destination: `${target}/api/:path*`
            }
        ];
    },
    webpack(config, { isServer }) {
        if (isServer) {
            config.output.chunkFilename = "chunks/[name].js";
        }
        return config;
    },
};

export default nextConfig;
