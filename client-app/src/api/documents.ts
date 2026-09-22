import { apiClient } from './client';
import type { Document } from './types';

export async function listDocuments(projectId: string): Promise<Document[]> {
  const { data } = await apiClient.get<Document[]>(`/projects/${projectId}/documents`);
  return data;
}

export async function uploadDocument(projectId: string, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await apiClient.post<Document>(`/projects/${projectId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return data;
}

export async function deleteDocument(projectId: string, documentId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/documents/${documentId}`);
}
