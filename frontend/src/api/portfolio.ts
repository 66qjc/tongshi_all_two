import http from './http'
import type { Project } from './project'

export interface PortfolioData {
  user: { id: string; name: string; role: string; major?: string }
  stats: { study_hours: number; total_exercises: number; accuracy: number; project_count: number }
  radar: Record<string, number>
  timeline: { type: string; title: string; date: string }[]
  projects: Project[]
}

export function getPortfolio() {
  return http.get<any, PortfolioData>('/portfolio')
}
