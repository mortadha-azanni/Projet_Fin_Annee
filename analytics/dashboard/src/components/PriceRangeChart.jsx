import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useCubeQuery } from '../hooks/useCubeQuery';
import { ChartWrapper, ChartSkeleton, ChartError } from './ChartHelpers';

function CategorySelect({ value, onChange }) {
  const { data, isLoading } = useCubeQuery({
    measures: ['CategoryDistribution.total_product_count'],
    dimensions: ['CategoryDistribution.name'],
    order: { 'CategoryDistribution.name': 'asc' },
  });

  const categories = (data || [])
    .map(row => row['CategoryDistribution.name'])
    .filter(Boolean);

  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={isLoading}
      style={{
        marginBottom: '1.25rem',
        padding: '0.5rem 1rem',
        background: '#f0fdf4',
        border: '1px solid #bbf7d0',
        borderRadius: '6px',
        color: '#14532d',
        fontSize: '0.875rem',
        cursor: 'pointer',
        width: '100%',
        outline: 'none',
      }}
    >
      <option value="">— Select a category —</option>
      {categories.map(cat => (
        <option key={cat} value={cat}>{cat}</option>
      ))}
    </select>
  );
}

export default function PriceRangeChart() {
  const [selectedCategory, setSelectedCategory] = useState('');

  const { data, isLoading, error } = useCubeQuery(
    selectedCategory
      ? {
          measures: [
            'PriceAnalysis.avg_price',
            'PriceAnalysis.min_price',
            'PriceAnalysis.max_price',
          ],
          dimensions: ['PriceAnalysis.name'],
          filters: [
            {
              member: 'PriceAnalysis.name',
              operator: 'equals',
              values: [selectedCategory],
            },
          ],
        }
      : null
  );

  const chartData = selectedCategory && data
    ? (data || []).map(row => ({
        category: row['PriceAnalysis.name'],
        avg: parseFloat(Number(row['PriceAnalysis.avg_price']).toFixed(2)),
        min: parseFloat(Number(row['PriceAnalysis.min_price']).toFixed(2)),
        max: parseFloat(Number(row['PriceAnalysis.max_price']).toFixed(2)),
      }))
    : [];

  return (
    <ChartWrapper title="Price Range by Category (DT)">
      <CategorySelect value={selectedCategory} onChange={setSelectedCategory} />

      {!selectedCategory && (
        <div style={{
          height: '450px', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#4b7c59', fontSize: '0.875rem'
        }}>
          Select a category to view price analysis
        </div>
      )}

      {selectedCategory && isLoading && (
        <div style={{
          height: '450px', background: '#f0fdf4', borderRadius: '8px', opacity: 0.6
        }} />
      )}

      {selectedCategory && error && (
        <p style={{ color: '#dc2626', fontSize: '0.875rem' }}>
          {error?.message || 'Failed to load data'}
        </p>
      )}

      {selectedCategory && !isLoading && !error && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={450}>
          <BarChart data={chartData} barCategoryGap="40%">
            <CartesianGrid strokeDasharray="3 3" stroke="#bbf7d0" />
            <XAxis dataKey="category" stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} />
            <YAxis stroke="#bbf7d0" tick={{ fill: '#4b7c59' }} />
            <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #bbf7d0', color: '#14532d' }} />
            <Legend wrapperStyle={{ color: '#4b7c59' }} />
            <Bar dataKey="min" fill="#4ade80" radius={[4, 4, 0, 0]} name="Min (DT)" />
            <Bar dataKey="avg" fill="#16a34a" radius={[4, 4, 0, 0]} name="Avg (DT)" />
            <Bar dataKey="max" fill="#166534" radius={[4, 4, 0, 0]} name="Max (DT)" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartWrapper>
  );
}
