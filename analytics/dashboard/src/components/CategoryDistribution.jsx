import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useCubeQuery } from '../hooks/useCubeQuery';
import { ChartWrapper, ChartSkeleton, ChartError } from './ChartHelpers';

export default function CategoryDistribution() {
  const { data, isLoading, error } = useCubeQuery({
    measures: ['CategoryDistribution.total_product_count'],
    order: { 'CategoryDistribution.total_product_count': 'desc' },
    dimensions: ['CategoryDistribution.name'],
  });

  if (isLoading) return <ChartSkeleton title="Category Distribution" />;
  if (error) return <ChartError title="Category Distribution" error={error} />;

  const chartData = (data || []).map(row => ({
    category: row['CategoryDistribution.name'],
    products: Number(row['CategoryDistribution.total_product_count']),
  }));

  return (
    <ChartWrapper title="Products per Top-Level Category">
      <ResponsiveContainer width="100%" height={450}>
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#bbf7d0" />
          <XAxis type="number" stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} />
          <YAxis type="category" dataKey="category" stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} width={150} />
          <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #bbf7d0', color: '#14532d' }} />
          <Bar dataKey="products" fill="#22c55e" radius={[0, 4, 4, 0]} name="Products" />
        </BarChart>
      </ResponsiveContainer>
    </ChartWrapper>
  );
}
