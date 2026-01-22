import Filter from 'badwords-ko';

const filter = new Filter();

/**
 * Checks if the given text contains Korean profanity
 * @param text - The text to check for profanity
 * @returns true if profanity is detected, false otherwise
 */
export function containsProfanity(text: string): boolean {
  if (!text || text.trim().length === 0) {
    return false;
  }

  const cleaned = filter.clean(text);
  // If the cleaned text contains asterisks (*), profanity was detected
  return cleaned.includes('*');
}

/**
 * Cleans profanity from the given text by replacing it with asterisks
 * @param text - The text to clean
 * @returns The cleaned text with profanity replaced by asterisks
 */
export function cleanProfanity(text: string): string {
  if (!text || text.trim().length === 0) {
    return text;
  }

  return filter.clean(text);
}
