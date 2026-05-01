import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onFilesUpload: (files: File[]) => void
  isDisabled?: boolean
  isUploading?: boolean
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesUpload, isDisabled = false, isUploading = false }) => {
  const [files, setFiles] = React.useState<File[]>([])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (isDisabled || isUploading) return
    const newFiles = [...files, ...acceptedFiles]
    setFiles(newFiles)
    onFilesUpload(newFiles)
  }, [files, onFilesUpload, isDisabled, isUploading])

  const removeFile = (index: number) => {
    const newFiles = files.filter((_, i) => i !== index)
    setFiles(newFiles)
    onFilesUpload(newFiles)
  }

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv']
    },
    multiple: true
  })

  const getDropzoneClassName = () => {
    let className = 'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 '
    
    if (isDisabled || isUploading) {
      className += 'border-gray-300 bg-gray-100 cursor-not-allowed opacity-50'
    } else if (isDragAccept) {
      className += 'border-green-500 bg-green-50'
    } else if (isDragReject) {
      className += 'border-red-500 bg-red-50'
    } else if (isDragActive) {
      className += 'border-rosatom-blue bg-rosatom-light-blue'
    } else {
      className += 'border-gray-300 hover:border-rosatom-blue hover:bg-gray-50'
    }
    
    return className
  }

  return (
    <div>
      <div {...getRootProps()} className={getDropzoneClassName()}>
        <input {...getInputProps()} disabled={isDisabled} />
        
        <div className="flex flex-col items-center">
          {isUploading ? (
            <>
              <Loader2 className="w-12 h-12 mb-4 text-rosatom-blue animate-spin" />
              <p className="text-rosatom-blue font-medium">Загрузка файлов...</p>
            </>
          ) : (
            <>
              <Upload className={`w-12 h-12 mb-4 ${isDragActive && !isDisabled ? 'text-rosatom-blue' : 'text-gray-400'}`} />
              
              {isDisabled && (
                <p className="text-gray-600 font-medium">Введите название презентации для загрузки файлов</p>
              )}
              {!isDisabled && isDragAccept && (
                <p className="text-green-600 font-medium">Отпустите файлы для загрузки</p>
              )}
              {!isDisabled && isDragReject && (
                <p className="text-red-600 font-medium">Некоторые файлы имеют неподдерживаемый формат</p>
              )}
              {!isDisabled && !isDragActive && (
                <>
                  <p className="text-gray-700 font-medium mb-2">
                    Перетащите файлы сюда или нажмите для выбора
                  </p>
                  <p className="text-gray-500 text-sm">
                    Поддерживаемые форматы: PDF, Excel, Word, PowerPoint, TXT, CSV
                  </p>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {/* Список загруженных файлов */}
      {files.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-rosatom-text mb-3">
            Загруженные файлы:
          </h3>
          <div className="space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center">
                  <FileText className="w-5 h-5 text-rosatom-blue mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  disabled={isUploading}
                  className="p-1 hover:bg-gray-200 rounded transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Удалить файл"
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default FileUpload
