export interface ChartPoint {
  time: number;
  value: number;
}

function generateRandomWalk(count: number, start: number, volatility: number): ChartPoint[] {
  const points: ChartPoint[] = [];
  let value = start;
  const now = Math.floor(Date.now() / 1000);
  for (let i = 0; i < count; i++) {
    value += (Math.random() - 0.45) * volatility;
    value = Math.max(0, value);
    points.push({ time: now - (count - i) * 60, value });
  }
  return points;
}

export const shortInterestData = generateRandomWalk(50, 12, 0.8);
export const spreadVolumeData = generateRandomWalk(50, 0.03, 0.005);
export const outstandingData = generateRandomWalk(50, 450, 5);

export function generateBarData(count: number): number[] {
  return Array.from({ length: count }, () => 30 + Math.random() * 70);
}
