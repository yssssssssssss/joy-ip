/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production'
const backendOrigin = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || 'http://127.0.0.1:6001'

const nextConfig = {
  reactStrictMode: true,
  
  // 静态导出配置（云服务器生产环境）
  output: 'export',
  trailingSlash: false,

  // 本地开发时将 `/api/*` 等请求代理到后端，避免跨域/404
  async rewrites() {
    if (!isDev) return []
    return [
      { source: '/api/:path*', destination: `${backendOrigin}/api/:path*` },
      { source: '/output/:path*', destination: `${backendOrigin}/output/:path*` },
      { source: '/generated_images/:path*', destination: `${backendOrigin}/generated_images/:path*` },
    ]
  },
}

module.exports = nextConfig
