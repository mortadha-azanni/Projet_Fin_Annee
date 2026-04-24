import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useCubeQuery } from '../hooks/useCubeQuery';
import { ChartWrapper, ChartSkeleton, ChartError } from './ChartHelpers';

export default function ProductsIndexedChart() {
  const { data, isLoading, error } = useCubeQuery({
    measures: ['ProductsBySource.count'],
    dimensions: ['ProductsBySource.source'],
    order: { 'ProductsBySource.count': 'desc' },
  });

  if (isLoading) return <ChartSkeleton title="Products by Source" />;
  if (error) return <ChartError title="Products by Source" error={error} />;

  const chartData = (data || []).map(row => ({
    source: row['ProductsBySource.source'] || 'Unknown',
    count: Number(row['ProductsBySource.count']),
  }));

  return (
    <ChartWrapper title="Products Indexed by Source">
      <ResponsiveContainer width="100%" height={450}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#bbf7d0" />
          <XAxis dataKey="source" stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} />
          <YAxis stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} />
          <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #bbf7d0', color: '#14532d' }} />
          <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} name="Products" />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}
