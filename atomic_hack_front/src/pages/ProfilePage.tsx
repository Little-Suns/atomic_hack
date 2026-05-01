import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Header from '../components/Header'
import { FileText, Loader2, Trash2 } from 'lucide-react'
import api from '../services/api'

interface Presentation {
  id: number
  title: string
  user_id: number
}

const ProfilePage: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [presentations, setPresentations] = useState<Presentation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    loadPresentations()
  }, [])

  const loadPresentations = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getPresentations()
      setPresentations(data)
    } catch (err) {
      console.error('Ошибка загрузки презентаций:', err)
      setError('Не удалось загрузить презентации')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOpenPresentation = (presentationId: number) => {
    // Переходим на страницу создания с параметром ID презентации
    navigate(`/create?presentation=${presentationId}`)
  }

  const handleCreateNew = async () => {
    setIsCreating(true)
    setError(null)
    try {
      // Создаем новую презентацию с дефолтным названием
      const newPresentation = await api.newPresentation('Новая презентация')
      // Переходим на страницу создания с ID новой презентации
      navigate(`/create?presentation=${newPresentation.id}`)
    } catch (err) {
      console.error('Ошибка создания презентации:', err)
      setError('Не удалось создать новую презентацию')
      setIsCreating(false)
    }
  }

  const handleDeletePresentation = async (presentationId: number) => {
    if (!confirm('Вы уверены, что хотите удалить эту презентацию?')) {
      return
    }

    setDeletingId(presentationId)
    try {
      await api.deletePresentation(presentationId)
      setPresentations(prev => prev.filter(p => p.id !== presentationId))
    } catch (err) {
      console.error('Ошибка удаления презентации:', err)
      setError('Не удалось удалить презентацию')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-rosatom-text mb-2">
                Мои презентации
              </h1>
              {user && (
                <p className="text-gray-600">
                  {user.email}
                </p>
              )}
            </div>
            {presentations.length > 0 && !isLoading && (
              <button
                onClick={handleCreateNew}
                disabled={isCreating}
                className="btn-primary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Создание...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-5 w-5" />
                    Создать новую
                  </>
                )}
              </button>
            )}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-12 w-12 animate-spin text-rosatom-blue mb-4" />
              <p className="text-gray-600">Загрузка презентаций...</p>
            </div>
          ) : presentations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-600 mb-2">
                У вас пока нет презентаций
              </h3>
              <p className="text-gray-500 mb-6">
                Создайте свою первую презентацию с помощью ИИ
              </p>
              <button
                onClick={handleCreateNew}
                disabled={isCreating}
                className="btn-primary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Создание...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-5 w-5" />
                    Создать презентацию
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {presentations.map((presentation) => (
                <div
                  key={presentation.id}
                  className="bg-gray-50 rounded-lg border border-gray-200 hover:border-rosatom-blue transition-all duration-200 hover:shadow-md"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <FileText className="h-8 w-8 text-rosatom-blue flex-shrink-0" />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDeletePresentation(presentation.id)}
                          disabled={deletingId === presentation.id}
                          className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors duration-200 disabled:opacity-50"
                          title="Удалить"
                        >
                          {deletingId === presentation.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                    
                    <h3 className="text-lg font-semibold text-rosatom-text mb-6 line-clamp-2">
                      {presentation.title}
                    </h3>

                    <button
                      onClick={() => handleOpenPresentation(presentation.id)}
                      className="w-full btn-secondary text-center"
                    >
                      Открыть
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default ProfilePage
