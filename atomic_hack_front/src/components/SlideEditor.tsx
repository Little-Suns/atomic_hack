import React, { useState, useEffect } from 'react'
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd'
import { GripVertical, Edit2, Check, X, Plus, Trash2, RefreshCw } from 'lucide-react'
import { SlideTitle } from '../pages/MainPage'

interface SlideEditorProps {
  slides: SlideTitle[]
  onSlidesChange: (slides: SlideTitle[]) => void
  onRegenerateSlide?: (slideId: string) => void
  showRegenerateButton?: boolean
}

const SlideEditor: React.FC<SlideEditorProps> = ({ slides, onSlidesChange, onRegenerateSlide, showRegenerateButton = false }) => {
  const [localSlides, setLocalSlides] = useState<SlideTitle[]>(slides)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editDescriptionId, setEditDescriptionId] = useState<string | null>(null)
  const [editDescriptionValue, setEditDescriptionValue] = useState('')

  useEffect(() => {
    setLocalSlides(slides)
  }, [slides])

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination) return

    const items = Array.from(localSlides)
    const [reorderedItem] = items.splice(result.source.index, 1)
    items.splice(result.destination.index, 0, reorderedItem)

    // Обновляем порядок
    const updatedSlides = items.map((item, index) => ({
      ...item,
      order: index + 1
    }))

    setLocalSlides(updatedSlides)
    onSlidesChange(updatedSlides)
  }

  const startEdit = (slide: SlideTitle) => {
    setEditingId(slide.id)
    setEditValue(slide.title)
  }

  const saveEdit = () => {
    if (editingId && editValue.trim()) {
      const updatedSlides = localSlides.map(slide =>
        slide.id === editingId ? { ...slide, title: editValue.trim() } : slide
      )
      setLocalSlides(updatedSlides)
      onSlidesChange(updatedSlides)
      setEditingId(null)
      setEditValue('')
    }
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditValue('')
  }

  const addSlide = () => {
    const newSlide: SlideTitle = {
      id: `slide-${Date.now()}`,
      title: 'Новый слайд',
      order: localSlides.length + 1
    }
    const updatedSlides = [...localSlides, newSlide]
    setLocalSlides(updatedSlides)
    onSlidesChange(updatedSlides)
  }

  const deleteSlide = (id: string) => {
    const updatedSlides = localSlides
      .filter(slide => slide.id !== id)
      .map((slide, index) => ({ ...slide, order: index + 1 }))
    setLocalSlides(updatedSlides)
    onSlidesChange(updatedSlides)
  }

  const startEditDescription = (slide: SlideTitle) => {
    setEditDescriptionId(slide.id)
    setEditDescriptionValue(slide.description || '')
  }

  const saveEditDescription = () => {
    if (editDescriptionId) {
      const updatedSlides = localSlides.map(slide =>
        slide.id === editDescriptionId ? { ...slide, description: editDescriptionValue.trim() } : slide
      )
      setLocalSlides(updatedSlides)
      onSlidesChange(updatedSlides)
      setEditDescriptionId(null)
      setEditDescriptionValue('')
    }
  }

  const cancelEditDescription = () => {
    setEditDescriptionId(null)
    setEditDescriptionValue('')
  }

  return (
    <div className="bg-gray-50 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-rosatom-text">
          Заголовки слайдов ({localSlides.length})
        </h3>
        <button
          onClick={addSlide}
          className="btn-secondary flex items-center text-sm py-1 px-3"
        >
          <Plus className="w-4 h-4 mr-1" />
          Добавить слайд
        </button>
      </div>

      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="slides">
          {(provided, snapshot) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className={`space-y-2 ${snapshot.isDraggingOver ? 'bg-blue-50' : ''} rounded-lg transition-colors duration-200`}
            >
              {localSlides.map((slide, index) => (
                <Draggable key={slide.id} draggableId={slide.id} index={index}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      className={`
                        bg-white rounded-lg border p-4 
                        ${snapshot.isDragging ? 'shadow-lg border-rosatom-blue' : 'border-gray-200'}
                        transition-all duration-200
                      `}
                    >
                      <div className="flex items-start">
                        <div
                          {...provided.dragHandleProps}
                          className="mr-3 mt-1 cursor-move text-gray-400 hover:text-gray-600"
                        >
                          <GripVertical className="w-5 h-5" />
                        </div>
                        
                        <div className="flex-1">
                          <div className="flex items-center">
                            <span className="text-sm font-medium text-gray-500 mr-3">
                              {slide.order}.
                            </span>
                            
                            {editingId === slide.id ? (
                              <div className="flex-1 flex items-center gap-2">
                                <input
                                  type="text"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  className="flex-1 px-3 py-1 border border-rosatom-blue rounded focus:outline-none focus:ring-2 focus:ring-rosatom-blue"
                                  autoFocus
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') saveEdit()
                                    if (e.key === 'Escape') cancelEdit()
                                  }}
                                />
                                <button
                                  onClick={saveEdit}
                                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                                  title="Сохранить"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={cancelEdit}
                                  className="p-1 text-red-600 hover:bg-red-50 rounded"
                                  title="Отменить"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex-1 flex items-center justify-between">
                                <div className="flex items-center gap-2 flex-1">
                                  <span className="text-rosatom-text font-medium">{slide.title}</span>
                                  {slide.generated && (
                                    <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">✓ Готов</span>
                                  )}
                                  {slide.generated === false && (
                                    <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded animate-pulse">⏳ Генерация...</span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  {showRegenerateButton && slide.generated && onRegenerateSlide && (
                                    <button
                                      onClick={() => onRegenerateSlide(slide.id)}
                                      className="p-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors duration-200"
                                      title="Перегенерировать этот слайд"
                                    >
                                      <RefreshCw className="w-4 h-4" />
                                    </button>
                                  )}
                                  <button
                                    onClick={() => startEdit(slide)}
                                    className="p-1 text-gray-500 hover:text-rosatom-blue hover:bg-gray-50 rounded transition-colors duration-200"
                                    title="Редактировать заголовок"
                                  >
                                    <Edit2 className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => deleteSlide(slide.id)}
                                    className="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors duration-200"
                                    title="Удалить"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Описание слайда */}
                          <div className="mt-2 ml-8">
                            {editDescriptionId === slide.id ? (
                              <div className="flex items-start gap-2">
                                <textarea
                                  value={editDescriptionValue}
                                  onChange={(e) => setEditDescriptionValue(e.target.value)}
                                  className="flex-1 px-3 py-2 border border-rosatom-blue rounded focus:outline-none focus:ring-2 focus:ring-rosatom-blue text-sm resize-none"
                                  rows={2}
                                  autoFocus
                                  placeholder="Описание слайда..."
                                />
                                <div className="flex flex-col gap-1">
                                  <button
                                    onClick={saveEditDescription}
                                    className="p-1 text-green-600 hover:bg-green-50 rounded"
                                    title="Сохранить описание"
                                  >
                                    <Check className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={cancelEditDescription}
                                    className="p-1 text-red-600 hover:bg-red-50 rounded"
                                    title="Отменить"
                                  >
                                    <X className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div 
                                onClick={() => startEditDescription(slide)}
                                className="flex items-start gap-2 cursor-pointer group"
                              >
                                {slide.description ? (
                                  <p className="text-sm text-gray-600 flex-1 group-hover:text-gray-800 transition-colors">
                                    {slide.description}
                                  </p>
                                ) : (
                                  <p className="text-sm text-gray-400 italic flex-1 group-hover:text-gray-600 transition-colors">
                                    Нажмите для добавления описания...
                                  </p>
                                )}
                                <Edit2 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5" />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>

      {localSlides.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Нет заголовков слайдов. Нажмите "Добавить слайд" для начала.
        </div>
      )}
    </div>
  )
}

export default SlideEditor
