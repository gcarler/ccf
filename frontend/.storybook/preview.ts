import type { Preview } from '@storybook/react'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'
import '../src/app/globals.css'
import { ThemeDecorator } from './ThemeDecorator';

export const globalTypes = {
  theme: {
    name: 'Tema',
    description: 'Modo de color de la interfaz',
    toolbar: {
      title: 'Tema',
      icon: 'circle',
      items: [
        { value: 'day', title: 'Claro' },
        { value: 'night', title: 'Oscuro' },
      ],
    },
  },
};

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
       color: /(background|color)$/i,
       date: /Date$/i,
      },
    },
  },
  initialGlobals: {
    theme: 'day',
  },
  decorators: [ThemeDecorator],
};

export default preview;
