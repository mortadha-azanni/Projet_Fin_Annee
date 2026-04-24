import { CubeProvider } from '@cubejs-client/react';
import cubejsApi from '../cubejsClient';
import Layout from './Layout';
import StatCard from './StatCard';
import ProductsIndexedChart from './ProductsIndexedChart';
import CategoryDistribution from './CategoryDistribution';
import PriceRangeChart from './PriceRangeChart';
import UserProfileSearch from './UserRegistrationsChart';
import { useCubeQuery } from '../hooks/useCubeQuery';

function StatsRow() {
  const products = useCubeQuery({ measures: ['Products.count'] });
  const categories = useCubeQuery({ measures: ['Categories.count'] });
  const users = useCubeQuery({ measures: ['Users.count'] });

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1rem',
      marginBottom: '2rem'
    }}>
      <StatCard
        title="Total Products"
        value={products.data?.[0]?.['Products.count'] ?? '...'}
        subtitle="Indexed across all sources"
        color="#3b82f6"
      />
      <StatCard
        title="Total Categories"
        value={categories.data?.[0]?.['Categories.count'] ?? '...'}
        subtitle="Including subcategories"
        color="#8b5cf6"
      />
      <StatCard
        title="Registered Users"
        value={users.data?.[0]?.['Users.count'] ?? '...'}
        subtitle="Admin accounts"
        color="#f59e0b"
      />
    </div>
  );
}

export default function AnalyticsDashboard() {
  return (
    <CubeProvider cubejsApi={cubejsApi}>
      <Layout>
        <StatsRow />
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '2rem'
        }}>
          <ProductsIndexedChart />
          <CategoryDistribution />
          <PriceRangeChart />
          <UserProfileSearch />
        </div>
      </Layout>
    </CubeProvider>
  );
}
