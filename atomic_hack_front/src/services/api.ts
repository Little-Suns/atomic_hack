/**
 * API клиент для взаимодействия с backend.
 * Предоставляет типизированные функции для всех API эндпоинтов.
 */

import axios from 'axios'
import { SlideTitle } from '../pages/MainPage'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const API_MODE = import.meta.env.VITE_API_MODE || 'api'
const USE_MOCK = API_MODE === 'mock'

if (USE_MOCK) {
  console.log('%c🧪 MOCK MODE ENABLED', 'background: #ff9800; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;')
  console.log('API запросы будут использовать моковые данные для тестирования фронтенда')
  console.log('Для переключения на реальный API установите VITE_API_MODE=api в .env файле')
} else {
  console.log('%c🚀 API MODE', 'background: #4caf50; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;')
  console.log(`Подключение к API: ${API_BASE_URL}`)
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Извлекает ID текущего пользователя из localStorage
 * @returns ID пользователя или null если не авторизован
 */
const getUserId = (): number | null => {
  const user = localStorage.getItem('user')
  if (user) {
    const userData = JSON.parse(user)
    return userData.id || null
  }
  return null
}

// Типы данных согласно OpenAPI схеме
export interface UserCreate {
  email: string
  password: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface UserRead {
  email: string
  id: number
}

export interface PresentationRead {
  id: number
  title: string
  user_id: number
  template_bucket_id?: string | null
  context_files?: string | null  // JSON array of uploaded files
  rag_id?: string | null
  slides: SlideRead[]
}

export interface SlideRead {
  id: number
  title: string
  description?: string | null
  position: number
  content_json?: string | null  // Structured JSON content
}

// API сервис
const api = {
  // ============ АУТЕНТИФИКАЦИЯ ============
  
  // Регистрация пользователя
  registration: async (email: string, password: string): Promise<UserRead> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Регистрация', { email })
      await new Promise(resolve => setTimeout(resolve, 500))
      return { email, id: Math.floor(Math.random() * 1000000) }
    }

    const response = await apiClient.post<UserRead>('/api/registration', {
      email,
      password,
    })
    return response.data
  },

  // Вход пользователя
  login: async (email: string, password: string): Promise<UserRead> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Вход', { email })
      await new Promise(resolve => setTimeout(resolve, 500))
      return { email, id: 1 }
    }

    try {
      const response = await apiClient.post<UserRead>('/api/login', {
        email,
        password,
      })
      return response.data
    } catch (error: any) {
      // Если пользователь не найден, пытаемся зарегистрировать
      if (error?.response?.status === 404 || error?.response?.status === 401) {
        console.log('Пользователь не найден, создаем нового...')
        return await api.registration(email, password)
      }
      throw error
    }
  },

  // ============ ПРЕЗЕНТАЦИИ ============

  // Получить все презентации пользователя
  getPresentations: async (): Promise<PresentationRead[]> => {
    const userId = getUserId()
    if (!userId) throw new Error('User not authenticated')

    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение презентаций')
      await new Promise(resolve => setTimeout(resolve, 500))
      return []
    }

    const response = await apiClient.get<PresentationRead[]>(
      `/api/getPresentations?user_id=${userId}`
    )
    return response.data
  },

  // Создать новую презентацию
  newPresentation: async (title: string): Promise<PresentationRead> => {
    const userId = getUserId()
    if (!userId) throw new Error('User not authenticated')

    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Создание презентации', { title })
      await new Promise(resolve => setTimeout(resolve, 500))
      return {
        id: Math.floor(Math.random() * 1000000),
        title,
        user_id: userId,
        slides: [],
      }
    }

    const response = await apiClient.post<PresentationRead>(
      `/api/newPresentation?user_id=${userId}&title=${encodeURIComponent(title)}`
    )
    return response.data
  },

  // Изменить заголовок презентации
  changeTitle: async (presentationId: number, newTitle: string): Promise<PresentationRead> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Изменение заголовка', { presentationId, newTitle })
      await new Promise(resolve => setTimeout(resolve, 300))
      return { id: presentationId, title: newTitle, user_id: 1, slides: [] }
    }

    const response = await apiClient.post<PresentationRead>(
      `/api/changeTitle?presentation_id=${presentationId}&new_title=${encodeURIComponent(newTitle)}`
    )
    return response.data
  },

  // Получить заголовок презентации
  getTitle: async (presentationId: number): Promise<string> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение заголовка', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 200))
      return 'Mock Presentation Title'
    }

    const response = await apiClient.get(
      `/api/getTitle?presentation_id=${presentationId}`
    )
    return response.data
  },

  // Получить презентацию
  getPresentation: async (presentationId: number): Promise<PresentationRead> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение презентации', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 500))
      return {
        id: presentationId,
        title: 'Mock Presentation',
        user_id: 1,
        slides: [],
      }
    }

    const response = await apiClient.get<PresentationRead>(
      `/api/getPresentation?presentation_id=${presentationId}`
    )
    return response.data
  },

  // Удалить презентацию
  deletePresentation: async (presentationId: number): Promise<void> => {
    const userId = getUserId()
    if (!userId) throw new Error('User not authenticated')

    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Удаление презентации', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 300))
      return
    }

    await apiClient.delete(
      `/api/deletePresentation?presentation_id=${presentationId}&user_id=${userId}`
    )
  },

  // ============ СЛАЙДЫ ============

  // Получить информацию о слайдах
  getSlidesInfo: async (presentationId: number): Promise<SlideTitle[]> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение слайдов', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 800))
      return [
        { id: '1', title: 'Введение в проект', description: 'Краткое описание проекта', order: 1 },
        { id: '2', title: 'Цели и задачи', description: 'Основные цели проекта', order: 2 },
        { id: '3', title: 'Текущая ситуация', description: 'Анализ текущей ситуации', order: 3 },
      ]
    }

    const response = await apiClient.get<SlideRead[]>(
      `/api/getSlidesInfo?presentation_id=${presentationId}`
    )
    
    // Преобразуем в формат SlideTitle
    // Сортируем по position перед преобразованием
    const sortedData = response.data.sort((a, b) => a.position - b.position)
    
    const slides: SlideTitle[] = sortedData.map((slide, index) => ({
      id: String(slide.id), // Конвертируем в строку для react-beautiful-dnd
      title: slide.title,
      description: slide.description || '',
      order: index + 1, // Нумерация с 1, используем index для корректности
      contentJson: slide.content_json || undefined,
    }))
    
    return slides
  },

  // Генерировать структуру слайдов (фоновая задача)
  generateSlidesInfo: async (
    presentationId: number,
    topic: string,
    numSlides: number = 10,
    useContext: boolean = true
  ): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Генерация структуры слайдов', {
        presentationId,
        topic,
        numSlides,
      })
      await new Promise(resolve => setTimeout(resolve, 2000))
      return
    }

    await apiClient.post(
      `/api/generateSlidesInfo?presentation_id=${presentationId}&topic=${encodeURIComponent(
        topic
      )}&num_slides=${numSlides}&use_context=${useContext}`
    )
  },

  // Изменить информацию одного слайда
  changeSlideInfo: async (
    presentationId: number,
    position: number,
    title: string,
    description: string
  ): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Изменение слайда', {
        presentationId,
        position,
        title,
      })
      await new Promise(resolve => setTimeout(resolve, 300))
      return
    }

    await apiClient.post(
      `/api/changeSlideInfo?presentation_id=${presentationId}&position=${position}&title=${encodeURIComponent(
        title
      )}&description=${encodeURIComponent(description)}`
    )
  },

  // Изменить позиции двух слайдов
  changeSlidesPosition: async (
    presentationId: number,
    position1: number,
    position2: number
  ): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Изменение позиций слайдов', {
        presentationId,
        position1,
        position2,
      })
      await new Promise(resolve => setTimeout(resolve, 300))
      return
    }

    await apiClient.post(
      `/api/changeSlidesPosition?presentation_id=${presentationId}&position1=${position1}&position2=${position2}`
    )
  },

  // Обновить информацию о всех слайдах (используется фронтендом)
  changeSlidesInfo: async (
    presentationId: number,
    slidesInfo: Array<{ id: string; title: string; description: string; position: number }>
  ): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Обновление информации о слайдах', {
        presentationId,
        slidesInfo,
      })
      await new Promise(resolve => setTimeout(resolve, 500))
      return
    }

    // Нормализуем ID - конвертируем строки в числа если возможно
    const normalizedSlides = slidesInfo.map(slide => ({
      id: slide.id ? parseInt(String(slide.id)) : null,
      title: slide.title,
      description: slide.description,
      position: slide.position
    }))

    await apiClient.post(
      `/api/changeSlidesInfo?presentation_id=${presentationId}`,
      normalizedSlides
    )
  },

  // Обновить JSON контент конкретного слайда
  updateSlideContent: async (slideId: number, contentJson: string): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Обновление контента слайда', { slideId })
      await new Promise(resolve => setTimeout(resolve, 300))
      return
    }

    await apiClient.post(
      `/api/updateSlideContent?slide_id=${slideId}`,
      { content_json: contentJson },
      { headers: { 'Content-Type': 'application/json' } }
    )
  },

  // ============ ГЕНЕРАЦИЯ КОНТЕНТА ============

  // Запустить генерацию структурированного контента слайдов (фоновая задача)
  generateSlideContent: async (presentationId: number): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Запуск генерации контента', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 2000))
      return
    }

    await apiClient.post(`/api/generateSlideContent?presentation_id=${presentationId}`)
  },

  // Получить сгенерированный контент слайдов для polling (формат [{Title, Content}])
  // Content теперь содержит JSON строку со структурированным контентом
  getContent: async (presentationId: number): Promise<Array<{ Title: string; Content: string }>> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение контента', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 1500))
      return [
        {
          Title: 'Введение',
          Content: JSON.stringify({ blocks: [{ type: 'text', data: { text: 'Моковый контент' } }] }),
        },
        {
          Title: 'Цели',
          Content: JSON.stringify({ blocks: [{ type: 'list', data: { items: ['Цель 1', 'Цель 2'] } }] }),
        },
      ]
    }

    const response = await apiClient.get(
      `/api/getContent?presId=${presentationId}`
    )
    return response.data
  },

  // Получить структурированный контент презентации из БД
  getPresentationContent: async (
    presentationId: number
  ): Promise<{
    presentation_id: number
    slides: Array<{ id: number; position: number; title: string; content_json: string }>
    has_content: boolean
  }> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Получение контента презентации', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 500))
      return {
        presentation_id: presentationId,
        slides: [
          {
            id: 1,
            position: 0,
            title: 'Слайд 1',
            content_json: JSON.stringify({ blocks: [{ type: 'text', data: { text: 'Контент 1' } }] }),
          },
        ],
        has_content: true,
      }
    }

    const response = await apiClient.get(
      `/api/getPresentationContent?presentation_id=${presentationId}`
    )
    return response.data
  },

  // Ассистент презентаций - исправить/переписать конкретные слайды
  presentationAssistantMessage: async (presentationId: number, message: string): Promise<any> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Ассистент презентаций', { presentationId, message })
      await new Promise(resolve => setTimeout(resolve, 1500))
      return { presentation_id: presentationId, message: 'Mock response', updated_slides: [] }
    }

    const response = await apiClient.post(
      `/api/presentationAssistantMessage?presentation_id=${presentationId}&message=${encodeURIComponent(
        message
      )}`
    )
    return response.data
  },

  // ============ ФАЙЛЫ ============

  // Загрузить шаблон PPTX
  uploadTemplate: async (presentationId: number, file: File): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Загрузка шаблона', { presentationId, file: file.name })
      await new Promise(resolve => setTimeout(resolve, 1000))
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    await axios.post(
      `${API_BASE_URL}/api/uploadTemplate?presentation_id=${presentationId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
  },

  // Загрузить контекстный файл для RAG
  uploadContextFile: async (presentationId: number, file: File): Promise<void> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Загрузка контекстного файла', {
        presentationId,
        file: file.name,
      })
      await new Promise(resolve => setTimeout(resolve, 1500))
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    await axios.post(
      `${API_BASE_URL}/api/uploadContextFile?presentation_id=${presentationId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
  },

  // ============ СКАЧИВАНИЕ ============

  // Скачать PPTX презентацию
  downloadPptx: async (presentationId: number): Promise<Blob> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Скачивание PPTX', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 1000))
      return new Blob(['Mock PPTX content'], {
        type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      })
    }

    const response = await axios.get(
      `${API_BASE_URL}/api/downloadPptx?presentation_id=${presentationId}`,
      {
        responseType: 'blob',
      }
    )

    return response.data
  },

  // Скачать PDF презентацию
  downloadPdf: async (presentationId: number): Promise<Blob> => {
    if (USE_MOCK) {
      console.log('🧪 MOCK MODE: Скачивание PDF', { presentationId })
      await new Promise(resolve => setTimeout(resolve, 1000))
      return new Blob(['Mock PDF content'], { type: 'application/pdf' })
    }

    const response = await axios.get(
      `${API_BASE_URL}/api/downloadPdf?presentation_id=${presentationId}`,
      {
        responseType: 'blob',
      }
    )

    return response.data
  },

  // ============ СОВМЕСТИМОСТЬ СО СТАРЫМ КОДОМ ============
  
  // Для совместимости с MainPage - создает презентацию и загружает файлы
  newPresentationRequest: async (title: string, files: File[], slideCount?: number): Promise<number> => {
    const userId = getUserId()
    if (!userId) throw new Error('User not authenticated')

    // Создаем презентацию
    const presentation = await api.newPresentation(title)
    
    // Загружаем файлы (если есть)
    if (files.length > 0) {
      for (const file of files) {
        await api.uploadContextFile(presentation.id, file)
      }
    }
    
    // Генерируем структуру слайдов
    if (slideCount) {
      await api.generateSlidesInfo(presentation.id, title, slideCount, true)
    }
    
    return presentation.id
  },

  // Для совместимости - запуск генерации контента (алиас для generateSlideContent)
  generatePresentation: async (presentationId: number): Promise<void> => {
    await api.generateSlideContent(presentationId)
  },

  // Для совместимости - скачивание (алиас)
  downloadPresentation: async (type: 'pdf' | 'pptx', presentationId: number): Promise<Blob> => {
    if (type === 'pdf') {
      return await api.downloadPdf(presentationId)
    } else {
      return await api.downloadPptx(presentationId)
    }
  },

  // Для совместимости - регенерация через ассистента
  regeneratePresentation: async (presentationId: number, changes: string): Promise<any> => {
    return await api.presentationAssistantMessage(presentationId, changes)
  },
}

export default api
