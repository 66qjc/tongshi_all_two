import http from './http'

export interface WrongQuestion {
    question_id: number
    course_id: number
    stem: string
    options: string[]
    answer: string
    explanation: string
    user_answer: string
    answered_at: string
}

export interface LikedProject {
    id: number
    title: string
    author_name: string
    major: string
    description: string
    image_url: string
    images: { image_url: string; sort_order: number }[]
    likes: number
    date: string
}

export function getWrongQuestions() {
    return http.get<any, WrongQuestion[]>('/profile/wrong-questions')
}

export function getLikedProjects() {
    return http.get<any, LikedProject[]>('/profile/liked-projects')
}
