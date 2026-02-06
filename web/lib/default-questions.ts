// Default personalization questions based on PRD
// These questions will be inserted for every new topic

export interface DefaultQuestion {
  question_text: string;
  question_type:
    | 'goal'
    | 'difficulty'
    | 'scope'
    | 'time'
    | 'source'
    | 'subtopic'
    | 'delivery_day'
    | 'generate_now';
  options: string[];
  display_order: number;
  is_required: boolean;
}

export const defaultQuestions: DefaultQuestion[] = [
  {
    question_text: '이 주제를 알아보는 목적이 무엇인가요?',
    question_type: 'goal',
    options: ['업무 적용', '학습/호기심', '투자/사업 검토', '기타'],
    display_order: 1,
    is_required: true,
  },
  {
    question_text: '어느 정도 수준의 설명을 원하시나요?',
    question_type: 'difficulty',
    options: ['초급 (기본 개념부터)', '중급 (실무 활용)', '고급 (전문가 수준)'],
    display_order: 2,
    is_required: true,
  },
  {
    question_text: '뉴스레터 분량은 어느 정도가 좋을까요?',
    question_type: 'time',
    options: [
      '3분 (빠른 요약)',
      '5분 (핵심 정리)',
      '10분 (상세 설명)',
      '15분+ (깊이 있는 분석)',
    ],
    display_order: 3,
    is_required: true,
  },
  {
    question_text: '선호하는 정보 출처가 있나요? (복수 선택 가능)',
    question_type: 'source',
    options: ['공식 문서', '학술 논문', '테크 블로그', '뉴스 기사'],
    display_order: 4,
    is_required: false,
  },
  {
    question_text: '관심 있는 범위를 선택해주세요 (복수 선택 가능)',
    question_type: 'scope',
    options: ['산업 동향', '기술 구현', '오픈소스', '학계 연구'],
    display_order: 5,
    is_required: false,
  },
  {
    question_text: '특히 관심 있는 하위 주제나 키워드가 있다면 알려주세요',
    question_type: 'subtopic',
    options: [],
    display_order: 6,
    is_required: false,
  },
  {
    question_text: '뉴스레터를 매주 받고 싶은 요일을 선택해주세요',
    question_type: 'delivery_day',
    options: [
      '월요일',
      '화요일',
      '수요일',
      '목요일',
      '금요일',
      '토요일',
      '일요일',
    ],
    display_order: 7,
    is_required: true,
  },
  {
    question_text: '지금 바로 생성하고 싶으신가요?',
    question_type: 'generate_now',
    options: ['지금 바로 생성하기'],
    display_order: 8,
    is_required: false,
  },
];
