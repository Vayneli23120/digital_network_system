import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import fs from 'fs'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      // 支持旧版 Chromium（扫码枪浏览器）
      target: ['es2015', 'chrome60'],
      // 不使用动态导入，避免兼容问题
      format: 'es'
    },
    server: {
      port: 3000,
      host: '0.0.0.0',
      https: {
        key: fs.readFileSync(resolve(__dirname, 'certs/key.pem')),
        cert: fs.readFileSync(resolve(__dirname, 'certs/cert.pem')),
      },
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true
        },
        '/photos': {
          target: apiBaseUrl,
          changeOrigin: true
        },
        '/ws': {
          target: apiBaseUrl,
          changeOrigin: true,
          ws: true,
          // 重要：WSS → WS 协议转换
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('proxy error', err);
            });
            proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
              // WebSocket 代理请求时的事件
              console.log('WebSocket proxy request:', req.url);
            });
          }
        },
        '/grafana': {
          target: apiBaseUrl,
          changeOrigin: true
        }
      }
    }
  }
})