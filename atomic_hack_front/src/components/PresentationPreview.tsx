import React, { useState } from 'react'
import { Eye, Download, Edit3, Send, ArrowLeft, Loader2, AlertCircle } from 'lucide-react'
import { SlideTitle } from '../pages/MainPage'
import StarRating from './StarRating'

interface PresentationPreviewProps {
  slides: SlideTitle[]
  onBack: () => void
  onDownload: (type: 'pdf' | 'pptx') => void
  onRefineRequest: (prompt: string) => Promise<void>
  isGenerating: boolean
  generationComplete: boolean
  isDownloadingPptx?: boolean
}

const PresentationPreview: React.FC<PresentationPreviewProps> = ({
  slides,
  onBack,
  onDownload,
  onRefineRequest,
  isGenerating,
  generationComplete,
  isDownloadingPptx = false
}) => {
  const [refinePrompt, setRefinePrompt] = useState('')
  const [isRefining, setIsRefining] = useState(false)
  const [showRefineForm, setShowRefineForm] = useState(false)
  const [_presentationRating, setPresentationRating] = useState<number>(0)

  const handleRefineSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!refinePrompt.trim()) return

    setIsRefining(true)
    try {
      await onRefineRequest(refinePrompt.trim())
      setRefinePrompt('')
      setShowRefineForm(false)
    } catch (error) {
      console.error('Ошибка при отправке запроса на доработку:', error)
    } finally {
      setIsRefining(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <button
            onClick={onBack}
            className="mr-4 p-2 text-gray-500 hover:text-rosatom-blue hover:bg-gray-50 rounded-md transition-colors duration-200"
            title="Назад к редактированию"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-2xl font-semibold text-rosatom-text flex items-center">
              <Eye className="mr-3 text-rosatom-blue" />
              Превью презентации
            </h2>
            <p className="text-gray-600 text-sm mt-1">
              Проверьте контент каждого слайда. При необходимости запросите доработку.
            </p>
          </div>
        </div>
      </div>

      {/* Превью слайдов */}
      <div className="mb-6">
        <div className="grid gap-6 max-h-[800px] overflow-y-auto pr-2">
          {slides.map((slide, index) => (
            <div
              key={slide.id}
              className="bg-white rounded-lg border-2 border-gray-200 hover:border-rosatom-blue transition-all duration-200 overflow-hidden shadow-sm hover:shadow-md"
            >
              {/* Заголовок слайда */}
              <div className="bg-gradient-to-r from-rosatom-blue to-rosatom-dark-blue p-4 flex items-center">
                <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center text-white font-bold mr-3">
                  {index + 1}
                </div>
                <h4 className="text-xl font-semibold text-white flex-1">{slide.title}</h4>
                <div className="flex items-center gap-2">
                  {slide.isRegenerating && (
                    <span className="px-3 py-1 bg-yellow-400 bg-opacity-90 text-white text-xs rounded-full font-medium flex items-center gap-1">
                      <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Перегенерация
                    </span>
                  )}
                  {slide.generated && !slide.isRegenerating && (
                    <span className="px-3 py-1 bg-green-500 bg-opacity-80 text-white text-xs rounded-full font-medium">
                      ✓ Готово
                    </span>
                  )}
                </div>
              </div>
              
              {/* Контент слайда */}
              <div className="p-6 bg-gray-50">
                {slide.isRegenerating || !slide.generated ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-8 h-8 text-rosatom-blue animate-spin mr-3" />
                    <span className="text-gray-600">Генерация контента...</span>
                  </div>
                ) : slide.contentJson && slide.contentJson.trim() ? (
                  <div className="bg-white border border-gray-300 rounded p-4">
                    {(() => {
                      try {
                        const content = JSON.parse(slide.contentJson)
                        return (
                          <div className="space-y-4">
                            {content.blocks?.map((block: any, blockIdx: number) => (
                              <div key={blockIdx}>
                                {block.type === 'text' && (
                                  <p className="text-gray-700 leading-relaxed">{block.data?.text}</p>
                                )}
                                {block.type === 'list' && (
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {block.data?.items?.map((item: string, i: number) => (
                                      <li key={i}>{item}</li>
                                    ))}
                                  </ul>
                                )}
                                {block.type === 'chart' && (
                                  <div className="p-4 bg-blue-50 rounded border border-blue-200">
                                    <div className="flex items-center gap-2 mb-3">
                                      <span className="text-2xl">📊</span>
                                      <p className="font-semibold text-blue-900 capitalize">
                                        {block.data?.chart_type || 'Chart'}
                                      </p>
                                    </div>
                                    {block.data?.data?.categories && block.data?.data?.series ? (
                                      <div className="overflow-x-auto">
                                        <table className="min-w-full text-sm border-collapse bg-white rounded">
                                          <thead>
                                            <tr className="bg-blue-100">
                                              <th className="border border-blue-200 px-3 py-2 text-left font-medium text-blue-900">
                                                Категория
                                              </th>
                                              {block.data.data.series.map((series: any, idx: number) => (
                                                <th key={idx} className="border border-blue-200 px-3 py-2 text-left font-medium text-blue-900">
                                                  {series.name || `Серия ${idx + 1}`}
                                                </th>
                                              ))}
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {block.data.data.categories.map((cat: string, catIdx: number) => (
                                              <tr key={catIdx} className={catIdx % 2 === 0 ? 'bg-white' : 'bg-blue-50'}>
                                                <td className="border border-blue-200 px-3 py-2 font-medium text-gray-700">
                                                  {cat}
                                                </td>
                                                {block.data.data.series.map((series: any, serIdx: number) => (
                                                  <td key={serIdx} className="border border-blue-200 px-3 py-2 text-gray-600">
                                                    {series.values?.[catIdx] ?? '-'}
                                                  </td>
                                                ))}
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    ) : (
                                      <p className="text-sm text-gray-600">График будет отображен в финальной презентации</p>
                                    )}
                                  </div>
                                )}
                                {block.type === 'table' && (
                                  <div className="overflow-x-auto">
                                    <table className="min-w-full border-collapse border border-gray-300">
                                      {block.data?.data?.map((row: string[], rowIdx: number) => (
                                        <tr key={rowIdx} className={rowIdx === 0 ? 'bg-gray-100 font-semibold' : ''}>
                                          {row.map((cell: string, cellIdx: number) => (
                                            <td key={cellIdx} className="border border-gray-300 px-3 py-2 text-sm">
                                              {cell}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </table>
                                  </div>
                                )}
                                {block.type === 'image' && (
                                  <div className="p-3 bg-gray-100 rounded border border-gray-200">
                                    {block.data?.url ? (
                                      <div className="flex items-start gap-4">
                                        <img
                                          src={block.data.url}
                                          alt={block.data?.description || 'image'}
                                          className="w-36 h-24 object-cover rounded-md border"
                                        />
                                        <div className="flex-1">
                                          <p className="text-gray-700">{block.data?.description || 'Описание отсутствует'}</p>
                                        </div>
                                      </div>
                                    ) : (
                                      <p className="text-gray-700">{block.data?.description || 'Описание изображения'}</p>
                                    )}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )
                      } catch (e) {
                        return (
                          <p className="text-red-600 text-sm">Ошибка отображения контента</p>
                        )
                      }
                    })()}
                  </div>
                ) : slide.description ? (
                  <p className="text-gray-700 leading-relaxed">
                    {slide.description}
                  </p>
                ) : (
                  <p className="text-gray-500 italic text-center py-4">
                    Контент слайда будет сгенерирован автоматически
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Форма для доработки */}
      <div className="mb-6 border-t border-gray-200 pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-rosatom-text">
            Нужны корректировки?
          </h3>
          <button
            onClick={() => setShowRefineForm(!showRefineForm)}
            className="btn-secondary flex items-center text-sm py-2 px-4"
          >
            <Edit3 className="w-4 h-4 mr-2" />
            {showRefineForm ? 'Скрыть' : 'Запросить доработку'}
          </button>
        </div>

        {showRefineForm && (
          <form onSubmit={handleRefineSubmit} className="space-y-4">
            <div>
              <label htmlFor="refinePrompt" className="block text-sm font-medium text-gray-700 mb-2">
                Опишите, что нужно изменить в контенте слайдов
              </label>
              <textarea
                id="refinePrompt"
                rows={4}
                value={refinePrompt}
                onChange={(e) => setRefinePrompt(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rosatom-blue focus:border-transparent outline-none transition-all duration-200 resize-none"
                placeholder="Например: 'В слайде 3 добавить больше данных о статистике', 'Изменить акценты в слайде 5 на экологические преимущества', 'Убрать пункт 2 из слайда 4', 'Добавить информацию о рисках в слайд 7'..."
                disabled={isRefining}
              />
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowRefineForm(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors duration-200"
                disabled={isRefining}
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={!refinePrompt.trim() || isRefining}
                className="btn-primary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRefining ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Отправка запроса...
                  </>
                ) : (
                  <>
                    <Send className="mr-2 h-4 w-4" />
                    Отправить запрос
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Кнопки скачивания */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="text-lg font-semibold text-rosatom-text mb-4">
          Скачать готовую презентацию
        </h3>
        
        {isGenerating && !generationComplete ? (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <div className="flex items-center">
              <Loader2 className="w-5 h-5 text-rosatom-blue mr-3 animate-spin" />
              <div>
                <p className="text-rosatom-blue font-medium">
                  Генерация презентации в процессе...
                </p>
                <p className="text-blue-700 text-sm mt-1">
                  Контент слайдов обрабатывается. Скачивание будет доступно через несколько минут.
                </p>
              </div>
            </div>
          </div>
        ) : !generationComplete ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
              <p className="text-yellow-800 text-sm">
                Дождитесь завершения генерации презентации.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <div className="flex items-center">
                <Eye className="w-5 h-5 text-green-600 mr-2" />
                <p className="text-green-800 text-sm">
                  Презентация готова! Вы можете скачать её в формате PPTX.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-4">
              <button
                onClick={() => onDownload('pptx')}
                disabled={isDownloadingPptx}
                className="btn-secondary flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDownloadingPptx ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Генерация PPTX...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-5 w-5" />
                    Скачать PPTX
                  </>
                )}
              </button>
            </div>

            {/* Оценка презентации */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <StarRating onRatingChange={(rating) => {
                setPresentationRating(rating)
                console.log('Оценка презентации:', rating)
              }} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PresentationPreview
