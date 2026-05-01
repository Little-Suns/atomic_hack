import React, { useState } from 'react'
import { Star } from 'lucide-react'

interface StarRatingProps {
  onRatingChange?: (rating: number) => void
}

const StarRating: React.FC<StarRatingProps> = ({ onRatingChange }) => {
  const [rating, setRating] = useState<number>(0)
  const [hoverRating, setHoverRating] = useState<number>(0)

  const handleClick = (value: number) => {
    setRating(value)
    if (onRatingChange) {
      onRatingChange(value)
    }
  }

  const handleMouseEnter = (value: number) => {
    setHoverRating(value)
  }

  const handleMouseLeave = () => {
    setHoverRating(0)
  }

  const stars = [1, 2, 3, 4, 5]

  return (
    <div className="flex flex-col items-center space-y-2">
      <h4 className="text-sm font-medium text-gray-700">
        Оцените качество презентации
      </h4>
      <div className="flex items-center space-x-2">
        {stars.map((star) => {
          const isFilled = star <= (hoverRating || rating)
          return (
            <button
              key={star}
              onClick={() => handleClick(star)}
              onMouseEnter={() => handleMouseEnter(star)}
              onMouseLeave={handleMouseLeave}
              className="transition-all duration-200 transform hover:scale-110 focus:outline-none"
              aria-label={`Оценка ${star} из 5`}
            >
              <Star
                className={`w-8 h-8 transition-colors duration-200 ${
                  isFilled
                    ? 'fill-yellow-400 text-yellow-400'
                    : 'fill-gray-200 text-gray-300 hover:fill-gray-300'
                }`}
              />
            </button>
          )
        })}
      </div>
      {rating > 0 && (
        <p className="text-sm text-gray-600">
          Ваша оценка: <span className="font-semibold text-rosatom-blue">{rating} из 5</span>
        </p>
      )}
    </div>
  )
}

export default StarRating
