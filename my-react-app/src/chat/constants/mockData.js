export const SUGGESTION_CHIPS = [
  "Running shoes",
  "Wireless headphones",
  "Mechanical keyboards",
  "Ergonomic chairs"
];

export const WELCOME_MESSAGE = {
  id: 1,
  role: 'assistant',
  content: 'Hi, I am your AI Shopping Assistant. What are you looking for today?',
  streaming: false,
  products: []
};

export const MOCK_HISTORY = [
  { id: 'chat_1', title: 'Running shoes', timestamp: '2 hours ago' },
  { id: 'chat_2', title: 'Wireless headphones', timestamp: 'Yesterday' }
];

export const MOCK_PRODUCTS = [
  {
    id: 'p1',
    name: 'Nike Air Zoom Pegasus 39',
    category: 'RUNNING',
    price: '$129.99',
    rating: 4.8,
    image: '👟'
  },
  {
    id: 'p2',
    name: 'Sony WH-1000XM5',
    category: 'AUDIO',
    price: '$348.00',
    rating: 4.9,
    image: '🎧'
  },
  {
    id: 'p3',
    name: 'Keychron Q1 Pro',
    category: 'KEYBOARD',
    price: '$199.00',
    rating: 4.7,
    image: '⌨️'
  }
];