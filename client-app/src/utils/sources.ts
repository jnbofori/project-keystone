import type { SourceCitation } from '@/api/types';

export function uniqueSourceFilenames(sources: SourceCitation[]): string[] {
  const names = sources.map((source) => source.filename).filter((name): name is string => !!name);
  return [...new Set(names)];
}
