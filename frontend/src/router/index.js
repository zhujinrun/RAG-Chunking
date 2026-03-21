import { createRouter, createWebHistory } from 'vue-router'
import KnowledgeBaseList from '../views/KnowledgeBaseList.vue'
import DocumentManagement from '../views/DocumentManagement.vue'

const routes = [
  {
    path: '/',
    name: 'KnowledgeBaseList',
    component: KnowledgeBaseList
  },
  {
    path: '/kb/:id/documents',
    name: 'DocumentManagement',
    component: DocumentManagement
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
