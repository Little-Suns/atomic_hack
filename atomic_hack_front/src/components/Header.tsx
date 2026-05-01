import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Atom, LogOut, User, FileText } from 'lucide-react'

const Header: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const isCreatePage = location.pathname === '/create' || location.pathname.startsWith('/create')

  return (
    <header className="bg-rosatom-blue shadow-lg">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Логотип */}
          <div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="flex items-center justify-center w-10 h-10 bg-white rounded-full">
              <Atom className="w-6 h-6 text-rosatom-blue" />
            </div>
            <div>
              <h1 className="text-white font-bold text-xl">РОСАТОМ</h1>
              <p className="text-blue-100 text-xs">Сервис генерации презентаций</p>
            </div>
          </div>

          {/* Информация о пользователе */}
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate(isCreatePage ? '/' : '/create')}
              className="flex items-center text-white hover:text-blue-100 transition-colors duration-200 px-3 py-2 rounded-lg hover:bg-rosatom-dark-blue"
              title={isCreatePage ? 'Мои презентации' : 'Создать презентацию'}
            >
              {isCreatePage ? (
                <>
                  <User className="w-5 h-5 mr-2" />
                  <span className="text-sm font-medium">Профиль</span>
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5 mr-2" />
                  <span className="text-sm font-medium">Создать</span>
                </>
              )}
            </button>
            <div className="flex items-center text-white">
              <span className="text-sm font-medium">{user?.email}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center text-white hover:text-blue-100 transition-colors duration-200"
              title="Выйти"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
