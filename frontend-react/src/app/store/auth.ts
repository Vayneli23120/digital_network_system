import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  isLoggedIn: boolean
  currentUser: string | null
  accessToken: string | null
  login: (token: string, username: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isLoggedIn: false,
      currentUser: null,
      accessToken: null,

      login: (token: string, username: string) => {
        // Token 格式校验
        const parts = token.split('.')
        if (parts.length !== 3) {
          console.error('Invalid JWT token format')
          return
        }

        set({
          isLoggedIn: true,
          accessToken: token,
          currentUser: username,
        })
      },

      logout: () => {
        set({
          isLoggedIn: false,
          accessToken: null,
          currentUser: null,
        })
      },
    }),
    {
      name: 'nas-auth',
    }
  )
)