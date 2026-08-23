/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",                    // 前端请求 /api/xxx 时……
        destination: "http://localhost:8000/:path*", // ……替它发给后端 xxx
      },
    ];
  },
};

export default nextConfig;

//:path* 是通配符。
// 前端请求 /api/agent/chat → 规则匹配 →
// Next 服务器自己去请求 http://localhost:8000/agent/chat，
// 拿到结果再原样回给浏览器。
// 注意 destination 必须写
// 完整的 http://localhost:8000（跨机器转发，不能写相对路径）