/** @type {import('next').NextConfig} */
const apiBaseUrl = process.env.API_BASE_URL || '';
const apiProxyTarget =
    process.env.API_PROXY_TARGET ||
    (apiBaseUrl ? apiBaseUrl.replace(/\/api\/?$/, '').replace(/\/$/, '') : '');

const nextConfig = {
    allowedDevOrigins: ['elfarocc.tech', 'www.elfarocc.tech'],
    images: {
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
        ],
    },
    eslint: {
        ignoreDuringBuilds: true,
    },
    typescript: {
        ignoreBuildErrors: true,
    },
    outputFileTracingRoot: process.env.OUTPUT_FILE_TRACING_ROOT || '/root/ccf/frontend',
    experimental: {
        outputFileTracingExcludes: {
            '*': ['**/@swc/core*', '**/@esbuild/**', '**/terser/**'],
        },
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
