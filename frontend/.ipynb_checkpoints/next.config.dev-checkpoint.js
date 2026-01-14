/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 本地开发模式：启用代理到后端
  async rewrites() {
    const backendOrigin = process.env.NEXT_PUBLIC_BACKEND_ORIGIN || 'http://127.0.0.1:6001'
    console.log('开发模式：代理后端地址 =>', backendOrigin)
    
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: '/output/:path*',
        destination: `${backendOrigin}/output/:path*`,
      },
      {
        source: '/generated_images/:path*',
        destination: `${backendOrigin}/generated_images/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
