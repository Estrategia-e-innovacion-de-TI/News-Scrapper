import { Injectable } from '@angular/core';
import { Cluster, HypeStage, Trend } from '../models/trendmap.model';

@Injectable({ providedIn: 'root' })
export class TrendmapService {
  sortClustersByImpact(clusters: Cluster[]): Cluster[] {
    return [...clusters].sort((a, b) => b.impact_score - a.impact_score);
  }

  filterClustersByCategory(clusters: Cluster[], category: string): Cluster[] {
    return clusters.filter((c) => c.category === category);
  }

  groupTrendsByMaturity(trends: Trend[]): Map<HypeStage, Trend[]> {
    const map = new Map<HypeStage, Trend[]>();
    for (const trend of trends) {
      const group = map.get(trend.maturity_stage) ?? [];
      group.push(trend);
      map.set(trend.maturity_stage, group);
    }
    return map;
  }

  getDirectionColor(direction: Trend['direction']): string {
    switch (direction) {
      case 'creciente':
        return '#00C587';
      case 'decreciente':
        return '#FF803A';
      case 'estable':
        return '#4B5563';
    }
  }
}
