import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import FileUpload from '../components/FileUpload'
import SlideEditor from '../components/SlideEditor'
import PresentationPreview from '../components/PresentationPreview'
import Header from '../components/Header'
import { FileText, AlertCircle, Loader2 } from 'lucide-react'
import api from '../services/api'

export interface SlideTitle {
  id: string
  title: string
  description?: string // Slide description from API
  order: number
  contentJson?: string // Structured JSON slide content
  generated?: boolean // Indicates generated content is ready
  isRegenerating?: boolean // Indicates this slide is being regenerated now
}

const MainPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const [presentationTitle, setPresentationTitle] = useState<string>('')
  const [slideCount, setSlideCount] = useState<number>(5)
  const [presentationId, setPresentationId] = useState<number | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [templateFile, setTemplateFile] = useState<File | null>(null)
  const [slideTitles, setSlideTitles] = useState<SlideTitle[]>([])
  const [originalSlides, setOriginalSlides] = useState<SlideTitle[]>([]) // Снимок слайдов после генерации для отслеживания изменений
  const [isLoadingPresentation, setIsLoadingPresentation] = useState(false)
  const [isDownloadingPptx, setIsDownloadingPptx] = useState(false)
  const [templateLoaded, setTemplateLoaded] = useState(false)
  const [hasRagCollection, setHasRagCollection] = useState(false)
  const pollingIntervalRef = useRef<number | null>(null)

  // Load presentation from URL query param.
  useEffect(() => {
    const presentationIdParam = searchParams.get('presentation')
    if (presentationIdParam) {
      const id = parseInt(presentationIdParam)
      if (!isNaN(id)) {
        loadExistingPresentation(id)
      }
    }
  }, [searchParams])

  // Cleanup intervals/timeouts on unmount.
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
      if (titleSaveTimeoutRef.current) {
        clearTimeout(titleSaveTimeoutRef.current)
      }
    }
  }, [])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [analysisComplete, setAnalysisComplete] = useState(false)
  const [generationComplete, setGenerationComplete] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isUploadingFiles, setIsUploadingFiles] = useState(false)
  const [isSavingTitle, setIsSavingTitle] = useState(false)

  // Detect slides changed since the last generated snapshot.
  const getModifiedSlides = (): number[] => {
    if (originalSlides.length === 0) return []
    
    const modifiedPositions: number[] = []
    
    // Если количество слайдов изменилось - ВСЕ слайды нужно перегенерировать
    if (slideTitles.length !== originalSlides.length) {
      console.log('📊 Изменилось количество слайдов:', originalSlides.length, '→', slideTitles.length)
      return slideTitles.map(slide => slide.order)
    }
    
    // Проверяем каждый слайд на изменения
    slideTitles.forEach((slide, index) => {
      const original = originalSlides[index]
      if (!original) {
        // Новый слайд - считаем измененным
        modifiedPositions.push(slide.order)
        return
      }
      
      // Проверяем изменения title, description или порядка
      if (
        slide.title !== original.title ||
        slide.description !== original.description ||
        slide.order !== original.order
      ) {
        modifiedPositions.push(slide.order)
      }
    })
    
    return modifiedPositions
  }

  const handleFilesUpload = useCallback(async (files: File[]) => {
    setUploadedFiles(files)
    setAnalysisComplete(false)
    setGenerationComplete(false)
    setSlideTitles([])
    setOriginalSlides([])
    setTemplateFile(null)
    setError(null)
    // НЕ сбрасываем presentationId - используем существующую презентацию если она уже создана
    setHasRagCollection(false)

    // Если файлы были выбраны, загружаем их на сервер
    if (files.length > 0 && presentationTitle.trim()) {
      setIsUploadingFiles(true)
      try {
        let presId = presentationId
        if (!presId) {
          console.log('📝 Создаём новую презентацию при загрузке файлов:', presentationTitle)
          const newPresentation = await api.newPresentation(presentationTitle)
          setPresentationId(newPresentation.id)
          presId = newPresentation.id
          console.log('✅ Презентация создана с ID:', presId)
        } else {
          console.log('📝 Используем существующую презентацию ID:', presId, 'для загрузки файлов')
        }

        // Загружаем каждый файл
        for (const file of files) {
          console.log(`📁 Загружаем файл: ${file.name}`)
          await api.uploadContextFile(presId, file)
          console.log(`✅ Файл загружен: ${file.name}`)
        }
        console.log('✅ Все файлы успешно загружены')
        setHasRagCollection(true)
      } catch (err) {
        console.error('Ошибка загрузки файлов:', err)
        setError('Ошибка при загрузке файлов. Попробуйте еще раз.')
      } finally {
        setIsUploadingFiles(false)
      }
    }
  }, [presentationTitle, presentationId])

  const handleTemplateUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pptx')) {
        setError('Пожалуйста, загрузите файл в формате .pptx');
        return;
      }

      if (!presentationTitle.trim()) {
        setError('Пожалуйста, введите название презентации перед загрузкой шаблона');
        // reset the file input
        event.target.value = '';
        return;
      }

      setTemplateFile(file);
      setError(null);

      try {
        // Используем существующую презентацию или создаём новую ТОЛЬКО если её нет
        let presId = presentationId;
        if (!presId) {
          console.log('📝 Создаём новую презентацию при загрузке шаблона:', presentationTitle);
          const newPresentation = await api.newPresentation(presentationTitle);
          setPresentationId(newPresentation.id);
          presId = newPresentation.id;
          console.log('✅ Презентация создана с ID:', presId);
        } else {
          console.log('📎 Загружаем шаблон для существующей презентации ID:', presId);
        }
        
        await api.uploadTemplate(presId, file);
        setTemplateLoaded(true);
        console.log('✅ Шаблон загружен успешно');

      } catch (err) {
        console.error('Ошибка загрузки шаблона:', err);
        setError('Не удалось загрузить шаблон');
        setTemplateFile(null);
        setTemplateLoaded(false);
        event.target.value = '';
      }
    }
  };

  const loadExistingPresentation = async (id: number) => {
    setIsLoadingPresentation(true)
    setError(null)
    
    try {
      console.log('📂 Загрузка презентации ID:', id)
      
      // 1. Получаем информацию о презентации
      const presentation = await api.getPresentation(id)
      setPresentationId(id)
      setPresentationTitle(presentation.title)
      
      // Проверяем наличие загруженного шаблона
      if (presentation.template_bucket_id) {
        setTemplateLoaded(true)
        console.log('📎 Шаблон загружен:', presentation.template_bucket_id)
      }
      
      // Проверяем наличие RAG коллекции
      if (presentation.rag_id) {
        setHasRagCollection(true)
        console.log('📚 RAG коллекция есть:', presentation.rag_id)
      }
      
      // 2. Получаем слайды
      const slides = await api.getSlidesInfo(id)
      
      // 3. Проверяем, есть ли сгенерированный контент и проставляем флаг generated
      const hasGeneratedContent = slides.some(s => s.contentJson)
      const slidesWithGeneratedFlags = slides.map(slide => ({
        ...slide,
        generated: Boolean(slide.contentJson && slide.contentJson.trim()),
        isRegenerating: false
      }))
      
      setSlideTitles(slidesWithGeneratedFlags)
      
      if (slides.length > 0) {
        setAnalysisComplete(true)
      }
      
      if (hasGeneratedContent) {
        setGenerationComplete(true)
        // Сохраняем снимок для отслеживания изменений
        console.log('📸 Сохраняем снимок загруженных слайдов')
        setOriginalSlides(JSON.parse(JSON.stringify(slidesWithGeneratedFlags)))
        console.log('✅ Загружена презентация с контентом')
      } else {
        console.log('📝 Загружена презентация без контента')
      }
      
    } catch (err) {
      console.error('Ошибка загрузки презентации:', err)
      setError('Не удалось загрузить презентацию')
    } finally {
      setIsLoadingPresentation(false)
    }
  }

  const handleAnalyzeData = async () => {
    if (uploadedFiles.length === 0 && !presentationId) {
      setError('Пожалуйста, загрузите файлы для анализа');
      return;
    }

    if (!presentationTitle.trim()) {
      setError('Пожалуйста, введите название презентации');
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // Создаём презентацию только если она ещё не существует
      let presId = presentationId;
      if (!presId) {
        console.log('📝 Создаём новую презентацию:', presentationTitle);
        const newPresentation = await api.newPresentation(presentationTitle);
        setPresentationId(newPresentation.id);
        presId = newPresentation.id;
        console.log('✅ Презентация создана с ID:', presId);
      } else {
        console.log('📝 Используем существующую презентацию ID:', presId);
      }

  // Файлы уже загружены в handleFilesUpload или есть RAG коллекция на бэкенде.
  // Передаём useContext=true когда есть контекст (либо загруженные файлы, либо уже существующая RAG коллекция)
  const useContext = hasRagCollection || uploadedFiles.length > 0
  await api.generateSlidesInfo(presId, presentationTitle, slideCount, useContext);
      
      console.log('📊 Создана/обновлена презентация ID:', presId);
      
      console.log('⏳ Ожидаем генерацию структуры...');
      
      // ... polling logic (with presId)
      let attempts = 0;
      const maxAttempts = 60; // 60 * 2 сек = 2 минуты
      let slides: SlideTitle[] = [];
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000)); // ждем 2 секунды
        
        try {
          slides = await api.getSlidesInfo(presId);
          
          if (slides.length > 0) {
            console.log('✅ Получены слайды:', slides.length);
            setSlideTitles(slides);
            setAnalysisComplete(true);
            setIsAnalyzing(false);
            return;
          }
          
          console.log(`⏳ Попытка ${attempts + 1}/${maxAttempts} - слайды еще не готовы...`);
          attempts++;
        } catch (pollErr) {
          console.log('⏳ Ожидаем завершения генерации...');
          attempts++;
        }
      }
      
      // Если превышено время ожидания
      setError('Превышено время ожидания генерации структуры. Попробуйте обновить страницу.');
      setIsAnalyzing(false);
      
    } catch (err) {
      setError('Ошибка при анализе файлов. Попробуйте еще раз.');
      setIsAnalyzing(false);
      console.error('Ошибка анализа:', err);
    }
  };

  const handleGeneratePresentation = async () => {
    if (slideTitles.length === 0) {
      setError('Нет заголовков для генерации презентации')
      return
    }

    if (presentationId === null) {
      setError('Отсутствует ID презентации')
      return
    }

    setIsGenerating(true)
    setError(null)
    
    // Проверяем, это первая генерация или перегенерация
    const isRegeneration = generationComplete
    const modifiedPositions = isRegeneration ? getModifiedSlides() : []
    
    if (isRegeneration) {
      if (modifiedPositions.length === 0) {
        setError('Нет изменений для перегенерации. Измените заголовки или описания слайдов.')
        setIsGenerating(false)
        return
      }
      
      console.log(`🔄 Перегенерация ${modifiedPositions.length} измененных слайдов:`, modifiedPositions)
      
      // Помечаем только измененные слайды как перегенерирующиеся
      setSlideTitles(prev => prev.map(slide => ({
        ...slide,
        isRegenerating: modifiedPositions.includes(slide.order),
        generated: modifiedPositions.includes(slide.order) ? false : slide.generated
      })))
    } else {
      console.log('🎨 Первая генерация всех слайдов')
    }

    try {
      // 1. Сохраняем изменения структуры слайдов на бэкенд
      console.log('💾 Сохраняем структуру слайдов на бэкенд...')
      const slidesInfo = slideTitles.map((slide, index) => ({
        id: slide.id, // Отправляем как есть (строка), бэкенд будет парсить
        title: slide.title.trim(),
        description: (slide.description || '').trim(),
        position: index + 1, // Позиция должна быть 1-based
      }))
      
      console.log('📋 Отправляем слайды на бэкенд:', slidesInfo)
      await api.changeSlidesInfo(presentationId, slidesInfo)
      console.log('✅ Структура слайдов сохранена')
      
      // Небольшая задержка для уверенности
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 2. Запускаем генерацию HTML контента в фоне (не ждём завершения)
      console.log('🎨 Запускаем генерацию HTML контента...')
      api.generatePresentation(presentationId).catch((err) => {
        console.error('Фоновая генерация завершилась с ошибкой:', err)
      })
      
      // Начинаем polling для получения готовых слайдов
      let receivedSlidesCount = 0
      const totalSlides = slideTitles.length
      let pollAttempts = 0
      const maxPollAttempts = 120 // 120 * 5 сек = 10 минут максимум
      
      // Очищаем предыдущий интервал если он есть
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }

      pollingIntervalRef.current = window.setInterval(async () => {
        try {
          pollAttempts++
          
          // Получаем текущие готовые контент слайдов (объекты с Title/Content от API)
          const data = await api.getContent(presentationId)

          const normalize = (s: string) => (s || '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .replace(/[«»"“”'’`]/g, '')
            .replace(/[:;,.!?()-]/g, '')
            .trim()

          // Карта: нормализованный заголовок -> контент
          const pageByTitle = new Map<string, string>()
          data.forEach((p: any) => {
            const t = p.title || p.Title || ''
            const c = p.content || p.Content || ''
            const key = normalize(t)
            if (key && !pageByTitle.has(key)) {
              pageByTitle.set(key, c)
            }
          })

          // Обновляем слайды строго по совпадению заголовков
          const updatedSlides = slideTitles.map((slide) => {
            const key = normalize(slide.title)
            const content = pageByTitle.get(key)
            
            const wasRegenerating = slide.isRegenerating
            const hasNewContent = Boolean(content && content.trim())
            
            // Логика обновления зависит от режима:
            // - Первая генерация: обновляем все слайды с непустым контентом
            // - Перегенерация: обновляем только слайды с isRegenerating=true
            const shouldUpdateContent = isRegeneration 
              ? (wasRegenerating && hasNewContent) // При перегенерации - только помеченные слайды
              : hasNewContent // При первой генерации - все слайды с контентом
            
            // Обновляем contentJson
            const newContentJson = shouldUpdateContent ? content : (slide.contentJson ?? '')
            
            return {
              ...slide,
              contentJson: newContentJson,
              generated: Boolean(newContentJson && newContentJson.trim()),
              isRegenerating: wasRegenerating && !hasNewContent // Сбрасываем когда получен контент
            }
          })

          const generatedCount = updatedSlides.filter(s => s.generated).length
          const stillRegeneratingCount = updatedSlides.filter(s => s.isRegenerating).length
          
          if (generatedCount > receivedSlidesCount) {
            console.log(`📊 Получено слайдов: ${generatedCount}/${totalSlides}`)
            receivedSlidesCount = generatedCount
          }

          setSlideTitles(updatedSlides)
          
          // Проверяем завершение генерации
          const isComplete = isRegeneration 
            ? stillRegeneratingCount === 0 // При перегенерации - когда нет перегенерирующихся слайдов
            : generatedCount >= totalSlides // При первой генерации - когда все готовы
          
          if (isComplete) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            setGenerationComplete(true)
            setIsGenerating(false)
            
            // Сохраняем/обновляем снимок слайдов для отслеживания изменений
            console.log('📸 Обновляем снимок слайдов для отслеживания изменений')
            setOriginalSlides(JSON.parse(JSON.stringify(updatedSlides)))
            
            console.log('✅ Генерация завершена!')
          }
          
          // Защита от бесконечного polling
          if (pollAttempts >= maxPollAttempts) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            setError('Превышено время ожидания генерации')
            setIsGenerating(false)
          }
        } catch (err) {
          console.error('Ошибка при получении HTML:', err)
          // Продолжаем попытки, не прерываем polling
        }
      }, 5000) // Проверяем каждые 5 секунд
      
    } catch (err) {
      setError('Ошибка при запуске генерации презентации. Попробуйте еще раз.')
      setIsGenerating(false)
      console.error('Ошибка генерации:', err)
    }
  }

  const handleDownload = async (type: 'pdf' | 'pptx') => {
    if (presentationId === null) {
      setError('Отсутствует ID презентации')
      return
    }

    setIsDownloadingPptx(true)

    try {
      console.log(`Скачивание ${type} файла для презентации ${presentationId}`)
      
      // Получаем Blob с презентацией (может занять время)
      const blob = await api.downloadPresentation(type, presentationId)
      
      // Создаем ссылку для скачивания
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${presentationTitle || 'presentation'}.${type}`
      document.body.appendChild(link)
      link.click()
      
      // Очистка
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      console.log(`✅ ${type.toUpperCase()} файл успешно скачан`)
    } catch (err) {
      console.error(`Ошибка при скачивании ${type}:`, err)
      setError(`Ошибка при скачивании ${type.toUpperCase()}. Попробуйте еще раз.`)
    } finally {
      setIsDownloadingPptx(false)
    }
  }

  const handleRegenerateSlide = async (slideId: string) => {
    if (presentationId === null) {
      setError('Отсутствует ID презентации')
      return
    }

    const slide = slideTitles.find(s => s.id === slideId)
    if (!slide) {
      setError('Слайд не найден')
      return
    }

    console.log(`🔄 Перегенерация слайда ${slide.order}: "${slide.title}"`)

    try {
      // 1. Сохраняем изменения этого слайда на бэкенд
      await api.changeSlideInfo(
        presentationId,
        slide.order,
        slide.title,
        slide.description || ''
      )

      // 2. Помечаем слайд как регенерируемый
      setSlideTitles(prev => prev.map(s =>
        s.id === slideId ? { ...s, generated: false, contentJson: undefined } : s
      ))

      // 3. Запускаем перегенерацию через ассистента
      const message = `Перегенерируй слайд ${slide.order} с заголовком "${slide.title}" и описанием "${slide.description || ''}"`
      await api.presentationAssistantMessage(presentationId, message)

      // 4. Polling для получения обновленного слайда
      let attempts = 0
      const maxAttempts = 40 // 40 * 3 сек = 2 минуты

      const pollInterval = setInterval(async () => {
        try {
          attempts++
          const data = await api.getContent(presentationId)

          const normalize = (s: string) => (s || '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .replace(/[«»"""''`]/g, '')
            .replace(/[:;,.!?()-]/g, '')
            .trim()

          const pageByTitle = new Map<string, string>()
          data.forEach((p: any) => {
            const t = p.title || p.Title || ''
            const c = p.content || p.Content || ''
            const key = normalize(t)
            if (key && !pageByTitle.has(key)) {
              pageByTitle.set(key, c)
            }
          })

          const key = normalize(slide.title)
          const content = pageByTitle.get(key)

          if (content) {
            console.log(`✅ Слайд ${slide.order} перегенерирован`)
            setSlideTitles(prev => prev.map(s =>
              s.id === slideId ? { ...s, contentJson: content, generated: true } : s
            ))
            clearInterval(pollInterval)
            return
          }

          if (attempts >= maxAttempts) {
            console.log(`⏰ Превышено время ожидания для слайда ${slide.order}`)
            clearInterval(pollInterval)
            setError('Превышено время ожидания перегенерации слайда')
          }
        } catch (err) {
          console.error('Ошибка polling перегенерации слайда:', err)
        }
      }, 3000)

    } catch (error) {
      console.error('Ошибка перегенерации слайда:', error)
      setError('Ошибка при перегенерации слайда')
    }
  }

  const handleRefineRequest = async (prompt: string) => {
    if (presentationId === null) {
      setError('Отсутствует ID презентации')
      return
    }

    setIsRegenerating(true)
    setError(null)

    try {
      // Запускаем регенерацию и получаем список измененных слайдов
      console.log('🔄 Отправка запроса на доработку:', prompt)
      const response = await api.regeneratePresentation(presentationId, prompt)
      console.log('📋 Ответ от backend:', response)

      // Извлекаем позиции измененных слайдов из ответа
      const updatedPositions: number[] = response?.updated_slides?.map((s: any) => s.position) || []
      console.log('📌 Позиции слайдов для перегенерации:', updatedPositions)

      // Очищаем предыдущий интервал если он есть
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }

      // Помечаем ТОЛЬКО измененные слайды как перегенерирующиеся
      // Preview остается видимым, generationComplete НЕ сбрасывается
      setSlideTitles(prev => prev.map(slide => ({
        ...slide,
        isRegenerating: updatedPositions.includes(slide.order),
        // Сбрасываем generated только для перегенерирующихся слайдов
        generated: updatedPositions.includes(slide.order) ? false : slide.generated
      })))

      if (updatedPositions.length === 0) {
        setError('Не удалось определить какие слайды изменить. Попробуйте переформулировать запрос.')
        setIsRegenerating(false)
        return
      }

      // Начинаем polling для получения обновленных слайдов
      let receivedSlidesCount = 0
      const totalSlides = slideTitles.length
      let pollAttempts = 0
      const maxPollAttempts = 120

      pollingIntervalRef.current = window.setInterval(async () => {
        try {
          pollAttempts++

          // Получаем текущие готовые контент слайдов (формат [{Title, Content}])
          const data = await api.getContent(presentationId)

          const normalize = (s: string) => (s || '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .replace(/[«»"“”'’`]/g, '')
            .replace(/[:;,.!?()-]/g, '')
            .trim()

          // Карта: нормализованный заголовок -> контент
          const pageByTitle = new Map<string, string>()
          data.forEach((p: any) => {
            const t = p.title || p.Title || ''
            const c = p.content || p.Content || ''
            const key = normalize(t)
            if (key && !pageByTitle.has(key)) {
              pageByTitle.set(key, c)
            }
          })

          // Обновляем слайды строго по совпадению заголовков
          const refreshedSlides = slideTitles.map((slide) => {
            const key = normalize(slide.title)
            const content = pageByTitle.get(key)

            const wasRegenerating = slide.isRegenerating
            const hasNewContent = Boolean(content && content.trim())

            // При доработке через ассистента обновляем только помеченные слайды
            const shouldUpdateContent = wasRegenerating && hasNewContent

            // Обновляем contentJson
            const newContentJson = shouldUpdateContent ? content : (slide.contentJson ?? '')

            return {
              ...slide,
              contentJson: newContentJson,
              generated: Boolean(newContentJson && newContentJson.trim()),
              isRegenerating: wasRegenerating && !hasNewContent
            }
          })

          const generatedCount = refreshedSlides.filter(s => s.generated).length
          const stillRegeneratingCount = refreshedSlides.filter(s => s.isRegenerating).length

          if (generatedCount > receivedSlidesCount) {
            console.log(`📊 Получено обновленных слайдов: ${generatedCount}/${totalSlides}`)
            receivedSlidesCount = generatedCount
          }

          setSlideTitles(refreshedSlides)

          // Проверяем завершение регенерации - когда нет больше слайдов с флагом isRegenerating
          if (stillRegeneratingCount === 0 && generatedCount >= totalSlides) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            setGenerationComplete(true)
            setIsRegenerating(false)

            // Обновляем снимок слайдов после доработки
            console.log('📸 Обновляем снимок слайдов после доработки')
            setOriginalSlides(JSON.parse(JSON.stringify(refreshedSlides)))

            console.log('✅ Все слайды регенерированы!')
          }

          // Защита от бесконечного polling
          if (pollAttempts >= maxPollAttempts) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            setError('Превышено время ожидания регенерации')
            setIsRegenerating(false)
          }
        } catch (err) {
          console.error('Ошибка при получении обновленных HTML:', err)
        }
      }, 5000)

    } catch (error) {
      setError('Ошибка при запуске регенерации презентации')
      setIsRegenerating(false)
      throw error
    }
  }

  // Функция для сохранения названия презентации с debounce
  const savePresentationTitle = useCallback(async (title: string) => {
    if (!presentationId || !title.trim()) {
      return
    }

    // Не сохраняем если название не изменилось
    if (title.trim() === presentationTitle.trim()) {
      return
    }

    setIsSavingTitle(true)
    try {
      console.log('💾 Сохраняем название презентации:', title)
      await api.changeTitle(presentationId, title.trim())
      console.log('✅ Название презентации сохранено')
    } catch (error) {
      console.error('Ошибка сохранения названия презентации:', error)
      setError('Не удалось сохранить название презентации')
    } finally {
      setIsSavingTitle(false)
    }
  }, [presentationId, presentationTitle])

  // Debounce ref для названия презентации
  const titleSaveTimeoutRef = useRef<number | null>(null)

  // Обработчик изменения названия с debounce
  const handleTitleChange = useCallback((newTitle: string) => {
    setPresentationTitle(newTitle)

    // Очищаем предыдущий таймер
    if (titleSaveTimeoutRef.current) {
      clearTimeout(titleSaveTimeoutRef.current)
    }

    // Устанавливаем новый таймер для сохранения через 1 секунду
    titleSaveTimeoutRef.current = window.setTimeout(() => {
      savePresentationTitle(newTitle)
    }, 1000)
  }, [savePresentationTitle])

  // Обработчик потери фокуса для немедленного сохранения
  const handleTitleBlur = useCallback(() => {
    // Очищаем таймер debounce
    if (titleSaveTimeoutRef.current) {
      clearTimeout(titleSaveTimeoutRef.current)
      titleSaveTimeoutRef.current = null
    }

    // Немедленное сохранение
    savePresentationTitle(presentationTitle)
  }, [savePresentationTitle, presentationTitle])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="bg-white rounded-lg shadow-lg p-8">
            {/* Индикатор загрузки презентации */}
            {isLoadingPresentation && (
              <div className="flex flex-col items-center justify-center py-12 mb-8">
                <Loader2 className="h-12 w-12 animate-spin text-rosatom-blue mb-4" />
                <p className="text-gray-600">Загрузка презентации...</p>
              </div>
            )}

            {/* Шаг 1: Название презентации */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-rosatom-text mb-4 flex items-center">
                <FileText className="mr-3 text-rosatom-blue" />
                Шаг 1: Название презентации
                {presentationId && (
                  <span className="ml-3 text-sm font-normal text-gray-500">
                    (ID: {presentationId})
                  </span>
                )}
              </h2>
              <div className="flex gap-4">
                <input
                  type="text"
                  value={presentationTitle}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  onBlur={handleTitleBlur}
                  placeholder="Введите название презентации..."
                  disabled={analysisComplete}
                  className={`flex-1 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-rosatom-blue focus:border-transparent outline-none transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed ${
                    isSavingTitle ? 'border-yellow-400 bg-yellow-50' : 'border-gray-300'
                  }`}
                />
                {isSavingTitle && (
                  <div className="flex items-center text-yellow-600">
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    <span className="text-sm">Сохранение...</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <label htmlFor="slideCount" className="text-sm font-medium text-gray-700 whitespace-nowrap">
                    Количество слайдов:
                  </label>
                  <input
                    id="slideCount"
                    type="number"
                    min="1"
                    max="50"
                    value={slideCount}
                    onChange={(e) => setSlideCount(Math.max(1, parseInt(e.target.value) || 1))}
                    disabled={analysisComplete}
                    className="w-20 px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rosatom-blue focus:border-transparent outline-none transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  />
                </div>
              </div>
            </div>

            {/* Шаг 2: Загрузка файлов */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-rosatom-text mb-4 flex items-center">
                <FileText className="mr-3 text-rosatom-blue" />
                Шаг 2: Загрузка документов
              </h2>
              <FileUpload 
                onFilesUpload={handleFilesUpload} 
                isDisabled={!presentationTitle.trim()}
                isUploading={isUploadingFiles}
              />
            </div>

            {/* Шаг 3: Загрузка шаблона PPTX (опционально) */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-rosatom-text mb-4">
                Шаг 3: Загрузка шаблона PPTX (опционально)
              </h2>
              
              {/* Индикатор загруженного шаблона */}
              {templateLoaded && (
                <div className="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                  <p className="text-green-800 font-medium flex items-center">
                    <span className="text-green-600 text-xl mr-2">✓</span>
                    Шаблон загружен
                  </p>
                </div>
              )}
              
              <div 
                onDragOver={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.add('border-rosatom-blue', 'bg-rosatom-light-blue')
                }}
                onDragLeave={(e) => {
                  e.currentTarget.classList.remove('border-rosatom-blue', 'bg-rosatom-light-blue')
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.remove('border-rosatom-blue', 'bg-rosatom-light-blue')
                  const files = e.dataTransfer.files
                  if (files.length > 0) {
                    const event = {
                      target: {
                        files: files
                      }
                    } as React.ChangeEvent<HTMLInputElement>
                    handleTemplateUpload(event)
                  }
                }}
                className="bg-gray-50 rounded-lg p-6 border-2 border-dashed border-gray-300 transition-colors duration-200 cursor-pointer"
              >
                <div className="flex flex-col items-center">
                  <label
                    htmlFor="template-upload"
                    className={`cursor-pointer inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white transition-colors duration-200 ${
                      !presentationTitle.trim()
                        ? 'bg-gray-400 cursor-not-allowed opacity-50'
                        : 'bg-rosatom-blue hover:bg-rosatom-dark-blue focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rosatom-blue'
                    }`}
                  >
                    <FileText className="mr-2 h-5 w-5" />
                    Выбрать шаблон .pptx
                  </label>
                  <input
                    id="template-upload"
                    type="file"
                    accept=".pptx"
                    onChange={handleTemplateUpload}
                    disabled={!presentationTitle.trim()}
                    className="hidden"
                  />
                  <p className="mt-2 text-sm text-gray-500">
                    Перетащите файл сюда или нажмите для выбора
                  </p>
                  {!presentationTitle.trim() && (
                    <p className="mt-2 text-sm text-red-600 font-medium">
                      Введите название презентации для загрузки шаблона
                    </p>
                  )}
                  {templateFile && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200 w-full max-w-md">
                      <p className="text-green-800 font-medium text-sm flex items-center">
                        <FileText className="mr-2 h-4 w-4" />
                        {templateFile.name}
                      </p>
                      <p className="text-green-600 text-xs mt-1">
                        {(templateFile.size / 1024).toFixed(1)} KB
                      </p>
                      <button
                        onClick={() => {
                          setTemplateFile(null)
                          setTemplateLoaded(false)
                        }}
                        className="mt-2 text-xs text-red-600 hover:text-red-800"
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Шаг 4: Анализ данных */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-rosatom-text mb-4">
                Шаг 4: Анализ данных
              </h2>
              <button
                onClick={handleAnalyzeData}
                // enabled when there are uploaded files OR there is already a RAG collection on the backend
                disabled={(!hasRagCollection && uploadedFiles.length === 0) || isAnalyzing}
                className="btn-primary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Анализ данных...
                  </>
                ) : (
                  'Анализировать данные'
                )}
              </button>
              {hasRagCollection && uploadedFiles.length === 0 && (
                <p className="text-sm text-blue-600 mt-2">
                  💡 У этой презентации уже загружены данные. Нажмите кнопку для анализа.
                </p>
              )}
            </div>

            {/* Шаг 5: Редактирование заголовков */}
            {analysisComplete && slideTitles.length > 0 && (
              <div className="mb-8">
                <h2 className="text-2xl font-semibold text-rosatom-text mb-4">
                  Шаг 5: Редактирование структуры слайдов
                </h2>
                <SlideEditor 
                  slides={slideTitles} 
                  onSlidesChange={setSlideTitles}
                  onRegenerateSlide={handleRegenerateSlide}
                  showRegenerateButton={generationComplete}
                />
              </div>
            )}

            {/* Шаг 6: Генерация презентации */}
            {analysisComplete && (() => {
              const modifiedCount = generationComplete ? getModifiedSlides().length : 0
              const hasModifications = modifiedCount > 0
              const isButtonDisabled = slideTitles.length === 0 || isGenerating || (generationComplete && !hasModifications)
              
              return (
                <div className="mb-8">
                  <h2 className="text-2xl font-semibold text-rosatom-text mb-4">
                    Шаг 6: Генерация контента слайдов
                  </h2>
                  <button
                    onClick={handleGeneratePresentation}
                    disabled={isButtonDisabled}
                    className="btn-primary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Генерация контента...
                      </>
                    ) : generationComplete ? (
                      hasModifications ? (
                        `Перегенерировать измененные слайды (${modifiedCount})`
                      ) : (
                        'Нет изменений для перегенерации'
                      )
                    ) : (
                      'Сгенерировать контент слайдов'
                    )}
                  </button>
                  {generationComplete && (
                    <p className={`text-sm mt-2 ${hasModifications ? 'text-yellow-600' : 'text-green-600'}`}>
                      {hasModifications 
                        ? `⚠️ Обнаружено ${modifiedCount} ${modifiedCount === 1 ? 'измененный слайд' : 'измененных слайда'}. Нажмите кнопку для перегенерации.`
                        : '✅ Контент сгенерирован! Измените заголовки или описания слайдов выше для перегенерации.'
                      }
                    </p>
                  )}
                </div>
              )
            })()}
            
            {/* Шаг 7: Презентация */}
            {(isGenerating || generationComplete) && (
              <div className="mb-8">
                <h2 className="text-2xl font-semibold text-rosatom-text mb-4">
                  Шаг 7: Презентация
                  {isGenerating && !generationComplete && (
                    <span className="ml-3 text-sm font-normal text-blue-600">
                      (генерация в процессе...)
                    </span>
                  )}
                </h2>
                <PresentationPreview
                  slides={slideTitles}
                  onBack={() => {}} // Пустая функция, т.к. мы не уходим со страницы
                  onDownload={handleDownload}
                  onRefineRequest={handleRefineRequest}
                  isGenerating={isRegenerating || isGenerating}
                  generationComplete={generationComplete}
                  isDownloadingPptx={isDownloadingPptx}
                />
              </div>
            )}

            {/* Сообщение об ошибке */}
            {error && (
              <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
                <p className="text-red-800 flex items-center">
                  <AlertCircle className="mr-2 h-5 w-5" />
                  {error}
                </p>
              </div>
            )}
          </div>
      </main>
    </div>
  )
}

export default MainPage
