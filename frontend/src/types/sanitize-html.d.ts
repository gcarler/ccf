declare module "sanitize-html" {
  interface IOptions {
    allowedTags?: string[];
    allowedAttributes?: Record<string, string[]>;
    allowedSchemes?: string[];
    allowedSchemesAppliedToAttributes?: string[];
    allowProtocolRelative?: boolean;
    transformTags?: Record<string, string | ((tagName: string, attribs: Record<string, string>) => { tagName: string; attribs: Record<string, string> })>;
    exclusiveFilter?: (frame: { tag: string; attribs: Record<string, string>; text: string }) => boolean;
    textFilter?: (text: string) => string;
    nonBooleanAttributes?: string[];
    ignoreDecorators?: string[];
    disallowedTagsMode?: "discard" | "recursiveEscape" | "escape";
  }

  function sanitizeHtml(dirty: string, options?: IOptions): string;
  namespace sanitizeHtml {
    type IOptions = import("sanitize-html").IOptions;
    function simpleTransform(tagName: string, attrs: Record<string, string>, merge?: boolean): (tagName: string, attribs: Record<string, string>) => { tagName: string; attribs: Record<string, string> };
  }
  export = sanitizeHtml;
}
