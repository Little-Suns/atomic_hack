/**
 * Контекст аутентификации пользователя.
 * Управляет состоянием входа/выхода и хранит данные текущего пользователя.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import api from '../services/api'

interface AuthContextType {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  user: { id: number; email: string } | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

/**
 * Hook для доступа к контексту аутентификации
 * @throws {Error} Если используется вне AuthProvider
 */
export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

/**
 * Провайдер контекста аутентификации
 * Оборачивает приложение и предоставляет методы login/logout
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [user, setUser] = useState<{ id: number; email: string } | null>(null)

  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
      setIsAuthenticated(true)
    }
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const userData = await api.login(email, password)
      setUser({ id: userData.id, email: userData.email })
      setIsAuthenticated(true)
      localStorage.setItem('user', JSON.stringify({ id: userData.id, email: userData.email }))
      return true
    } catch (error) {
      console.error('Ошибка входа:', error)
      return false
    }
  }

  const logout = () => {
    setUser(null)
    setIsAuthenticated(false)
    localStorage.removeItem('user')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, user }}>
      {children}
    </AuthContext.Provider>
  )
}
