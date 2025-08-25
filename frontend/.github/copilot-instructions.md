<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# AI Legal Assistant Frontend

This is a React TypeScript frontend for an AI Legal Assistant application with the following specifications:

## Design Guidelines

- **Theme**: Professional white and golden color scheme for premium appearance
- **Primary Colors**: Various shades of white (#ffffff, #f9fafb, #f3f4f6)
- **Accent Colors**: Golden tones (#f59e0b, #fbbf24, #fcd34d) for premium touches
- **Typography**: Clean, professional fonts (Inter)

## Technical Stack

- React 18 with TypeScript
- Vite for development and building
- Tailwind CSS for styling
- Framer Motion for animations
- Lucide React for icons

## Backend Integration

- Backend API endpoint: `http://localhost:8000`
- Chat endpoint: `POST /chat`
- Request format: `{ question: string, session_id: string }`
- Response format: `{ answer: string, source_documents: string[], confidence: number }`

## UI Components Requirements

- Professional chat interface with message bubbles
- Smooth animations and transitions using Framer Motion
- Dropdown menus where appropriate
- Source document display with proper formatting
- Loading states and error handling
- Responsive design for mobile and desktop

## Animation Guidelines

- Use subtle, professional animations
- Fade-in effects for new messages
- Slide-up animations for UI elements
- Hover effects with golden accents
- Loading spinners with golden colors

## Code Patterns

- Use TypeScript interfaces for type safety
- Implement proper error boundaries
- Follow React best practices with hooks
- Use custom hooks for API calls
- Implement proper loading and error states
