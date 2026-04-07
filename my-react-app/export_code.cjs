const fs = require('fs');
const path = require('path');

const filesToExport = [
  'index.html',
  'src/main.jsx',
  'src/App.jsx',
  'src/index.css',
  'src/shared/tokens.css',
  'src/chat/ChatPage.jsx',
  'src/chat/hooks/useChat.js',
  'src/chat/constants/mockData.js',
  'src/chat/components/Sidebar.jsx',
  'src/chat/components/Topbar.jsx',
  'src/chat/components/MessageList.jsx',
  'src/chat/components/Message.jsx',
  'src/chat/components/ProductCard.jsx',
  'src/chat/components/ChatInput.jsx',
  'src/chat/styles/chat.css',
  'src/admin/AdminPage.jsx',
  'src/admin/hooks/useETL.js',
  'src/admin/components/ETLControls.jsx',
  'src/admin/components/StatusBadge.jsx',
  'src/admin/components/ProgressFeed.jsx',
  'src/admin/styles/admin.css'
];

let markdownContent = '# Nexus Marketplace Frontend - Code Export\n\n';
markdownContent += 'This document contains all the major source files for the React frontend project. Explain the logic and implementation for these files line by line.\n\n';

filesToExport.forEach(file => {
  try {
    const fullPath = path.join(__dirname, file);
    if (fs.existsSync(fullPath)) {
      const content = fs.readFileSync(fullPath, 'utf-8');
      const ext = path.extname(file).substring(1);
      let language = ext;
      if (ext === 'jsx' || ext === 'js') language = 'javascript';
      
      markdownContent += `## File: \`${file}\`\n\n`;
      markdownContent += '```' + language + '\n';
      markdownContent += content + '\n';
      markdownContent += '```\n\n';
    } else {
      console.warn(`File not found: ${file}`);
    }
  } catch (err) {
    console.error(`Error reading ${file}:`, err.message);
  }
});

const outputPath = path.join(__dirname, 'Project_Code_Export.md');
fs.writeFileSync(outputPath, markdownContent);
console.log('Export complete: Project_Code_Export.md');