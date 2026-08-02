import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import fs from 'fs'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiBaseUrl = env.VITE_API_URL || 'http://localhost:8000'
  const certKey = resolve(__dirname, 'certs/key.pem')
  const certFile = resolve(__dirname, 'certs/cert.pem')
  const hasCerts = fs.existsSync(certKey) && fs.existsSync(certFile)

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      // 支持旧版 Chromium（扫码枪浏览器）：router 已全量动态 import()，
      // 最低需 Chrome 63+，target 不能再按 chrome60 声称支持。
      target: ['es2018', 'chrome63'],
      rollupOptions: {
        output: {
          // 拆分 vendor chunk，避免 three+echarts+element-plus 挤进同一首屏 chunk
          manualChunks(id) {
            if (id.includes('node_modules/three')) return 'three'
            if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) return 'echarts'
            if (id.includes('node_modules/element-plus') || id.includes('@element-plus')) return 'element-plus'
            if (id.includes('node_modules/vue') || id.includes('node_modules/@vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia')) return 'vue-vendor'
            if (id.includes('node_modules/axios')) return 'axios'
          }
        }
      }
    },
    server: {
      port: 3000,
      host: '0.0.0.0',
      // 证书缺失时跳过 HTTPS（读不到证书连 vite build 都会在配置加载期崩溃）
      https: hasCerts
        ? {
            key: fs.readFileSync(resolve(__dirname, 'certs/key.pem')),
            cert: fs.readFileSync(resolve(__dirname, 'certs/cert.pem')),
          }
        : undefined,
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