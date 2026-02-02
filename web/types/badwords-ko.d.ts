declare module 'badwords-ko' {
  interface FilterOptions {
    placeHolder?: string;
    regex?: RegExp;
    replaceRegex?: RegExp;
  }

  class Filter {
    constructor(options?: FilterOptions);
    clean(text: string): string;
    isProfane(text: string): boolean;
  }

  export default Filter;
}
