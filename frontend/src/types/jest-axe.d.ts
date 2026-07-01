declare module 'jest-axe' {
  import { AxeResults } from 'axe-core';
  
  export interface JestAxeConfiguration {
    globalOptions?: any;
    impactLevels?: string[];
    rules?: any[];
  }
  
  export function axe(
    html: Element | string,
    options?: JestAxeConfiguration
  ): Promise<AxeResults>;
  
  export function toHaveNoViolations(results: AxeResults): {
    message: () => string;
    pass: boolean;
  };
  
  export function configureAxe(options: JestAxeConfiguration): void;
}

declare module '*.svg' {
  const content: string;
  export default content;
}

declare module '*.png' {
  const content: string;
  export default content;
}

declare module '*.jpg' {
  const content: string;
  export default content;
}

declare module '*.jpeg' {
  const content: string;
  export default content;
}

declare module '*.gif' {
  const content: string;
  export default content;
}

declare module '*.webp' {
  const content: string;
  export default content;
}
