/** @type {import('next').NextConfig} */
const apiBaseUrl = process.env.API_BASE_URL || '';
const apiProxyTarget =
    process.env.API_PROXY_TARGET ||
    (apiBaseUrl ? apiBaseUrl.replace(/\/api\/?$/, '').replace(/\/$/, '') : '');

const nextConfig = {
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
    async rewrites() {
        if (!apiProxyTarget) return [];
        return [
            {
                source: '/api/:path*',
                destination: `${apiProxyTarget}/api/:path*`
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
