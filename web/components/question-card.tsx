'use client';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { Question, Answer } from '@/lib/validation/question';
import { getAnswerTypeFromQuestionType } from '@/lib/validation/question';

interface QuestionCardProps {
  question: Question;
  value?: Answer;
  onChange: (answer: Answer | undefined) => void;
  onSkip: () => void;
  skipped: boolean;
  error?: string;
}

export function QuestionCard({
  question,
  value,
  onChange,
  onSkip,
  skipped,
  error,
}: QuestionCardProps) {
  const answerType = getAnswerTypeFromQuestionType(question.question_type);
  const options = question.options || [];

  const handleRadioChange = (selectedValue: string) => {
    onChange({
      type: 'radio',
      value: selectedValue,
    });
  };

  const handleCheckboxChange = (optionValue: string, checked: boolean) => {
    const currentValues =
      value?.type === 'checkbox' ? value.value : ([] as string[]);
    const newValues = checked
      ? [...currentValues, optionValue]
      : currentValues.filter((v) => v !== optionValue);

    onChange({
      type: 'checkbox',
      value: newValues,
    });
  };

  const handleTextChange = (text: string) => {
    onChange({
      type: 'text',
      value: text,
    });
  };

  const handleSkipClick = () => {
    onChange(undefined);
    onSkip();
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {question.question_text}
            {question.is_required && (
              <span className="ml-1 text-red-600">*</span>
            )}
          </h3>
        </div>
        {!question.is_required && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleSkipClick}
            className="ml-4 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            스킵
          </Button>
        )}
      </div>

      {skipped ? (
        <div className="rounded-md bg-gray-100 p-4 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-400">
          이 질문을 건너뛰었습니다.{' '}
          <button
            type="button"
            onClick={() => onSkip()}
            className="font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            답변하기
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {answerType === 'radio' && (
            <div className="space-y-2">
              {options.map((option) => (
                <label
                  key={option}
                  className="flex cursor-pointer items-center space-x-3 rounded-md border border-gray-200 p-3 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={option}
                    checked={value?.type === 'radio' && value.value === option}
                    onChange={(e) => handleRadioChange(e.target.value)}
                    className="h-4 w-4 border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {option}
                  </span>
                </label>
              ))}
            </div>
          )}

          {answerType === 'checkbox' && (
            <div className="space-y-2">
              {options.map((option) => (
                <label
                  key={option}
                  className="flex cursor-pointer items-center space-x-3 rounded-md border border-gray-200 p-3 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
                >
                  <input
                    type="checkbox"
                    value={option}
                    checked={
                      value?.type === 'checkbox' && value.value.includes(option)
                    }
                    onChange={(e) =>
                      handleCheckboxChange(option, e.target.checked)
                    }
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {option}
                  </span>
                </label>
              ))}
            </div>
          )}

          {answerType === 'text' && (
            <div>
              <Input
                type="text"
                value={value?.type === 'text' ? value.value : ''}
                onChange={(e) => handleTextChange(e.target.value)}
                placeholder="답변을 입력해주세요"
                className="w-full"
                maxLength={500}
              />
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {value?.type === 'text' ? value.value.length : 0}/500
              </p>
            </div>
          )}
        </div>
      )}

      {error && !skipped && (
        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}
