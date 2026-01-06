/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 静态导出配置（云服务器生产环境）
  output: 'export',
  trailingSlash: false,
}

module.exports = nextConfig

