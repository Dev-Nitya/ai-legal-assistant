# AI Legal Assistant Frontend

A professional React TypeScript frontend for the AI Legal Assistant application, featuring a premium white and golden design theme with smooth animations.

## Features

- 🎨 **Premium Design**: Professional white and golden color scheme
- ⚡ **Modern Stack**: React 18 + TypeScript + Vite
- 🎭 **Smooth Animations**: Framer Motion for professional animations
- 🎯 **Responsive Design**: Mobile-first responsive design
- 🔍 **Smart Chat Interface**: Intelligent legal question processing
- 📚 **Source References**: Display of referenced legal documents
- ⚙️ **Real-time Updates**: Live chat with loading states

## Tech Stack

- **Frontend Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with custom golden theme
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Backend Integration**: RESTful API communication

## Design System

### Colors

- **Primary**: Golden tones (#f59e0b, #fbbf24, #fcd34d)
- **Background**: White and light gray gradients
- **Text**: Professional gray tones
- **Accents**: Golden highlights for premium feel

### Typography

- **Font Family**: Inter (Google Fonts)
- **Weights**: 300, 400, 500, 600, 700

## Getting Started

### Prerequisites

- Node.js 16+
- npm or yarn

### Installation

1. **Install dependencies**:

   ```bash
   npm install
   ```

2. **Start development server**:

   ```bash
   npm run dev
   ```

3. **Build for production**:
   ```bash
   npm run build
   ```

### Backend Integration

Make sure your backend API is running on `http://localhost:8000` with the following endpoint:

- `POST /chat`
  - Request: `{ question: string, session_id: string }`
  - Response: `{ answer: string, source_documents: string[], confidence: number }`

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ChatMessage.tsx  # Individual chat message
│   └── SourceDocument.tsx # Document reference sidebar
├── hooks/               # Custom React hooks
│   └── useChatAPI.ts   # API communication hook
├── types/               # TypeScript type definitions
│   └── index.ts        # Main type exports
├── App.tsx             # Main application component
├── main.tsx            # React entry point
└── index.css           # Global styles and Tailwind imports
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Features in Detail

### Chat Interface

- Professional message bubbles with user/assistant distinction
- Real-time typing indicators
- Error handling with user-friendly messages
- Confidence scoring display

### Animations

- Fade-in animations for new messages
- Slide-up effects for UI elements
- Loading animations with golden accents
- Smooth transitions throughout the interface

### Responsive Design

- Mobile-first approach
- Adaptive layout for different screen sizes
- Touch-friendly interface elements

## Customization

The design system is built with Tailwind CSS and can be easily customized through the `tailwind.config.js` file. The golden theme is implemented through custom color palettes and utility classes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the AI Legal Assistant application suite.
